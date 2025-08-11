# ♥♥─── Database Service ─────────────────────────────────────────────────────────
from __future__ import annotations

from typing import Any, Self, Literal, cast

from pyxabit.client import HabiticaClient
from pyxabit.models.tag_model import TagCollection
from pyxabit.config.app_config import app_config
from pyxabit.models.task_model import TaskCollection
from pyxabit.models.user_model import UserCollection
from pyxabit.models.party_model import PartyCollection
from pyxabit.models.content_model import ContentCollection
from pyxabit.models.message_model import UserMessage
from pyxabit.console.global_logging import log
from pyxabit.models.challenge_model import ChallengeCollection
from pyxabit.repositories.tag_vault import TagVault
from pyxabit.repositories.task_vault import TaskVault
from pyxabit.repositories.user_vault import UserVault
from pyxabit.repositories.party_vault import PartyVault
from pyxabit.repositories.content_vault import ContentVault
from pyxabit.repositories.generic_vault import SaveStrategy
from pyxabit.repositories.challenge_vault import ChallengeVault


SuccessfulResponseData = dict[str, Any] | list[dict[str, Any]] | list[Any] | None
VaultType = Literal["user", "party", "content", "tasks", "challenges", "tags"]
INBOX_MINIMAL = 201


# ─── DataVault ─────────────────────────────────────────────────────────────────
class DataVault:
	"""Database vault manager for Habitica data storage and retrieval."""

	def __init__(
		self,
		client: HabiticaClient | None = None,
	) -> None:
		"""Initialize the DataVault with all necessary components.

		:param client: Optional HabiticaClient instance.
		"""
		self.client = client or HabiticaClient()

		self._initialize_vaults()
		self.path = app_config.storage.get_database_directory()
		self.path.mkdir(parents=True, exist_ok=True)
		self._initialize_collections()

		log.info(
			"[i]Vault[/i] initialized.",
		)

	def _initialize_vaults(self) -> None:
		"""Initialize all database vault instances."""
		log.debug("Initializing database vaults...")

		try:
			self.user_vault = UserVault()
			self.party_vault = PartyVault()
			self.content_vault = ContentVault()
			self.task_vault = TaskVault()
			self.challenge_vault = ChallengeVault()
			self.tag_vault = TagVault()
			log.success("All [i]vaults[/i] initialized successfully")

		except Exception as e:
			log.error("Failed to initialize database vaults: {}", str(e))
			raise

	def _initialize_collections(self) -> None:
		"""Initialize all collection attributes to None."""
		self.user: UserCollection | None = None
		self.party: PartyCollection | None = None
		self.game_content: ContentCollection | None = None
		self.tasks: TaskCollection | None = None
		self.tags: TagCollection | None = None
		self.challenges: ChallengeCollection | None = None

	def _vault_is_ready(self, vault_type: VaultType) -> tuple[bool, list[str]]:
		"""Check if a specific vault is ready for loading.

		:param vault_type: The type of vault to check.
		:returns: (is_ready: bool, issues: list[str])
		"""
		issues: list[str] = []

		try:
			vault_map = {
				"user": self.user_vault,
				"party": self.party_vault,
				"content": self.content_vault,
				"tasks": self.task_vault,
				"challenges": self.challenge_vault,
				"tags": self.tag_vault,
			}

			if vault_type not in vault_map:
				issues.append(f"Unknown vault type: {vault_type}")

				return False, issues

			vault = vault_map[vault_type]
			result: tuple[bool, list[str]] = vault.is_vault_ready_for_load()

		except Exception as e:
			issues.append(f"Error checking vault readiness: {e!s}")

			return False, issues

		else:
			return result

	def _load_from_database(self, vault_type: VaultType) -> Any | None:
		"""Load data from pyxabit.database vault.

		:param vault_type: The type of vault to load from.
		:returns: Loaded data or None if loading fails.
		"""
		try:
			vault_map = {
				"user": self.user_vault,
				"party": self.party_vault,
				"content": self.content_vault,
				"tasks": self.task_vault,
				"challenges": self.challenge_vault,
				"tags": self.tag_vault,
			}
			vault = vault_map.get(vault_type)

			if not vault:
				log.error("Unknown vault type: {}", vault_type)

				return None

			loaded_data = vault.load()

		except Exception as e:
			log.error("Failed to load {} data from pyxabit.database: {}", vault_type, str(e))

			return None

		else:
			if loaded_data:
				log.debug("{} data loaded successfully from pyxabit.database", vault_type.title())

				return loaded_data

			log.debug("No {} data found in database", vault_type)

			return None

	async def _get_game_content(
		self,
		mode: SaveStrategy,
		debug: bool,
		force: bool = False,
	) -> None:
		"""Fetch and store game content with Single Source of Truth pattern.

		:param mode: The saving strategy to use.
		:param debug: Whether to enable debug mode for saving.
		:param force: Whether to force a refresh from the API, defaults to False.
		"""
		log.debug("Processing game content...")

		if not force:
			valid, issues = self._vault_is_ready("content")

			if valid:
				self.game_content = self._load_from_database("content")

				if self.game_content:
					return

		if not force:
			log.debug(
				"Game content vault issues: {}",
				", ".join(issues) if "issues" in locals() else "No valid data",
			)

		log.debug("Fetching fresh game content from API...")

		try:
			content_data = await self.client.get_game_content()
			temp_content = ContentCollection.from_api_data(content_data)
			self.content_vault.save(temp_content, mode, debug)
			self.game_content = self._load_from_database("content")

			if self.game_content:
				log.debug("Game content fetched, saved, and loaded from pyxabit.database")

			else:
				log.error("Failed to load game content from pyxabit.database after saving")

		except Exception as e:
			log.error("Failed to fetch game content: {}", str(e))
			raise

	async def _get_party_content(
		self,
		mode: SaveStrategy,
		debug: bool,
		force: bool = False,
	) -> None:
		"""Fetch and store party content with Single Source of Truth pattern.

		:param mode: The saving strategy to use.
		:param debug: Whether to enable debug mode for saving.
		:param force: Whether to force a refresh from the API, defaults to False.
		"""
		log.debug("Processing party content...")

		if not force:
			valid, issues = self._vault_is_ready("party")

			if valid:
				self.party = self._load_from_database("party")

				if self.party:
					return

		if not force:
			log.debug(
				"Party vault issues: {}",
				", ".join(issues) if "issues" in locals() else "No valid data",
			)

		log.debug("Fetching fresh party content from API...")

		try:
			party_content = await self.client.get_current_party_data()
			temp_party = PartyCollection.from_api_data(cast("dict", party_content))
			self.party_vault.save(temp_party, mode, debug)
			self.party = self._load_from_database("party")

			if self.party:
				log.debug("Party content fetched, saved, and loaded from pyxabit.database")

			else:
				log.error("Failed to load party content from pyxabit.database after saving")

		except Exception as e:
			log.error("Failed to fetch party content: {}", str(e))
			raise

	async def _get_user_data(
		self,
		mode: SaveStrategy,
		debug: bool,
		force: bool = False,
	) -> None:
		"""Fetch and store user data with Single Source of Truth pattern.

		:param mode: The saving strategy to use.
		:param debug: Whether to enable debug mode for saving.
		:param force: Whether to force a refresh from the API, defaults to False.
		"""
		log.debug("Processing user content...")

		if not force:
			valid, issues = self._vault_is_ready("user")

			if valid:
				self.user = self._load_from_database("user")

				if self.user:
					return

		if not force:
			log.debug(
				"User vault issues: {}",
				", ".join(issues) if "issues" in locals() else "No valid data",
			)

		log.debug("Fetching fresh user content from API...")

		try:
			user_content = await self.client.get_current_user_data()
			temp_user = UserCollection.from_api_data(
				cast("dict", user_content),
				cast("ContentCollection", self.game_content),
			)
			self.user_vault.save(temp_user, mode, debug)
			self.user = self._load_from_database("user")

			if self.user:
				log.debug("User content fetched, saved, and loaded from pyxabit.database")

			else:
				log.error("Failed to load user content from pyxabit.database after saving")
			temp_tags = TagCollection.from_api_data(cast("list", user_content.get("tags", {})))
			self.tag_vault.save(temp_tags, mode, debug)
			self.tags = self._load_from_database("tags")
		except Exception as e:
			log.error("Failed to fetch user content: {}", str(e))
			raise

	async def _get_user_data_with_inbox(
		self,
		mode: SaveStrategy,
		debug: bool,
		force: bool = False,
	) -> None:
		"""Fetch and store user data, including all inbox messages.

		:param mode: The saving strategy to use.
		:param debug: Whether to enable debug mode for saving.
		:param force: Whether to force a refresh from the API, defaults to False.
		"""
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
						issues.append(f"Insufficient inbox messages: {inbox_count} <= 210")

				except Exception as e:
					issues.append(f"Error checking inbox count: {e!s}")

		if not force:
			log.debug(
				"User vault issues: {}",
				", ".join(issues) if "issues" in locals() else "No valid data",
			)

		log.debug("Fetching fresh user content with full inbox from API...")

		try:
			user_content = await self.client.get_current_user_data()
			inbox_content = await self.client.get_all_inbox_messages_data()
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
				log.error("Failed to load user content from pyxabit.database after saving")

		except Exception as e:
			log.error("Failed to fetch user content with inbox: {}", str(e))
			raise

	async def _get_tasks_data(
		self,
		mode: SaveStrategy,
		debug: bool,
		force: bool = False,
	) -> None:
		"""Fetch and store tasks data with Single Source of Truth pattern.

		:param mode: The saving strategy to use.
		:param debug: Whether to enable debug mode for saving.
		:param force: Whether to force a refresh from the API, defaults to False.
		"""
		log.debug("Processing tasks content...")

		if not force:
			valid, issues = self._vault_is_ready("tasks")

			if valid:
				self.tasks = self._load_from_database("tasks")

				if self.tasks:
					return

		if not force:
			log.debug(
				"Tasks vault issues: {}",
				", ".join(issues) if "issues" in locals() else "No valid data",
			)

		log.debug("Fetching fresh tasks content from API...")

		try:
			tasks_content = await self.client.get_user_tasks_data()
			temp_tasks = TaskCollection.from_api_data(
				cast("SuccessfulResponseData", tasks_content),
				cast("UserCollection", self.user),
			)
			self.task_vault.save(temp_tasks, mode, debug)
			self.tasks = self._load_from_database("tasks")

			if self.tasks:
				log.debug("Tasks content fetched, saved, and loaded from pyxabit.database")

			else:
				log.error("Failed to load tasks content from pyxabit.database after saving")

		except Exception as e:
			log.error("Failed to fetch tasks content: {}", str(e))
			raise

	async def _get_tags_data(self, mode: SaveStrategy, debug: bool, force: bool = False) -> None:
		"""Fetch and store tags data with Single Source of Truth pattern.

		:param mode: The saving strategy to use.
		:param debug: Whether to enable debug mode for saving.
		:param force: Whether to force a refresh from the API, defaults to False.
		"""
		log.debug("Processing tags content...")

		if not force:
			valid, issues = self._vault_is_ready("tags")

			if valid:
				self.tags = self._load_from_database("tags")

				if self.tags:
					return

		if not force:
			log.debug(
				"Tags vault issues: {}",
				", ".join(issues) if "issues" in locals() else "No valid data",
			)

		log.debug("Fetching fresh tags content from API...")

		try:
			tags_content = await self.client.get_all_tags_data()
			temp_tags = TagCollection.from_api_data(cast("list", tags_content))
			self.tag_vault.save(temp_tags, mode, debug)
			self.tags = self._load_from_database("tags")

			if self.tags:
				log.debug("Tags content fetched, saved, and loaded from pyxabit.database")

			else:
				log.error("Failed to load tags content from pyxabit.database after saving")

		except Exception as e:
			log.error("Failed to fetch tags content: {}", str(e))
			raise

	async def _get_challenges_data(
		self,
		mode: SaveStrategy,
		debug: bool,
		force: bool = False,
	) -> None:
		"""Fetch and store challenges data with Single Source of Truth pattern.

		:param mode: The saving strategy to use.
		:param debug: Whether to enable debug mode for saving.
		:param force: Whether to force a refresh from the API, defaults to False.
		"""
		log.debug("Processing challenges content...")

		if not force:
			valid, issues = self._vault_is_ready("challenges")

			if valid:
				self.challenges = self._load_from_database("challenges")

				if self.challenges:
					return

		if not force:
			log.debug(
				"Challenges vault issues: {}",
				", ".join(issues) if "issues" in locals() else "No valid data",
			)

		log.debug("Fetching fresh challenges content from API...")

		try:
			challenge_content = await self.client.get_all_user_challenges_data()
			temp_challenges = ChallengeCollection.from_api_data(
				challenges_data=challenge_content,
				user=self.user,
				tasks=self.tasks,
			)
			self.challenge_vault.save(temp_challenges, mode, debug)
			self.challenges = self._load_from_database("challenges")

			if self.challenges:
				log.debug("Challenges content fetched, saved, and loaded from pyxabit.database")

			else:
				log.error("Failed to load challenges content from database after saving")

		except Exception as e:
			log.error("Failed to fetch challenges content: {}", str(e))
			raise

	# ─── Public Update Methods ───────────────────────────────────────────────────
	async def update_tags_only(
		self,
		mode: SaveStrategy = "smart",
		debug: bool = False,
		force: bool = False,
	) -> None:
		"""Updates only the tags data without affecting other data.

		:param mode: The saving strategy to use (e.g., "smart", "overwrite").
		:param debug: If True, enable debug logging for the operation.
		:param force: If True, force a refresh from the API, ignoring cached data.
		"""
		log.info("Updating tags only...")

		await self._get_tags_data(mode, debug, force)
		log.success("Tags update completed")

	async def update_tasks_only(
		self,
		mode: SaveStrategy = "smart",
		debug: bool = False,
		force: bool = False,
	) -> None:
		"""Updates only the tasks data without affecting other data.

		:param mode: The saving strategy to use (e.g., "smart", "overwrite").
		:param debug: If True, enable debug logging for the operation.
		:param force: If True, force a refresh from the API, ignoring cached data.
		"""
		log.info("Updating tasks only...")

		if not self.user:
			log.warning("User data not loaded, fetching user data first...")
			await self._get_user_data(mode, debug, force)

		await self._get_tasks_data(mode, debug, force)
		log.success("Tasks update completed")

	async def update_user_only(
		self,
		mode: SaveStrategy = "smart",
		debug: bool = False,
		force: bool = False,
		with_inbox: bool = False,
	) -> None:
		"""Updates only the user data without affecting other data.

		:param mode: The saving strategy to use (e.g., "smart", "overwrite").
		:param debug: If True, enable debug logging for the operation.
		:param force: If True, force a refresh from the API, ignoring cached data.
		:param with_inbox: If True, fetch all inbox messages along with user data.
		"""
		log.info("Updating user data only...")

		if not self.game_content:
			log.warning("Game content not loaded, fetching game content first...")
			await self._get_game_content(mode, debug, force)

		if with_inbox:
			await self._get_user_data_with_inbox(mode, debug, force)

		else:
			await self._get_user_data(mode, debug, force)

		log.success("User data update completed")

	async def update_party_only(
		self,
		mode: SaveStrategy = "smart",
		debug: bool = False,
		force: bool = False,
	) -> None:
		"""Updates only the party data without affecting other data.

		:param mode: The saving strategy to use (e.g., "smart", "overwrite").
		:param debug: If True, enable debug logging for the operation.
		:param force: If True, force a refresh from the API, ignoring cached data.
		"""
		log.info("Updating party data only...")

		await self._get_party_content(mode, debug, force)
		log.success("Party data update completed")

	async def update_challenges_only(
		self,
		mode: SaveStrategy = "smart",
		debug: bool = False,
		force: bool = False,
	) -> None:
		"""Updates only the challenges data without affecting other data.

		:param mode: The saving strategy to use (e.g., "smart", "overwrite").
		:param debug: If True, enable debug logging for the operation.
		:param force: If True, force a refresh from the API, ignoring cached data.
		"""
		log.info("Updating challenges only...")

		if not self.user:
			log.warning("User data not loaded, fetching user data first...")
			await self._get_user_data(mode, debug, force)

		if not self.tasks:
			log.warning("Tasks data not loaded, fetching tasks data first...")
			await self._get_tasks_data(mode, debug, force)

		await self._get_challenges_data(mode, debug, force)
		log.success("Challenges update completed")

	async def update_content_only(
		self,
		mode: SaveStrategy = "smart",
		debug: bool = False,
		force: bool = False,
	) -> None:
		"""Updates only the game content without affecting other data.

		:param mode: The saving strategy to use (e.g., "smart", "overwrite").
		:param debug: If True, enable debug logging for the operation.
		:param force: If True, force a refresh from the API, ignoring cached data.
		"""
		log.info("Updating game content only...")

		await self._get_game_content(mode, debug, force)
		log.info("Game content update completed")

	# ─── Public Data Fetching Methods ────────────────────────────────────────────
	async def get_data(
		self,
		mode: SaveStrategy,
		debug: bool,
		force: bool = False,
		with_inbox: bool = False,
		with_challenges: bool = False,
	) -> None:
		"""Main data fetching orchestration with Single Source of Truth pattern.

		This method ensures all data is consistently loaded from the database
		after being saved, maintaining session integrity and data consistency.

		:param mode: The saving strategy to use.
		:param debug: Whether to enable debug mode for saving.
		:param force: Whether to force a refresh from the API, defaults to False.
		:param with_inbox: If True, fetch all inbox messages with user data.
		:param with_challenges: If True, fetch challenges data.
		"""
		if force:
			log.debug("Clearing existing data for force refresh")
			self.clear_data()
			log.info("Force-refreshing all data...")

		try:
			# Phase 1: Game content (prerequisite for everything else)
			await self._get_game_content(mode, debug, force)

			if self.game_content is None:
				log.error("Game content failed to load, aborting data fetch")

				return

			# Phase 2: Party content (independent)
			await self._get_party_content(mode, debug, force)

			# Add tags loading
			await self._get_tags_data(mode, debug, force)

			# Phase 3: User content (prerequisite for tasks and challenges)
			if with_inbox:
				await self._get_user_data_with_inbox(mode, debug, force)

			else:
				await self._get_user_data(mode, debug, force)

			if self.user is None:
				log.error("User content failed to load, skipping dependent data")

				return

			# Phase 4: Tasks content (depends on user)
			await self._get_tasks_data(mode, debug, force)

			# Phase 5: Challenges content (depends on user and tasks)
			if with_challenges:
				await self._get_challenges_data(mode, debug, force)

			log.success("Data fetching completed successfully")

		except Exception as e:
			log.error("Error during data fetching: {}", str(e))
			raise

	# ─── Context Manager Methods ─────────────────────────────────────────────────
	async def __aenter__(self) -> Self:
		"""Context manager entry - automatically fetch and save data.

		:returns: Self, with data fetched and saved.
		"""
		log.info("Entering DataVault context manager")

		await self.get_data(mode="smart", debug=True, force=False)

		return self

	async def __aexit__(
		self,
		exc_type: type[BaseException] | None,
		exc_val: BaseException | None,
		exc_tb: object,
	) -> None:
		"""Context manager exit - log completion and cleanup.

		:param exc_type: Exception type if an exception occurred.
		:param exc_val: Exception value if an exception occurred.
		:param exc_tb: Exception traceback if an exception occurred.
		"""
		if exc_type:
			log.error("Exiting DataVault context manager due to exception: {}", str(exc_val))

		else:
			log.info("Exiting DataVault context manager successfully")

	# ─── Data Status and Utility Methods ─────────────────────────────────────────
	def is_data_loaded(self, with_challenges: bool = False) -> bool:
		"""Check if all required data has been fetched and loaded.

		:param with_challenges: If True, also check if challenges data is loaded.
		:returns: True if all required data is loaded, False otherwise.
		"""
		base_data_items: list[tuple[str, Any | None]] = [
			("user", self.user),
			("party", self.party),
			("game_content", self.game_content),
			("tasks", self.tasks),
			("tags", self.tags),
		]

		if with_challenges:
			base_data_items.append(("challenges", self.challenges))

		missing_items = [name for name, item in base_data_items if item is None]

		if missing_items:
			log.debug("Missing data items: {}", ", ".join(missing_items))

			return False

		log.debug("All required data is loaded")

		return True

	def clear_data(self) -> None:
		"""Clear all cached data and reset to initial state."""
		log.debug("Clearing all cached data")

		self._initialize_collections()
		log.debug("All data cleared")

	def get_data_summary(self) -> dict[str, Any]:
		"""Get a summary of currently loaded data for debugging purposes.

		:returns: Summary of loaded data with counts and basic info.
		"""
		summary = {
			"user_loaded": self.user is not None,
			"party_loaded": self.party is not None,
			"game_content_loaded": self.game_content is not None,
			"tasks_loaded": self.tasks is not None,
			"tags_loaded": self.tags is not None,
			"challenges_loaded": self.challenges is not None,
			"tasks_count": 0,
			"challenges_count": 0,
			"tags_count": 0,
		}

		if self.tasks:
			summary["tasks_count"] = len(self.tasks.all_tasks)

		if self.challenges:
			summary["challenges_count"] = len(self.challenges.challenges) or 0

		if self.tags:
			summary["tags_count"] = len(self.tags) or 0

		log.debug("Data summary: {}", summary)

		return summary

	# ─── Public Refresh/Sync Methods ─────────────────────────────────────────────
	async def refresh_quick(self, force: bool = False) -> None:
		"""Performs a quick refresh of essential user, tasks, and tags data.

		This method is suitable for frequent updates where full data is not
		immediately required.

		:param force: If True, force a refresh from the API, ignoring cached data.
		"""
		await self._get_user_data("smart", False, force)
		await self._get_tasks_data("smart", False, force)
		await self._get_tags_data("smart", False, force)

	async def refresh_standard(self, force: bool = False) -> None:
		"""Performs a standard refresh of all data except inbox and challenges.

		This method is a good balance for general use cases.

		:param force: If True, force a refresh from the API, ignoring cached data.
		"""
		await self.get_data("smart", False, force, with_inbox=False, with_challenges=False)

	async def refresh_with_challenges(self, force: bool = False) -> None:
		"""Performs a refresh including challenges data.

		:param force: If True, force a refresh from the API, ignoring cached data.
		"""
		await self.get_data("smart", False, force, with_inbox=False, with_challenges=True)

	async def refresh_with_full_inbox(self, force: bool = False) -> None:
		"""Performs a refresh including all inbox messages.

		:param force: If True, force a refresh from the API, ignoring cached data.
		"""
		await self.get_data("smart", False, force, with_inbox=True, with_challenges=False)

	async def refresh_everything(self, force: bool = False) -> None:
		"""Performs a comprehensive refresh of all available data.

		This includes user data with a full inbox, party data, game content,
		tasks, tags, and challenges.

		:param force: If True, force a refresh from the API, ignoring cached data.
		"""
		await self.get_data("smart", False, force, with_inbox=True, with_challenges=True)

	async def sync_tasks_only(self, force: bool = False) -> None:
		"""Synchronizes only the tasks data.

		This method is an alias for `update_tasks_only` for clarity.

		:param force: If True, force a refresh from the API, ignoring cached data.
		"""
		await self.update_tasks_only("smart", False, force)

	async def sync_user_only(self, force: bool = False) -> None:
		"""Synchronizes only the user data.

		This method is an alias for `update_user_only` for clarity.

		:param force: If True, force a refresh from the API, ignoring cached data.
		"""
		await self.update_user_only("smart", False, force)

	# Type guards para validar que los datos están cargados
	def ensure_user_loaded(self) -> UserCollection:
		"""Ensure user data is loaded and return it."""
		if self.user is None:
			raise ValueError("User data not loaded. Call get_data() first.")
		return self.user

	def ensure_tasks_loaded(self) -> TaskCollection:
		"""Ensure tasks data is loaded and return it."""
		if self.tasks is None:
			raise ValueError("Tasks data not loaded. Call get_data() first.")
		return self.tasks

	def ensure_game_content_loaded(self) -> ContentCollection:
		"""Ensure game content is loaded and return it."""
		if self.game_content is None:
			raise ValueError("Game content not loaded. Call get_data() first.")
		return self.game_content

	def ensure_party_loaded(self) -> PartyCollection:
		"""Ensure party data is loaded and return it."""
		if self.party is None:
			raise ValueError("Party data not loaded. Call get_data() first.")
		return self.party

	def ensure_tags_loaded(self) -> TagCollection:
		"""Ensure tags data is loaded and return it."""
		if self.tags is None:
			raise ValueError("Tags data not loaded. Call get_data() first.")
		return self.tags

	def ensure_challenges_loaded(self) -> ChallengeCollection:
		"""Ensure challenges data is loaded and return it."""
		if self.challenges is None:
			raise ValueError("Challenges data not loaded. Call get_data() first.")
		return self.challenges
