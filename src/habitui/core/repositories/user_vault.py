# ♥♥─── User Vault ────────────────────────────────────────────────────────────
from datetime import timedelta
from typing import cast

from sqlmodel import Session, select

from habitui.config.app_config import app_config
from habitui.core.models import (
    HabiTuiSQLModel,
    TagComplex,
    UserAchievements,
    UserCollection,
    UserCurrentState,
    UserHistory,
    UserMessage,
    UserNotifications,
    UserPreferences,
    UserProfile,
    UserStatsComputed,
    UserStatsRaw,
    UserTasksOrder,
    UserTimestamps,
)
from habitui.custom_logger import log

from .base_vault import DATABASE_FILE_NAME, BaseVault, SaveStrategy

TIMEOUT = timedelta(minutes=app_config.cache.live_minutes)


# ─── User Vault ───────────────────────────────────────────────────────────────
class UserVault(BaseVault[UserCollection]):
    """Vault implementation for managing all user profile-related content."""

    def __init__(self, vault_name: str = "user_vault", db_url: str | None = None, echo: bool = False) -> None:
        """Initialize the UserVault with the appropriate cache timeout.

        :param vault_name: The name of this vault instance.
        :param db_url: The database connection URL (uses default if None).
        :param echo: If True, SQLAlchemy will log all generated SQL.
        """
        if db_url is None:
            db_url = f"sqlite:///{DATABASE_FILE_NAME}"

        super().__init__(vault_name=vault_name, cache_time=TIMEOUT, db_url=db_url, echo=echo)

    def get_model_configs(self) -> dict[str, type[HabiTuiSQLModel]]:
        """Returns the mapping of content types to their SQLModel classes."""
        return {
            "profile": UserProfile,
            "raw_stats": UserStatsRaw,
            "computed_stats": UserStatsComputed,
            "user_state": UserCurrentState,
            "history": UserHistory,
            "tasks_order": UserTasksOrder,
            "preferences": UserPreferences,
            "achievements": UserAchievements,
            "notifications": UserNotifications,
            "timestamps": UserTimestamps,
            "simple_tags": TagComplex,
            "inbox": UserMessage,
        }

    def save(self, content: UserCollection, strategy: SaveStrategy = "smart", debug: bool = True) -> None:
        """Saves all components of a UserCollection to the database.

        :param content: A UserCollection object containing all user profile parts.
        :param strategy: The save strategy ('smart', 'incremental', 'force_recreate').
        :param debug: If True, enables detailed logging for changes.
        """
        with Session(self.engine) as session:
            try:
                log.info("Starting user profile database sync with '{}' strategy.", strategy)
                models_to_save = {
                    "profile": (UserProfile, content.profile),
                    "raw_stats": (UserStatsRaw, content.raw_stats),
                    "computed_stats": (UserStatsComputed, content.computed_stats),
                    "user_state": (UserCurrentState, content.user_state),
                    "history": (UserHistory, content.history),
                    "tasks_order": (UserTasksOrder, content.tasks_order),
                    "preferences": (UserPreferences, content.preferences),
                    "achievements": (UserAchievements, content.achievements),
                    "notifications": (UserNotifications, content.notifications),
                    "timestamps": (UserTimestamps, content.timestamps),
                }
                for name, (model_cls, item) in models_to_save.items():
                    if item:
                        self._save_single_item(session, model_cls, item, strategy, name, debug)

                if content.simple_tags:
                    self._save_item_list(session, TagComplex, content.simple_tags, "smart", "simple_tags", debug)

                if content.inbox:
                    self._save_append_mode(session, UserMessage, content.inbox, "inbox", debug)

                session.commit()
                log.info("Commit successful")
            except Exception as e:
                log.error("Commit failed: {}", e)
                raise
            log.info("User profile database sync completed.")

    def load(self) -> UserCollection | None:
        """Loads all user profile content from the database. Reconstructs the UserCollection.

        :return: The loaded UserCollection or None if UserProfile is not found.
        """
        with Session(self.engine) as session:
            profile = session.exec(select(UserProfile)).first()
            if not profile:
                log.warning("No UserProfile found in the database. Cannot load user collection.")
                return None

            raw_stats = session.exec(select(UserStatsRaw)).first()
            computed_stats = session.exec(select(UserStatsComputed)).first()
            user_state = session.exec(select(UserCurrentState)).first()
            history = session.exec(select(UserHistory)).first()
            tasks_order = session.exec(select(UserTasksOrder)).first()
            preferences = session.exec(select(UserPreferences)).first()
            achievements = session.exec(select(UserAchievements)).first()
            notifications = session.exec(select(UserNotifications)).first()
            timestamps = session.exec(select(UserTimestamps)).first()
            simple_tags = list(session.exec(select(TagComplex)).all())
            inbox_messages = list(session.exec(select(UserMessage)).all())

            try:
                return UserCollection(
                    profile=profile,
                    raw_stats=cast("UserStatsRaw", raw_stats),
                    computed_stats=cast("UserStatsComputed", computed_stats),
                    user_state=cast("UserCurrentState", user_state),
                    history=cast("UserHistory", history),
                    tasks_order=cast("UserTasksOrder", tasks_order),
                    preferences=cast("UserPreferences", preferences),
                    achievements=cast("UserAchievements", achievements),
                    notifications=cast("UserNotifications", notifications),
                    timestamps=cast("UserTimestamps", timestamps),
                    simple_tags=simple_tags,
                    inbox=inbox_messages,
                    challenges=[],
                )
            except Exception as e:
                log.exception("Failed to assemble UserCollection from DB data: {}", e)
                return None
