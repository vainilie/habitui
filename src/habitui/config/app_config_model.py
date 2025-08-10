# ♥♥─── Settings Model ───────────────────────────────────────────────────────────
from __future__ import annotations

from uuid import UUID as TYPE_UUID
from typing import Any, Self
from pathlib import Path
from functools import lru_cache

from pydantic import Field, SecretStr, computed_field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from habitui.custom_logger import log


DUMMY_UUID = TYPE_UUID("00000000-0000-0000-0000-000000000000")
DUMMY_TOKEN = SecretStr("deadbeef-dead-4bad-beef-deadbeef0000")


@lru_cache
def get_project_root() -> Path:
	"""Detect the project root intelligently."""
	current = Path.cwd()
	for parent in [current, *list(current.parents)]:
		if any((parent / indicator).exists() for indicator in ["requirements.txt", ".git"]):
			return parent
	return current


root = get_project_root()
app_data = root / "app_data"


@lru_cache
def get_default_env_path() -> Path:
	"""Get the default path for the main environment file."""
	return root / "app_data/config/.env"


@lru_cache
def get_default_tags_path() -> Path:
	"""Get the default path for the tags environment file."""
	return root / "app_data/config/tags.env"


# ─── Default Content Constants ────────────────────────────────────────────────
TAGS_ENV_DEFAULT_CONTENT = """# Tag Configuration
# Add your tag IDs and rules here
# TAGS_ID_ATTR_STR=your-str-tag-id
# TAGSs_ID_ATTR_INT=your-int-tag-id
# TAGS_ID_ATTR_CON=your-con-tag-id
# TAGS_ID_ATTR_PER=your-per-tag-id
# TAGS_ID_NO_ATTR=your-no-attr-tag-id
# TAGS_ID_CHALLENGE=your-challenge-tag-id
# TAGS_ID_PERSONAL=your-personal-tag-id
# TAGS_ID_LEGACY=your-legacy-tag-id
# DEFAULT_ATTR=str
"""
ENV_DEFAULT_CONTENT = """# HabiTui Configuration File
# Copy this file and fill in your actual values
# ─── Habitica API Configuration ────────────────────────────────────
# Get these from https://habitica.com/user/settings/api
HABITICA_USER_ID=your-user-id-here
HABITICA_API_TOKEN=your-api-token-here
# ─── Storage Configuration ─────────────────────────────────────────
# STORAGE_DB_DIR=database
# STORAGE_RAW_DIR=raw_cache
# STORAGE_PROCESSED_DIR=processed_cache
# STORAGE_DB_FILENAME=habitui_database.db
# ─── Cache Configuration ───────────────────────────────────────────
# CACHE_CONTENT_DAYS=7
# CACHE_LIVE_MINUTES=5
# CACHE_CHALLENGE_HOURS=2
"""


# ─── Configuration Paths Component ────────────────────────────────────────────
class ConfigPaths(BaseSettings):
	"""Optional configuration for application directory structure and file paths."""

	model_config = SettingsConfigDict(
		env_prefix="CONFIG_",
		case_sensitive=False,
		extra="ignore",
		env_file=get_default_env_path(),
	)

	@computed_field
	@property
	def app_data_dir(self) -> Path:
		"""Base directory for all application data storage.

		:return: The path to the application data directory.
		"""
		return root / "app_data"

	@computed_field
	@property
	def config_dir(self) -> Path:
		"""Directory containing all configuration files.

		:return: The path to the configuration directory.
		"""
		return self.app_data_dir / "config"

	@computed_field
	@property
	def env_file_path(self) -> Path:
		"""The path to the main .env configuration file.

		:return: The path to the .env file.
		"""
		return self.config_dir / ".env"

	@computed_field
	@property
	def tags_env_path(self) -> Path:
		"""Full path to the tags-specific config file.

		:return: The path to the tags.env file.
		"""
		return self.config_dir / "tags.env"

	def model_post_init(self, __context: Any | None = None, /) -> None:
		"""Ensure configuration directory exists after initialization."""
		self.config_dir.mkdir(parents=True, exist_ok=True)


# ─── Habitica Configuration Component Models ────────────────────────────────
class HabiticaApiSettings(BaseSettings):
	"""Configuration for Habitica API credentials and connection settings."""

	model_config = SettingsConfigDict(
		env_prefix="HABITICA_",
		env_file_encoding="utf-8",
		case_sensitive=False,
		extra="ignore",
		env_file=get_default_env_path(),
	)
	user_id: TYPE_UUID = Field(
		default=DUMMY_UUID,
		title="Habitica User ID",
		description="Habitica User UUID",
		examples=["12345678-1234-5678-9012-123456789012"],
	)
	api_token: SecretStr = Field(
		default=DUMMY_TOKEN,
		title="Habitica API Token",
		description="Your private API token. \nKeep this secret and secure.",
		examples=["87654321-4321-8765-2109-876543210987"],
	)

	@field_validator("api_token")
	@classmethod
	def validate_api_token_uuid(cls, v: SecretStr | None) -> SecretStr | None:
		"""Validate that api_token is a valid UUID format."""
		if v is None:
			return None
		try:
			token_value = v.get_secret_value()
		except Exception as e:
			msg = "api_token must be a valid SecretStr"
			raise ValueError(msg) from e
		if not token_value or not token_value.strip():
			msg = "api_token must not be empty or blank"
			raise ValueError(msg)
		try:
			TYPE_UUID(token_value.strip())
		except ValueError as e:
			msg = "api_token must be a valid UUID format"
			raise ValueError(msg) from e
		return v

	@model_validator(mode="after")
	def _check_credentials_present(self) -> Self:
		if self.user_id == DUMMY_UUID:
			msg = "HABITICA_USER_ID must not be the dummy value."
			raise ValueError(msg)
		if self.api_token.get_secret_value() == DUMMY_TOKEN.get_secret_value():
			msg = "HABITICA_API_TOKEN must not be the dummy value."
			raise ValueError(msg)
		return self


# ─── Storage Configuration ───────────────────────────────────────────────────────────
class StorageSettings(BaseSettings):
	"""Optional configuration for customizing data storage paths and file naming."""

	model_config = SettingsConfigDict(
		env_prefix="STORAGE_",
		env_file_encoding="utf-8",
		case_sensitive=False,
		extra="ignore",
		env_file=get_default_env_path(),
	)
	db_dir: str = Field(
		default="database",
		title="Database Directory Name",
		description="The subdirectory for database",
		min_length=1,
		max_length=255,
		pattern=r"^[a-zA-Z0-9_\-\.]+$",
		examples=["database", "db", "sqlite_data"],
	)
	raw_dir: str = Field(
		default="raw",
		title="Raw Data Cache Directory Name",
		description="The subdirectory for raw API data",
		min_length=1,
		max_length=255,
		pattern=r"^[a-zA-Z0-9_\-\.]+$",
		examples=["raw_cache", "api_cache", "raw_data"],
	)
	processed_dir: str = Field(
		default="processed",
		title="Processed Data Cache Directory Name",
		description="The subdirectory for processed data",
		min_length=1,
		max_length=255,
		pattern=r"^[a-zA-Z0-9_\-\.]+$",
		examples=["processed_cache", "processed_data", "transformed_cache"],
	)
	db_filename: str = Field(
		default="HabiTui.db",
		title="Main Database Filename",
		description="Filename for the main database",
		min_length=1,
		max_length=255,
		pattern=r"^[a-zA-Z0-9_\-\.]+\.(db|sqlite|sqlite3)$",
		examples=["habitui_database.db", "main.sqlite", "app_data.sqlite3"],
	)

	def get_database_directory(self) -> Path:
		"""Get the full path to the database directory."""
		return app_data / self.db_dir

	def get_database_file_path(self) -> Path:
		"""Get the full path to the main database file."""
		return self.get_database_directory() / self.db_filename

	def get_raw_data_directory(self) -> Path:
		"""Get the full path to the raw data cache directory."""
		return root / self.raw_dir

	def get_processed_data_directory(self) -> Path:
		"""Get the full path to the processed data cache directory."""
		return root / self.processed_dir

	def ensure_directories_exist(self) -> None:
		"""Create all necessary storage directories if they don't already exist."""
		directories_to_create: list[Path] = [
			self.get_database_directory(),
			self.get_raw_data_directory(),
			self.get_processed_data_directory(),
		]
		for directory_path in directories_to_create:
			directory_path.mkdir(parents=True, exist_ok=True)


# ─── Cache Settings ───────────────────────────────────────────────────────────
class CacheSettings(BaseSettings):
	"""Optional configuration for application cache timeouts and data freshness."""

	model_config = SettingsConfigDict(
		env_prefix="CACHE_",
		case_sensitive=False,
		extra="ignore",
		env_file_encoding="utf-8",
		env_file=get_default_env_path(),
	)
	content_days: int = Field(
		default=7,
		ge=1,
		le=365,
		title="Content Cache (Days)",
		description="Days to cache general content data",
		examples=[7, 14, 30],
	)
	live_minutes: int = Field(
		default=15,
		ge=1,
		le=1440,
		title="Live Data Cache (Minutes)",
		description="Minutes to cache live feed data",
		examples=[5, 10, 15],
	)
	challenge_hours: int = Field(
		default=12,
		ge=1,
		le=168,
		title="Challenge Data Cache (Hours)",
		description="Hours to cache challenge data",
		examples=[2, 4, 12, 24],
	)


# ─── Tags Config ──────────────────────────────────────────────────────────────
class TagSettings(BaseSettings):
	"""Optional configuration for mapping tags to attributes and special categories."""

	model_config = SettingsConfigDict(
		env_prefix="TAGS_",
		env_file_encoding="utf-8",
		case_sensitive=False,
		extra="ignore",
		env_file=str(get_default_tags_path()),
	)
	id_attr_str: TYPE_UUID | None = Field(
		default=None,
		title="Strength Attr Tag ID",
		description="Tag UUID for Strength attribute",
	)
	id_attr_int: TYPE_UUID | None = Field(
		default=None,
		title="Intelligence Attr Tag ID",
		description="Tag UUID for Intelligence attribute",
	)
	id_attr_con: TYPE_UUID | None = Field(
		default=None,
		title="Constitution Attr Tag ID",
		description="Tag UUID for Constitution attribute",
	)
	id_attr_per: TYPE_UUID | None = Field(
		default=None,
		title="Perception Attr Tag ID",
		description="Tag UUID for Perception attribute",
	)
	id_no_attr: TYPE_UUID | None = Field(
		default=None,
		title="No Attr Tag ID",
		description="Tag UUID for attribute not manually set",
	)
	id_legacy: TYPE_UUID | None = Field(
		default=None,
		title="Legacy Tag ID",
		description="Tag UUID for guild challenges",
	)
	id_challenge: TYPE_UUID | None = Field(
		default=None,
		title="Challenge Tag ID",
		description="Tag UUID for challenge tasks",
	)
	id_personal: TYPE_UUID | None = Field(
		default=None,
		title="Personal Tag ID",
		description="Tag UUID for personal tasks",
	)
	default_attr: str = Field(
		default="str",
		title="Default Attr Type",
		description="Default attribute to assign",
		pattern=r"^(str|int|con|per)$",
		examples=["str", "int", "con", "per"],
	)

	@field_validator(
		"id_attr_str",
		"id_attr_int",
		"id_attr_con",
		"id_attr_per",
		"id_no_attr",
		"id_legacy",
		"id_challenge",
		"id_personal",
	)
	@classmethod
	def validate_tag_id_uuid(cls, v: str | TYPE_UUID | None) -> TYPE_UUID | None:
		"""Validate that tag IDs are valid UUID format when provided.

		:param v: The tag ID string.
		:return: The validated tag ID string or None.
		:raises ValueError: If the tag ID is not a valid UUID.
		"""
		if v is None:
			return None
		if isinstance(v, TYPE_UUID):
			return v
		if isinstance(v, str):
			v = v.strip()
			if not v:
				return None
			try:
				return TYPE_UUID(v)
			except ValueError as e:
				msg = "Tag ID must be a valid UUID format"
				raise ValueError(msg) from e
		msg = f"Unsupported type for UUID field: {type(v).__name__}"
		raise TypeError(msg)

	@field_validator("default_attr")
	@classmethod
	def validate_default_attr(cls, v: str | None) -> str | None:
		"""Validate that default_attr is one of: str, int, con, per."""
		if v is None:
			return None
		allowed_values = {"str", "int", "con", "per"}
		v_lower = v.lower()
		if v_lower not in allowed_values:
			msg = f"default_attr must be one of: {', '.join(allowed_values)}"
			raise ValueError(msg)
		return v_lower

	@classmethod
	def from_env_file(cls, env_file_path: Path) -> Self:
		"""Load tag settings from an .env file or create a default if it doesn't exist.

		:param env_file_path: The path to the tags .env file.
		:return: A TagSettings instance loaded from the file or with defaults.
		"""
		if not env_file_path.exists():
			cls._create_default_env_file(env_file_path)
		try:
			return cls(_env_file=env_file_path)  # type: ignore[call-arg]
		except Exception as e:
			log.warning("Failed to load tags from env file {}: {}", env_file_path, e)
			return cls()

	@staticmethod
	def _create_default_env_file(env_file_path: Path) -> None:
		"""Create a default tags.env file.

		:param env_file_path: The path where the default tags.env file should be created.
		"""
		try:
			env_file_path.parent.mkdir(parents=True, exist_ok=True)
			env_file_path.write_text(TAGS_ENV_DEFAULT_CONTENT, encoding="utf-8")
			log.info("Created default tags configuration file: {}", env_file_path)
		except OSError as e:
			log.warning("Could not create default tags file: {}", e)


# ─── Application Settings ─────────────────────────────────────────────────────
class ApplicationSettings(BaseSettings):
	"""Main application settings model for the HabiTui Habitica integration tool."""

	model_config = SettingsConfigDict(
		case_sensitive=False,
		extra="ignore",
		title="HabiTui Application Configuration",
		env_file=str(get_default_env_path()),
		env_file_encoding="utf-8",
	)
	habitica: HabiticaApiSettings = Field(default_factory=HabiticaApiSettings, title="Habitica API Configuration")
	paths: ConfigPaths = Field(default_factory=ConfigPaths, title="Application Paths Configuration")
	storage: StorageSettings = Field(default_factory=StorageSettings, title="Storage Configuration")
	cache: CacheSettings = Field(default_factory=CacheSettings, title="Cache Configuration")
	tags: TagSettings | None = Field(default_factory=TagSettings, title="Tag Configuration")

	@property
	def base_storage_dir(self) -> Path:
		"""Base directory where all storage data is located.

		:return: The base storage path.
		"""
		return self.paths.app_data_dir

	@classmethod
	def get_schema(cls) -> dict[str, Any]:
		"""Generate and return the complete JSON schema for the application settings.

		:return: The JSON schema of the application settings.
		"""
		return cls.model_json_schema()

	def validate_configuration(self) -> bool:
		"""Validate the configuration and return True if all required settings are configured.

		Checks if `user_id` and `api_token` are set and not their dummy values.
		:return: True if the configuration is valid, False otherwise.
		"""
		try:
			return self.habitica.user_id != DUMMY_UUID and self.habitica.api_token != DUMMY_TOKEN
		except Exception as e:
			log.error("Configuration validation failed: {}", e)
			return False

	def get_configuration_summary(self) -> dict[str, Any]:
		"""Return a summary of the current configuration (excluding sensitive data).

		:return: A dictionary summarizing the configuration.
		"""
		return {
			"config_directory": str(self.paths.config_dir),
			"env_file": str(self.paths.env_file_path),
			"api_configured": self.habitica.user_id != DUMMY_UUID and self.habitica.api_token != DUMMY_TOKEN,
			"storage_db_filename": self.storage.db_filename,
			"cache_content_days": self.cache.content_days,
			"cache_live_minutes": self.cache.live_minutes,
			"cache_challenge_hours": self.cache.challenge_hours,
			"tags_configured": self.tags is not None,
			"default_attribute": self.tags.default_attr if self.tags else "str",
		}

	@classmethod
	def get_schema_friendly(cls) -> dict[str, Any]:
		"""Return a simplified, grouped, and normalized version of the schema.

		:return: A dictionary representing the friendly schema.
		"""
		schema = cls.get_schema()
		return cls._build_friendly_schema(schema)

	@classmethod
	def _build_friendly_schema(cls, schema: dict[str, Any]) -> dict[str, Any]:
		"""Build a simplified and normalized schema for display purposes.

		:param schema: The raw JSON schema.
		:return: The friendly schema.
		"""
		result = {"title": schema.get("title"), "description": schema.get("description"), "properties": {}}
		for item_name, item_data in schema.get("properties", {}).items():
			section_name = item_name
			ref = cls._extract_ref(item_data)
			if ref and ref in schema.get("$defs", {}):
				about = schema["$defs"][ref]
				props = cls._normalize_properties(about.get("properties", {}))
				detailed_props = {}
				for prop_name, prop_data in props.items():
					field_info = cls._extract_field_info(prop_name, prop_data, section_name)
					detailed_props[prop_name] = field_info
				result["properties"][item_name] = {
					"display_title": item_data.get("title", "(untitled)"),
					"name": about.get("title"),
					"description_text": about.get("description"),
					"properties": detailed_props,
					"category": section_name,
				}
			else:
				field_info = cls._extract_field_info(item_name, item_data, "")
				result["properties"][item_name] = {"display_title": item_data.get("title", "(untitled)"), **field_info}
		return result

	@staticmethod
	def _extract_field_info(field_name: str, schema_field_data: dict[str, Any], section_name: str) -> dict[str, Any]:
		"""Extract detailed field information similar to FieldInfo.from_schema_field().

		:param field_name: The name of the field.
		:param schema_field_data: The schema data for the field.
		:param section_name: The section/category name.
		:return: Dictionary with extracted field information.
		"""
		field_type_indicator = "string"
		if schema_field_data.get("type") == "integer":
			field_type_indicator = "integer"
		elif schema_field_data.get("type") == "boolean":
			field_type_indicator = "boolean"
		elif schema_field_data.get("format") == "uuid" or (
			schema_field_data.get("type") == "string"
			and schema_field_data.get("pattern")
			and "uuid" in schema_field_data["pattern"]
		):
			field_type_indicator = "uuid"
		is_sensitive = schema_field_data.get("writeOnly", False) or schema_field_data.get("format") == "password"
		env_var_name = f"{section_name.upper()}_{field_name.upper()}"
		default_value = schema_field_data.get("default")
		is_required = section_name == "habitica"
		min_value = schema_field_data.get("minimum", schema_field_data.get("exclusiveMinimum"))
		max_value = schema_field_data.get("maximum", schema_field_data.get("exclusiveMaximum"))
		title = schema_field_data.get("title")
		pattern = schema_field_data.get("pattern")
		example_text = None
		if schema_field_data.get("examples"):
			example_text = schema_field_data["examples"][0] if schema_field_data["examples"] else None
		description_text = schema_field_data.get("description", schema_field_data.get("title"))
		icon_display = schema_field_data.get("icon", "•")
		return {
			"name": field_name,
			"title": title,
			"env_var_name": env_var_name,
			"description_text": description_text,
			"example_text": example_text,
			"is_sensitive": is_sensitive,
			"field_type_indicator": field_type_indicator,
			"default_value": default_value,
			"min_value": min_value,
			"max_value": max_value,
			"is_required": is_required,
			"category": section_name,
			"icon_display": icon_display,
			"pattern": pattern,
		}

	@staticmethod
	def _extract_ref(item_data: dict[str, Any]) -> str | None:
		"""Extract the reference name from a schema item.

		:param item_data: The schema item data.
		:return: The reference name or None.
		"""
		if "$ref" in item_data:
			return item_data["$ref"].split("/")[-1]
		if "anyOf" in item_data:
			for option in item_data["anyOf"]:
				if "$ref" in option:
					return option["$ref"].split("/")[-1]
		return None

	@staticmethod
	def _normalize_properties(props: dict[str, Any]) -> dict[str, Any]:
		"""Normalize properties by resolving 'anyOf' for friendly schema.

		:param props: The properties dictionary.
		:return: The normalized properties dictionary.
		"""
		result = {}
		for prop_name, prop_data in props.items():
			if "anyOf" in prop_data:
				non_null = next((entry for entry in prop_data["anyOf"] if entry.get("type") != "null"), None)
				if non_null:
					prop_data = {**prop_data, **non_null}  # noqa: PLW2901
					prop_data.pop("anyOf", None)
			result[prop_name] = prop_data
		return result
