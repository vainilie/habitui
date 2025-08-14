# ♥♥─── Main Datavault ───────────────────────────────────────────────────────────
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self, Literal, cast
import asyncio
from dataclasses import field, dataclass

from habitui.ui import icons
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


if TYPE_CHECKING:
    from pathlib import Path


# ─── Type Aliases & Constants ──────────────────────────────────────────────────
SuccessfulResponseData = dict[str, Any] | list[dict[str, Any]] | list[Any] | None
VaultType = Literal["user", "party", "content", "tasks", "challenges", "tags"]
AnyVault = UserVault | PartyVault | ContentVault | TaskVault | ChallengeVault | TagVault

INBOX_MINIMAL = 201


# ─── Vault Configuration ───────────────────────────────────────────────────────
@dataclass
class VaultConfig:
    """Configuration for a specific data vault."""

    name: str
    vault_attr: str
    collection_attr: str
    fetch_method: str
    collection_class: type
    dependencies: list[VaultType] = field(default_factory=list)
    requires_cast: bool = True


class DataVault:
    """Manages local data caching and synchronization with the Habitica API."""

    # ─── Class Configuration ───────────────────────────────────────────────────────
    VAULT_CONFIGS: dict[str, VaultConfig] = {
        "content": VaultConfig(
            "content",
            "content_vault",
            "game_content",
            "get_game_content",
            ContentCollection,
        ),
        "party": VaultConfig(
            "party",
            "party_vault",
            "party",
            "get_current_party_data",
            PartyCollection,
        ),
        "user": VaultConfig(
            "user",
            "user_vault",
            "user",
            "get_current_user_data",
            UserCollection,
            dependencies=["content"],
        ),
        "tags": VaultConfig(
            "tags",
            "tag_vault",
            "tags",
            "get_all_tags_data",
            TagCollection,
            requires_cast=False,
        ),
        "tasks": VaultConfig(
            "tasks",
            "task_vault",
            "tasks",
            "get_user_tasks_data",
            TaskCollection,
            dependencies=["user"],
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

    # ─── Initialization ────────────────────────────────────────────────────────────
    def __init__(self, client: HabiticaClient | None = None) -> None:
        """Initialize the DataVault and its underlying repository vaults."""
        self.client: HabiticaClient = client or HabiticaClient()
        self.path: Path = app_config.storage.get_database_directory()
        self.path.mkdir(parents=True, exist_ok=True)

        self.user_vault: UserVault = UserVault()
        self.party_vault: PartyVault = PartyVault()
        self.content_vault: ContentVault = ContentVault()
        self.task_vault: TaskVault = TaskVault()
        self.challenge_vault: ChallengeVault = ChallengeVault()
        self.tag_vault: TagVault = TagVault()

        self._initialize_collections()

        log.info(f"{icons.INFO} Vault initialized.")

    def _initialize_collections(self) -> None:
        """Reset all data collections to their initial empty state."""
        self.user: UserCollection | None = None
        self.party: PartyCollection | None = None
        self.game_content: ContentCollection | None = None
        self.tasks: TaskCollection | None = None
        self.tags: TagCollection | None = None
        self.challenges: ChallengeCollection | None = None

    # ─── Public API: Comprehensive Fetch ───────────────────────────────────────────
    async def get_data(
        self,
        mode: SaveStrategy,
        debug: bool,
        force: bool = False,
        with_inbox: bool = False,
        with_challenges: bool = False,
    ) -> None:
        """Fetch all primary data from the API, respecting dependencies."""
        if force:
            log.debug(f"{icons.BUG} Clearing existing data for force refresh.")
            self.clear_data()
            log.info(f"{icons.INFO} Force-refreshing all data...")

        try:
            # Step 1: Fetch independent data concurrently
            log.info(f"{icons.INFO} Loading concurrent data (content, party)...")
            await asyncio.gather(
                self._get_data_generic("content", mode, debug, force),
                self._get_data_generic("party", mode, debug, force),
                self._get_data_generic("tags", mode, debug, force),  # ← AGREGAR ESTO
            )

            # Step 2: Load user data (depends on content)
            if self.game_content is None:
                log.error(f"{icons.ERROR} Game content failed to load, aborting.")
                return

            log.info(f"{icons.INFO} Loading user data...")
            if with_inbox:
                await self._get_user_data_with_inbox(mode, debug, force)
            else:
                await self._get_data_generic("user", mode, debug, force)

            # Step 3: Load tasks (depends on user)
            if self.user is None:
                log.error(
                    f"{icons.ERROR} User content failed to load, skipping dependent data.",
                )
                return

            log.info(f"{icons.INFO} Loading tasks...")
            await self._get_data_generic("tasks", mode, debug, force)

            # Step 4: Load challenges (depends on tasks)
            if with_challenges:
                if self.tasks is None:
                    log.error(
                        f"{icons.ERROR} Tasks failed to load, cannot load challenges.",
                    )
                    return

                log.info(f"{icons.INFO} Loading challenges...")
                await self._get_data_generic("challenges", mode, debug, force)

            log.success(f"{icons.CHECK} Data fetching completed successfully.")

        except Exception as e:
            log.error(f"{icons.ERROR} Error during data fetching: {e!s}")
            raise

    # ─── Public API: Granular Updates ──────────────────────────────────────────────
    async def update_user_only(
        self,
        mode: SaveStrategy = "smart",
        debug: bool = False,
        force: bool = False,
        with_inbox: bool = False,
    ) -> None:
        """Fetch or update only the user data."""
        log.info(f"{icons.INFO} Updating user data only...")

        await self._ensure_dependencies("user", mode, debug, force)

        if with_inbox:
            await self._get_user_data_with_inbox(mode, debug, force)
        else:
            await self._get_data_generic("user", mode, debug, force)

        log.success(f"{icons.CHECK} User data update completed.")

    async def update_tasks_only(
        self,
        mode: SaveStrategy = "smart",
        debug: bool = False,
        force: bool = False,
    ) -> None:
        """Fetch or update only the user's tasks."""
        log.info(f"{icons.INFO} Updating tasks only...")

        await self._ensure_dependencies("tasks", mode, debug, force)
        await self._get_data_generic("tasks", mode, debug, force)

        log.success(f"{icons.CHECK} Tasks update completed.")

    async def update_challenges_only(
        self,
        mode: SaveStrategy = "smart",
        debug: bool = False,
        force: bool = False,
    ) -> None:
        """Fetch or update only the user's challenges."""
        log.info(f"{icons.INFO} Updating challenges only...")

        await self._ensure_dependencies("challenges", mode, debug, force)
        await self._get_data_generic("challenges", mode, debug, force)

        log.success(f"{icons.CHECK} Challenges update completed.")

    async def update_tags_only(
        self,
        mode: SaveStrategy = "smart",
        debug: bool = False,
        force: bool = False,
    ) -> None:
        """Fetch or update only the user's tags."""
        log.info(f"{icons.INFO} Updating tags only...")

        await self._get_data_generic("tags", mode, debug, force)

        log.success(f"{icons.CHECK} Tags update completed.")

    async def update_party_only(
        self,
        mode: SaveStrategy = "smart",
        debug: bool = False,
        force: bool = False,
    ) -> None:
        """Fetch or update only the user's party data."""
        log.info(f"{icons.INFO} Updating party data only...")

        await self._get_data_generic("party", mode, debug, force)

        log.success(f"{icons.CHECK} Party data update completed.")

    async def update_content_only(
        self,
        mode: SaveStrategy = "smart",
        debug: bool = False,
        force: bool = False,
    ) -> None:
        """Fetch or update only the game content (e.g., events, gear)."""
        log.info(f"{icons.INFO} Updating game content only...")

        await self._get_data_generic("content", mode, debug, force)

        log.success(f"{icons.CHECK} Game content update completed.")

    # ─── Public API: Refresh Scenarios ─────────────────────────────────────────────
    async def refresh_quick(self, force: bool = False) -> None:
        """Perform a fast refresh of user, tasks, and tags."""
        await self.update_user_only(force=force)
        await self.update_tasks_only(force=force)
        await self.update_tags_only(force=force)

    async def refresh_standard(self, force: bool = False) -> None:
        """Perform a standard, comprehensive data refresh."""
        await self.get_data(
            "smart",
            False,
            force,
            with_inbox=False,
            with_challenges=False,
        )

    async def refresh_with_challenges(self, force: bool = False) -> None:
        """Perform a standard refresh including challenges."""
        await self.get_data(
            "smart",
            False,
            force,
            with_inbox=False,
            with_challenges=True,
        )

    async def refresh_with_full_inbox(self, force: bool = False) -> None:
        """Perform a standard refresh including all inbox messages."""
        await self.get_data(
            "smart",
            False,
            force,
            with_inbox=True,
            with_challenges=False,
        )

    async def refresh_everything(self, force: bool = False) -> None:
        """Perform a full refresh including challenges and all inbox messages."""
        await self.get_data(
            "smart",
            False,
            force,
            with_inbox=True,
            with_challenges=True,
        )

    # ─── Public API: State and Data Access ─────────────────────────────────────────
    def is_data_loaded(self, with_challenges: bool = False) -> bool:
        """Check if all essential data collections are loaded."""
        required_attrs = ["user", "party", "game_content", "tasks", "tags"]
        if with_challenges:
            required_attrs.append("challenges")

        missing_items = [name for name in required_attrs if getattr(self, name) is None]

        if missing_items:
            log.debug(f"{icons.BUG} Missing data items: {', '.join(missing_items)}")

            return False

        log.debug(f"{icons.BUG} All required data is loaded.")

        return True

    def clear_data(self) -> None:
        """Clear all cached data collections from memory."""
        log.debug(f"{icons.BUG} Clearing all cached data collections.")
        self._initialize_collections()
        log.debug(f"{icons.BUG} All data collections cleared.")

    def get_data_summary(self) -> dict[str, Any]:
        """Return a summary of the current data state."""
        summary = {
            "user_loaded": self.user is not None,
            "party_loaded": self.party is not None,
            "game_content_loaded": self.game_content is not None,
            "tasks_loaded": self.tasks is not None,
            "tags_loaded": self.tags is not None,
            "challenges_loaded": self.challenges is not None,
            "tasks_count": len(self.tasks.all_tasks) if self.tasks else 0,
            "challenges_count": len(self.challenges.challenges)
            if self.challenges
            else 0,
            "tags_count": len(self.tags) if self.tags else 0,
        }
        log.debug(f"{icons.BUG} Data summary: {summary}")

        return summary

    def ensure_user_loaded(self) -> UserCollection:
        """Return the UserCollection, raising an error if not loaded."""
        if self.user is None:
            msg = "User data not loaded. Call a fetch method first."
            raise ValueError(msg)

        return self.user

    def ensure_tasks_loaded(self) -> TaskCollection:
        """Return the TaskCollection, raising an error if not loaded."""
        if self.tasks is None:
            msg = "Tasks data not loaded. Call a fetch method first."
            raise ValueError(msg)

        return self.tasks

    def ensure_game_content_loaded(self) -> ContentCollection:
        """Return the ContentCollection, raising an error if not loaded."""
        if self.game_content is None:
            msg = "Game content data not loaded. Call a fetch method first."
            raise ValueError(msg)

        return self.game_content

    def ensure_party_loaded(self) -> PartyCollection:
        """Return the PartyCollection, raising an error if not loaded."""
        if self.party is None:
            msg = "Party data not loaded. Call a fetch method first."
            raise ValueError(msg)

        return self.party

    def ensure_tags_loaded(self) -> TagCollection:
        """Return the TagCollection, raising an error if not loaded."""
        if self.tags is None:
            msg = "Tags data not loaded. Call a fetch method first."
            raise ValueError(msg)

        return self.tags

    def ensure_challenges_loaded(self) -> ChallengeCollection:
        """Return the ChallengeCollection, raising an error if not loaded."""
        if self.challenges is None:
            msg = "Challenges data not loaded. Call a fetch method first."
            raise ValueError(msg)

        return self.challenges

    # ─── Context Manager Protocol ──────────────────────────────────────────────────
    async def __aenter__(self) -> Self:
        """Enter the async context, loading standard data."""
        log.info(f"{icons.INFO} Entering DataVault context.")

        await self.refresh_standard()

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit the async context."""
        if exc_type:
            log.error(f"{icons.ERROR} Exiting DataVault due to exception: {exc_val!s}")
        else:
            log.info(f"{icons.INFO} Exiting DataVault context successfully.")

    # ─── Internal: Core Data Loading Logic ─────────────────────────────────────────
    async def _get_data_generic(
        self,
        vault_type: VaultType,
        mode: SaveStrategy,
        debug: bool,
        force: bool = False,
    ) -> None:
        """Fetch, process, and cache data for any vault type."""
        log.debug(f"{icons.BUG} Processing {vault_type} content...")

        if vault_type not in self.VAULT_CONFIGS:
            log.error(f"{icons.ERROR} Unknown vault type: {vault_type}")

            return

        if not force and self._get_collection_attr(vault_type) is not None:
            log.debug(f"{icons.BUG} {vault_type.title()} is already loaded.")

            return

        # Attempt to load from local cache unless `force` is true
        if not force:
            is_ready, issues = self._vault_is_ready(vault_type)
            if is_ready:
                collection = await self._load_from_database(vault_type)
                if collection:
                    self._set_collection_attr(vault_type, collection)
                    log.debug(
                        f"{icons.BUG} {vault_type.title()} data loaded from database (cache was ready).",
                    )

                    return
                issues.append(
                    f"Failed to load {vault_type} from database despite cache being ready.",
                )
            if issues:
                log.debug(
                    f"{icons.BUG} {vault_type.title()} cache issues: {', '.join(issues)}. Proceeding to API fetch.",
                )

        # Fetch fresh data from the API
        log.debug(f"{icons.BUG} Fetching fresh {vault_type} content from API...")

        await self._ensure_dependencies(vault_type, mode, debug, force)

        try:
            temp_collection = await self._fetch_and_process_data(
                vault_type,
                mode,
                debug,
            )
            vault = self._get_vault_by_type(vault_type)

            if not vault:
                log.error(f"{icons.ERROR} Vault not found for type: {vault_type}")

                return
            await asyncio.to_thread(vault.save, temp_collection, mode, debug)  # type: ignore
            collection = await self._load_from_database(vault_type)

            if collection:
                self._set_collection_attr(vault_type, collection)
                log.debug(
                    f"{icons.BUG} {vault_type.title()} content fetched, saved, and loaded.",
                )
            else:
                log.error(
                    f"{icons.ERROR} Failed to load {vault_type} content from database after saving.",
                )
                msg = f"Failed to load {vault_type} from database"
                raise ValueError(msg)

        except Exception as e:
            log.error(f"{icons.ERROR} Failed to fetch {vault_type} content: {e!s}")
            raise

    async def _get_user_data_with_inbox(
        self,
        mode: SaveStrategy,
        debug: bool,
        force: bool = False,
    ) -> None:
        """Fetch user data and ensure the inbox is fully populated."""
        log.debug(f"{icons.BUG} Processing user content with full inbox...")

        if not force:
            is_ready, issues = self._vault_is_ready("user")
            if is_ready:
                try:
                    inbox_count = await asyncio.to_thread(
                        self.user_vault.count,
                        UserMessage,
                    )
                    if inbox_count > INBOX_MINIMAL:
                        collection = await self._load_from_database("user")
                        if collection:
                            self.user = collection
                            log.debug(
                                f"{icons.BUG} User data with sufficient inbox ({inbox_count}) loaded from cache.",
                            )

                            return
                        issues.append(
                            "Failed to load user from cache despite being ready with sufficient inbox.",
                        )
                    else:
                        issues.append(
                            f"Insufficient inbox messages in cache: {inbox_count} <= {INBOX_MINIMAL}",
                        )
                except Exception as e:
                    issues.append(f"Error checking inbox count: {e!s}")
            if issues:
                log.debug(
                    f"{icons.BUG} User vault (inbox) issues: {', '.join(issues)}. Fetching from API.",
                )

        await self._ensure_dependencies("user", mode, debug, force)
        log.debug(
            f"{icons.BUG} Fetching fresh user content with full inbox from API...",
        )

        try:
            user_content = await self.client.get_current_user_data()
            inbox_content = await self.client.get_all_inbox_messages_data()
            for msg in inbox_content:
                user_content["inbox"]["messages"].update({msg.get("_id"): msg})

            temp_user = await self._process_user_data(user_content, mode, debug)
            await asyncio.to_thread(self.user_vault.save, temp_user, mode, debug)
            self.user = await self._load_from_database("user")

            if self.user:
                count = await asyncio.to_thread(self.user_vault.count, UserMessage)
                log.debug(
                    f"{icons.BUG} User content with inbox fetched and loaded ({count} messages).",
                )
            else:
                log.error(
                    f"{icons.ERROR} Failed to load user content from database after saving.",
                )

        except Exception as e:
            log.error(f"{icons.ERROR} Failed to fetch user content with inbox: {e!s}")
            raise

    # ─── Internal: Data Processing Helpers ─────────────────────────────────────────
    async def _fetch_and_process_data(
        self,
        vault_type: VaultType,
        mode: SaveStrategy,
        debug: bool,
    ) -> Any:
        """Fetch raw data from the API and delegate to the correct processor."""
        config = self.VAULT_CONFIGS[vault_type]

        try:
            api_method = getattr(self.client, config.fetch_method)
            api_data = await api_method()

            if vault_type == "user":
                return await self._process_user_data(api_data, mode, debug)

            if vault_type == "challenges":
                return self._process_challenges_data(api_data)

            if vault_type == "tasks":
                return self._process_tasks_data(api_data)

            return self._process_generic_data(vault_type, api_data)

        except Exception as e:
            log.error(f"{icons.ERROR} Failed to fetch {vault_type} content: {e!s}")
            raise

    async def _process_user_data(
        self,
        api_data: Any,
        mode: SaveStrategy,
        debug: bool,
    ) -> UserCollection:
        """Process user data, which includes handling embedded tags."""
        game_content = self.ensure_game_content_loaded()
        temp_user = UserCollection.from_api_data(cast("dict", api_data), game_content)

        # User data contains tags, so we can update them at the same time
        temp_tags = TagCollection.from_api_data(cast("list", api_data.get("tags", [])))
        await asyncio.to_thread(self.tag_vault.save, temp_tags, mode, debug)
        self.tags = await self._load_from_database("tags")
        return temp_user

    def _process_tasks_data(self, api_data: Any) -> TaskCollection:
        """Process tasks data, which depends on user data."""
        user = self.ensure_user_loaded()

        return TaskCollection.from_api_data(
            cast("SuccessfulResponseData", api_data),
            user,
        )

    def _process_challenges_data(self, api_data: Any) -> ChallengeCollection:
        """Process challenges data, which depends on user and task data."""
        user = self.ensure_user_loaded()
        tasks = self.ensure_tasks_loaded()

        return ChallengeCollection.from_api_data(
            challenges_data=api_data,
            user=user,
            tasks=tasks,
        )

    def _process_generic_data(self, vault_type: VaultType, api_data: Any) -> Any:
        """Process data for simple collections without complex dependencies."""
        config = self.VAULT_CONFIGS[vault_type]

        if config.requires_cast:
            return config.collection_class.from_api_data(cast("dict | list", api_data))

        return config.collection_class.from_api_data(api_data)

    # ─── Internal: State & Dependency Helpers ──────────────────────────────────────
    async def _ensure_dependencies(
        self,
        vault_type: VaultType,
        mode: SaveStrategy,
        debug: bool,
        force: bool,
    ) -> None:
        """Recursively fetch and load any missing dependencies for a vault type."""
        config = self.VAULT_CONFIGS[vault_type]

        for dep in config.dependencies:
            if self._get_collection_attr(dep) is None:
                log.warning(
                    f"{icons.WARNING} Dependency '{dep}' not loaded. Fetching it first...",
                )
                await self._get_data_generic(dep, mode, debug, force)

                if self._get_collection_attr(dep) is None:
                    msg = f"Failed to load required dependency: {dep}"
                    raise ValueError(msg)

    def _vault_is_ready(self, vault_type: VaultType) -> tuple[bool, list[str]]:
        """Check if a local vault file is present and valid for loading."""
        issues: list[str] = []
        try:
            vault = self._get_vault_by_type(vault_type)
            if not vault:
                issues.append(f"Vault not found: {vault_type}")

                return False, issues

            return vault.is_vault_ready_for_load()

        except Exception as e:
            issues.append(f"Error checking vault readiness: {e!s}")

            return False, issues

    async def _load_from_database(self, vault_type: VaultType) -> Any | None:
        """Load a data collection from its corresponding vault file."""
        try:
            vault = self._get_vault_by_type(vault_type)
            if not vault:
                log.error(f"{icons.ERROR} Unknown vault type: {vault_type}")

                return None

            loaded_data = vault.load()
            if loaded_data:
                log.debug(
                    f"{icons.BUG} {vault_type.title()} data loaded successfully from database.",
                )

                return loaded_data

            log.debug(f"{icons.BUG} No {vault_type} data found in database.")

            return None

        except Exception as e:
            log.error(
                f"{icons.ERROR} Failed to load {vault_type} data from database: {e!s}",
            )

            return None

    def _get_vault_by_type(self, vault_type: VaultType) -> AnyVault | None:
        """Get the vault instance corresponding to a vault type string."""
        vault_map: dict[VaultType, AnyVault] = {
            "user": self.user_vault,
            "party": self.party_vault,
            "content": self.content_vault,
            "tasks": self.task_vault,
            "challenges": self.challenge_vault,
            "tags": self.tag_vault,
        }

        return vault_map.get(vault_type)

    def _get_collection_attr(self, vault_type: VaultType) -> Any | None:
        """Get the data collection attribute (e.g., self.user) by vault type."""
        if config := self.VAULT_CONFIGS.get(vault_type):
            return getattr(self, config.collection_attr, None)

        return None

    def _set_collection_attr(self, vault_type: VaultType, value: Any) -> None:
        """Set the data collection attribute (e.g., self.user) by vault type."""
        if config := self.VAULT_CONFIGS.get(vault_type):
            setattr(self, config.collection_attr, value)
