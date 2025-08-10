from __future__ import annotations

from typing import Any, Self, Literal, cast
from dataclasses import field, dataclass

from habitui.core.client import HabiticaClient
from habitui.core.models import (
	UserMessage,
	TagCollection,
	TaskCollection,
	UserCollection,
	PartyCollection,
	ContentCollection,
	ChallengeCollection,
)
from habitui.custom_logger import log
from habitui.config.app_config import app_config
from habitui.core.repositories import (
	TagVault,
	TaskVault,
	UserVault,
	PartyVault,
	ContentVault,
	SaveStrategy,
	ChallengeVault,
)


SuccessfulResponseData = dict[str, Any] | list[dict[str, Any]] | list[Any] | None
VaultType = Literal["user", "party", "content", "tasks", "challenges", "tags"]
INBOX_MINIMAL = 201


@dataclass
class VaultConfig:
	name: str
	vault_attr: str
	collection_attr: str
	fetch_method: str
	collection_class: type
	dependencies: list[VaultType] = field(default_factory=list)
	requires_cast: bool = True


class DataVault:
	# Configuración de vaults
	VAULT_CONFIGS = {
		"content": VaultConfig("content", "content_vault", "game_content", "get_game_content", ContentCollection),
		"party": VaultConfig("party", "party_vault", "party", "get_current_party_data", PartyCollection),
		"user": VaultConfig(
			"user", "user_vault", "user", "get_current_user_data", UserCollection, dependencies=["content"]
		),
		"tags": VaultConfig("tags", "tag_vault", "tags", "get_all_tags_data", TagCollection, requires_cast=False),
		"tasks": VaultConfig(
			"tasks", "task_vault", "tasks", "get_user_tasks_data", TaskCollection, dependencies=["user"]
		),
		"challenges": VaultConfig(
			"challenges",
			"challenge_vault",
			"challenges",
			"get_all_user_challenges_data",
			ChallengeCollection,
			dependencies=["user", "tasks"],
		),
	}

	def __init__(self, client: HabiticaClient | None = None) -> None:
		self.client = client or HabiticaClient()
		self.path = app_config.storage.get_database_directory()
		self.path.mkdir(parents=True, exist_ok=True)

		# Inicializar vaults
		self.user_vault = UserVault()
		self.party_vault = PartyVault()
		self.content_vault = ContentVault()
		self.task_vault = TaskVault()
		self.challenge_vault = ChallengeVault()
		self.tag_vault = TagVault()

		self._initialize_collections()
		log.info("[i]Vault[/i] initialized.")

	def _initialize_collections(self) -> None:
		self.user: UserCollection | None = None
		self.party: PartyCollection | None = None
		self.game_content: ContentCollection | None = None
		self.tasks: TaskCollection | None = None
		self.tags: TagCollection | None = None
		self.challenges: ChallengeCollection | None = None

	def _get_vault_by_type(self, vault_type: VaultType):
		vault_map = {
			"user": self.user_vault,
			"party": self.party_vault,
			"content": self.content_vault,
			"tasks": self.task_vault,
			"challenges": self.challenge_vault,
			"tags": self.tag_vault,
		}
		return vault_map.get(vault_type)

	def _vault_is_ready(self, vault_type: VaultType) -> tuple[bool, list[str]]:
		issues: list[str] = []
		try:
			if vault_type not in self.VAULT_CONFIGS:
				issues.append(f"Unknown vault type: {vault_type}")
				return False, issues

			vault = self._get_vault_by_type(vault_type)
			if not vault:
				issues.append(f"Vault not found: {vault_type}")
				return False, issues

			return vault.is_vault_ready_for_load()
		except Exception as e:
			issues.append(f"Error checking vault readiness: {e!s}")
			return False, issues

	def _load_from_database(self, vault_type: VaultType) -> Any | None:
		try:
			vault = self._get_vault_by_type(vault_type)
			if not vault:
				log.error("Unknown vault type: {}", vault_type)
				return None

			loaded_data = vault.load()
			if loaded_data:
				log.debug("{} data loaded successfully from database", vault_type.title())
				return loaded_data

			log.debug("No {} data found in database", vault_type)
			return None
		except Exception as e:
			log.error("Failed to load {} data from database: {}", vault_type, str(e))
			return None

	def _get_collection_attr(self, vault_type: VaultType):
		"""Obtiene el atributo de colección para el vault_type"""
		config = self.VAULT_CONFIGS.get(vault_type)
		return getattr(self, config.collection_attr) if config else None

	def _set_collection_attr(self, vault_type: VaultType, value):
		"""Establece el atributo de colección para el vault_type"""
		config = self.VAULT_CONFIGS.get(vault_type)
		if config:
			setattr(self, config.collection_attr, value)

	async def _fetch_and_process_data(self, vault_type: VaultType, mode: SaveStrategy, debug: bool) -> Any:
		"""Método genérico para obtener datos de la API y procesarlos"""
		config = self.VAULT_CONFIGS[vault_type]

		try:
			# Obtener datos de la API
			api_method = getattr(self.client, config.fetch_method)
			api_data = await api_method()

			# Procesar según el tipo
			if vault_type == "user":
				return await self._process_user_data(api_data, mode, debug)
			elif vault_type == "challenges":
				return self._process_challenges_data(api_data)
			else:
				return self._process_generic_data(vault_type, api_data)

		except Exception as e:
			log.error("Failed to fetch {} content: {}", vault_type, str(e))
			raise

	def _process_generic_data(self, vault_type: VaultType, api_data: Any) -> Any:
		"""Procesa datos genéricos"""
		config = self.VAULT_CONFIGS[vault_type]

		if vault_type == "content":
			return config.collection_class.from_api_data(api_data)
		elif vault_type == "party":
			return config.collection_class.from_api_data(cast("dict", api_data))
		elif vault_type == "tags":
			return config.collection_class.from_api_data(cast("list", api_data))
		elif vault_type == "tasks":
			return config.collection_class.from_api_data(
				cast("SuccessfulResponseData", api_data), cast("UserCollection", self.user)
			)
		else:
			return config.collection_class.from_api_data(api_data)

	async def _process_user_data(self, api_data: Any, mode: SaveStrategy, debug: bool) -> UserCollection:
		"""Procesa datos de usuario y tags"""
		temp_user = UserCollection.from_api_data(cast("dict", api_data), cast("ContentCollection", self.game_content))

		# Procesar tags del usuario
		temp_tags = TagCollection.from_api_data(cast("list", api_data.get("tags", {})))
		self.tag_vault.save(temp_tags, mode, debug)
		self.tags = self._load_from_database("tags")

		return temp_user

	def _process_challenges_data(self, api_data: Any) -> ChallengeCollection:
		"""Procesa datos de challenges"""
		return ChallengeCollection.from_api_data(
			challenges_data=api_data,
			user=self.user,
			tasks=self.tasks,
		)

	async def _ensure_dependencies(self, vault_type: VaultType, mode: SaveStrategy, debug: bool, force: bool):
		"""Asegura que las dependencias estén cargadas"""
		config = self.VAULT_CONFIGS[vault_type]

		for dep in config.dependencies:
			if self._get_collection_attr(dep) is None:
				log.warning(f"{dep.title()} data not loaded, fetching {dep} data first...")
				await self._get_data_generic(dep, mode, debug, force)

	async def _get_data_generic(
		self, vault_type: VaultType, mode: SaveStrategy, debug: bool, force: bool = False
	) -> None:
		"""Método genérico para obtener cualquier tipo de datos"""
		log.debug("Processing {} content...", vault_type)

		if vault_type not in self.VAULT_CONFIGS:
			log.error("Unknown vault type: {}", vault_type)
			return

		# Verificar si ya está cargado (si no es force)
		if not force:
			valid, issues = self._vault_is_ready(vault_type)
			if valid:
				collection = self._load_from_database(vault_type)
				if collection:
					self._set_collection_attr(vault_type, collection)
					return

			if issues:
				log.debug("{} vault issues: {}", vault_type.title(), ", ".join(issues))

		# Asegurar dependencias
		await self._ensure_dependencies(vault_type, mode, debug, force)

		log.debug("Fetching fresh {} content from API...", vault_type)

		try:
			# Obtener y procesar datos
			temp_collection = await self._fetch_and_process_data(vault_type, mode, debug)

			# Guardar y cargar desde base de datos
			vault = self._get_vault_by_type(vault_type)
			vault.save(temp_collection, mode, debug)  # type: ignore
			collection = self._load_from_database(vault_type)

			if collection:
				self._set_collection_attr(vault_type, collection)
				log.debug("{} content fetched, saved, and loaded from database", vault_type.title())
			else:
				log.error("Failed to load {} content from database after saving", vault_type)

		except Exception as e:
			log.error("Failed to fetch {} content: {}", vault_type, str(e))
			raise

	# Métodos especiales que necesitan lógica específica
	async def _get_user_data_with_inbox(self, mode: SaveStrategy, debug: bool, force: bool = False) -> None:
		"""Versión especial para obtener datos de usuario con inbox completo"""
		log.debug("Processing user content with inbox...")
		inbox_count_valid = False

		if not force:
			valid, issues = self._vault_is_ready("user")
			if valid:
				try:
					inbox_count = self.user_vault.count(UserMessage)
					inbox_count_valid = inbox_count > INBOX_MINIMAL
					if inbox_count_valid:
						self.user = self._load_from_database("user")
						if self.user:
							return
					else:
						issues.append(f"Insufficient inbox messages: {inbox_count} <= {INBOX_MINIMAL}")
				except Exception as e:
					issues.append(f"Error checking inbox count: {e!s}")

			if issues:
				log.debug("User vault issues: {}", ", ".join(issues))

		# Asegurar dependencias
		if not self.game_content:
			await self._get_data_generic("content", mode, debug, force)

		log.debug("Fetching fresh user content with full inbox from API...")

		try:
			user_content = await self.client.get_current_user_data()
			inbox_content = await self.client.get_all_inbox_messages_data()

			# Merge inbox messages
			for ibx in inbox_content:
				user_content["inbox"]["messages"].update({ibx.get("_id"): ibx})

			temp_user = UserCollection.from_api_data(
				cast("dict", user_content),
				cast("ContentCollection", self.game_content),
			)

			self.user_vault.save(temp_user, mode, debug)
			self.user = self._load_from_database("user")

			if self.user:
				log.debug("User content with inbox fetched, saved, and loaded from database")
			else:
				log.error("Failed to load user content from database after saving")

		except Exception as e:
			log.error("Failed to fetch user content with inbox: {}", str(e))
			raise

	# Métodos de actualización individuales - ahora usando el método genérico
	async def update_tags_only(self, mode: SaveStrategy = "smart", debug: bool = False, force: bool = False) -> None:
		log.info("Updating tags only...")
		await self._get_data_generic("tags", mode, debug, force)
		log.success("Tags update completed")

	async def update_tasks_only(self, mode: SaveStrategy = "smart", debug: bool = False, force: bool = False) -> None:
		log.info("Updating tasks only...")
		await self._get_data_generic("tasks", mode, debug, force)
		log.success("Tasks update completed")

	async def update_user_only(
		self, mode: SaveStrategy = "smart", debug: bool = False, force: bool = False, with_inbox: bool = False
	) -> None:
		log.info("Updating user data only...")

		if with_inbox:
			await self._get_user_data_with_inbox(mode, debug, force)
		else:
			await self._get_data_generic("user", mode, debug, force)

		log.success("User data update completed")

	async def update_party_only(self, mode: SaveStrategy = "smart", debug: bool = False, force: bool = False) -> None:
		log.info("Updating party data only...")
		await self._get_data_generic("party", mode, debug, force)
		log.success("Party data update completed")

	async def update_challenges_only(
		self, mode: SaveStrategy = "smart", debug: bool = False, force: bool = False
	) -> None:
		log.info("Updating challenges only...")
		await self._get_data_generic("challenges", mode, debug, force)
		log.success("Challenges update completed")

	async def update_content_only(self, mode: SaveStrategy = "smart", debug: bool = False, force: bool = False) -> None:
		log.info("Updating game content only...")
		await self._get_data_generic("content", mode, debug, force)
		log.info("Game content update completed")

	# Método principal de obtención de datos
	async def get_data(
		self,
		mode: SaveStrategy,
		debug: bool,
		force: bool = False,
		with_inbox: bool = False,
		with_challenges: bool = False,
	) -> None:
		if force:
			log.debug("Clearing existing data for force refresh")
			self.clear_data()
			log.info("Force-refreshing all data...")

		try:
			# Orden de carga según dependencias
			load_order = ["content", "party", "tags"]

			if with_inbox:
				load_order.append("user_with_inbox")
			else:
				load_order.append("user")

			load_order.append("tasks")

			if with_challenges:
				load_order.append("challenges")

			# Cargar datos en orden
			for data_type in load_order:
				if data_type == "user_with_inbox":
					await self._get_user_data_with_inbox(mode, debug, force)
				else:
					await self._get_data_generic(cast("VaultType", data_type), mode, debug, force)

				# Validaciones críticas
				if data_type in ["content", "user", "user_with_inbox"]:
					collection = self._get_collection_attr("content" if data_type == "content" else "user")
					if collection is None:
						log.error(f"{data_type.title()} content failed to load, aborting data fetch")
						return

			log.success("Data fetching completed successfully")

		except Exception as e:
			log.error("Error during data fetching: {}", str(e))
			raise

	# Context manager
	async def __aenter__(self) -> Self:
		log.info("Entering DataVault context manager")
		await self.get_data(mode="smart", debug=True, force=False)
		return self

	async def __aexit__(
		self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: object
	) -> None:
		if exc_type:
			log.error("Exiting DataVault context manager due to exception: {}", str(exc_val))
		else:
			log.info("Exiting DataVault context manager successfully")

	# Métodos de utilidad
	def is_data_loaded(self, with_challenges: bool = False) -> bool:
		required_attrs = ["user", "party", "game_content", "tasks", "tags"]
		if with_challenges:
			required_attrs.append("challenges")

		missing_items = [name for name in required_attrs if getattr(self, name) is None]

		if missing_items:
			log.debug("Missing data items: {}", ", ".join(missing_items))
			return False

		log.debug("All required data is loaded")
		return True

	def clear_data(self) -> None:
		log.debug("Clearing all cached data")
		self._initialize_collections()
		log.debug("All data cleared")

	def get_data_summary(self) -> dict[str, Any]:
		summary = {
			"user_loaded": self.user is not None,
			"party_loaded": self.party is not None,
			"game_content_loaded": self.game_content is not None,
			"tasks_loaded": self.tasks is not None,
			"tags_loaded": self.tags is not None,
			"challenges_loaded": self.challenges is not None,
			"tasks_count": len(self.tasks.all_tasks) if self.tasks else 0,
			"challenges_count": len(self.challenges.challenges) if self.challenges else 0,
			"tags_count": len(self.tags) if self.tags else 0,
		}
		log.debug("Data summary: {}", summary)
		return summary

	# Métodos de refresh - usando el método genérico
	async def refresh_quick(self, force: bool = False) -> None:
		await self._get_data_generic("user", "smart", False, force)
		await self._get_data_generic("tasks", "smart", False, force)
		await self._get_data_generic("tags", "smart", False, force)

	async def refresh_standard(self, force: bool = False) -> None:
		await self.get_data("smart", False, force, with_inbox=False, with_challenges=False)

	async def refresh_with_challenges(self, force: bool = False) -> None:
		await self.get_data("smart", False, force, with_inbox=False, with_challenges=True)

	async def refresh_with_full_inbox(self, force: bool = False) -> None:
		await self.get_data("smart", False, force, with_inbox=True, with_challenges=False)

	async def refresh_everything(self, force: bool = False) -> None:
		await self.get_data("smart", False, force, with_inbox=True, with_challenges=True)

	async def sync_tasks_only(self, force: bool = False) -> None:
		await self.update_tasks_only("smart", False, force)

	async def sync_user_only(self, force: bool = False) -> None:
		await self.update_user_only("smart", False, force)

	# Métodos ensure - usando generación dinámica
	def _create_ensure_method(self, vault_type: VaultType, collection_type: type):
		"""Crea dinámicamente métodos ensure_*_loaded"""

		def ensure_loaded(self):
			collection = self._get_collection_attr(vault_type)
			if collection is None:
				raise ValueError(f"{vault_type.title()} data not loaded. Call get_data() first.")
			return collection

		return ensure_loaded

	def ensure_user_loaded(self) -> UserCollection:
		return self._create_ensure_method("user", UserCollection)(self)

	def ensure_tasks_loaded(self) -> TaskCollection:
		return self._create_ensure_method("tasks", TaskCollection)(self)

	def ensure_game_content_loaded(self) -> ContentCollection:
		return self._create_ensure_method("content", ContentCollection)(self)

	def ensure_party_loaded(self) -> PartyCollection:
		return self._create_ensure_method("party", PartyCollection)(self)

	def ensure_tags_loaded(self) -> TagCollection:
		return self._create_ensure_method("tags", TagCollection)(self)

	def ensure_challenges_loaded(self) -> ChallengeCollection:
		return self._create_ensure_method("challenges", ChallengeCollection)(self)
