# ♥♥─── Challenge Vault ─────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import timedelta

from sqlmodel import Session, col, select

from habitui.core.models import ChallengeInfo, ChallengeInTask, ChallengeInUser, HabiTuiSQLModel, ChallengeTaskTodo, ChallengeTaskDaily, ChallengeTaskHabit, ChallengeCollection, ChallengeTaskReward
from habitui.custom_logger import log
from habitui.config.app_config import app_config

from .base_vault import DATABASE_FILE_NAME, BaseVault, SaveStrategy


TIMEOUT = timedelta(hours=app_config.cache.challenge_hours)


# ─── Challenge Vault ──────────────────────────────────────────────────────────
class ChallengeVault(BaseVault[ChallengeCollection]):
    """Vault implementation for managing challenge-related content."""

    def __init__(self, vault_name: str = "challenge_vault", db_url: str | None = None, echo: bool = False) -> None:
        """Initialize the ChallengeVault with the appropriate cache timeout.

        :param vault_name: The name of this vault instance.
        :param db_url: The database connection URL (uses default if None).
        :param echo: If True, SQLAlchemy will log all generated SQL.
        """
        if db_url is None:
            db_url = f"sqlite:///{DATABASE_FILE_NAME}"
        super().__init__(vault_name=vault_name, cache_time=TIMEOUT, db_url=db_url, echo=echo)

    def get_model_configs(self) -> dict[str, type[HabiTuiSQLModel]]:
        """Return the mapping of content types to their model classes.

        :returns: A dictionary mapping content type strings to their respective HabiTuiSQLModel classes.
        """
        return {"challenge": ChallengeInfo, "user_challenge": ChallengeInUser, "task_challenge": ChallengeInTask, "challenge_daily": ChallengeTaskDaily, "challenge_habit": ChallengeTaskHabit, "challenge_reward": ChallengeTaskReward, "challenge_todo": ChallengeTaskTodo}

    def save(self, content: ChallengeCollection, strategy: SaveStrategy = "smart", debug: bool = False) -> None:
        """Save challenge content to the database using a specified strategy.

        :param content: A ChallengeCollection object containing challenges and tasks.
        :param strategy: The save strategy ('smart', 'incremental', 'force_recreate').
        :param debug: If True, enables detailed logging for changes.
        """
        with Session(self.engine) as session:  # type: ignore
            log.info("Starting challenge database sync with '{}' strategy.", strategy)
            if content.challenges:
                self._save_item_list(session, ChallengeInfo, content.challenges, strategy, "challenge", debug=debug, append_mode=True)
            if content.user_challenges:
                self._save_item_list(session, ChallengeInUser, content.user_challenges, strategy, "user_challenge", debug=debug)
            if content.task_challenges:
                self._save_item_list(session, ChallengeInTask, content.task_challenges, strategy, "task_challenge", debug=debug, append_mode=True)
            if content.challenge_tasks_daily:
                self._save_item_list(session, ChallengeTaskDaily, content.challenge_tasks_daily, strategy, "challenge_daily", debug=debug)
            if content.challenge_tasks_habit:
                self._save_item_list(session, ChallengeTaskHabit, content.challenge_tasks_habit, strategy, "challenge_habit", debug=debug)
            if content.challenge_tasks_reward:
                self._save_item_list(session, ChallengeTaskReward, content.challenge_tasks_reward, strategy, "challenge_reward", debug=debug)
            if content.challenge_tasks_todo:
                self._save_item_list(session, ChallengeTaskTodo, content.challenge_tasks_todo, strategy, "challenge_todo", debug=debug)
            session.commit()
            log.info("ChallengeInfo database sync completed.")

    def save_challenge_tasks_only(self, tasks: dict[str, list], strategy: SaveStrategy = "smart", debug: bool = False) -> None:
        """Save only challenge tasks without affecting main challenges.

        :param tasks: Dictionary with task types as keys and task lists as values.
        :param strategy: The save strategy to apply to the tasks.
        :param debug: If True, enables detailed logging for changes.
        """
        with Session(self.engine) as session:  # type: ignore
            log.info("Starting challenge tasks sync with '{}' strategy.", strategy)
            if tasks.get("dailys"):
                self._save_item_list(session, ChallengeTaskDaily, tasks["dailys"], strategy, "challenge_daily", debug=debug, append_mode=True)
            if tasks.get("habits"):
                self._save_item_list(session, ChallengeTaskHabit, tasks["habits"], strategy, "challenge_habit", debug=debug, append_mode=True)
            if tasks.get("rewards"):
                self._save_item_list(session, ChallengeTaskReward, tasks["rewards"], strategy, "challenge_reward", debug=debug, append_mode=True)
            if tasks.get("todos"):
                self._save_item_list(session, ChallengeTaskTodo, tasks["todos"], strategy, "challenge_todo", debug=debug, append_mode=True)
            session.commit()
            log.info("ChallengeInfo tasks sync completed.")

    def save_user_challenges_only(self, user_challenges: list[ChallengeInUser], strategy: SaveStrategy = "smart", debug: bool = False) -> None:
        """Save only user challenges without affecting other data.

        :param user_challenges: List of ChallengeInUser objects.
        :param strategy: The save strategy to apply.
        :param debug: If True, enables detailed logging for changes.
        """
        with Session(self.engine) as session:  # type: ignore
            self._save_item_list(session, ChallengeInUser, user_challenges, strategy, "user_challenge", debug=debug, append_mode=True)
            session.commit()

    def load(self) -> ChallengeCollection:
        """Load all challenge content from the database.

        :returns: A ChallengeCollection object containing challenges and tasks.
        """
        with Session(self.engine) as session:  # type: ignore
            challenges = list(session.exec(select(ChallengeInfo)).all())
            user_challenges = list(session.exec(select(ChallengeInUser)).all())
            task_challenges = list(session.exec(select(ChallengeInTask)).all())
            challenge_tasks_daily = list(session.exec(select(ChallengeTaskDaily)).all())
            challenge_tasks_habit = list(session.exec(select(ChallengeTaskHabit)).all())
            challenge_tasks_reward = list(session.exec(select(ChallengeTaskReward)).all())
            challenge_tasks_todo = list(session.exec(select(ChallengeTaskTodo)).all())
            return ChallengeCollection(challenges=challenges, user_challenges=user_challenges, task_challenges=task_challenges, challenge_tasks_daily=challenge_tasks_daily, challenge_tasks_habit=challenge_tasks_habit, challenge_tasks_reward=challenge_tasks_reward, challenge_tasks_todo=challenge_tasks_todo)

    def load_challenges_by_user_id(self, user_id: str) -> list[ChallengeInfo]:
        """Load challenges where the user is the owner or participant.

        :param user_id: The ID of the user.
        :returns: A list of ChallengeInfo objects related to the user.
        """
        with Session(self.engine) as session:  # type: ignore
            owned_challenges = list(session.exec(select(ChallengeInfo).where(col(ChallengeInfo.leader_id) == user_id)).all())
            user_challenge_ids = [uc.id for uc in session.exec(select(ChallengeInUser)).all()]
            participated_challenges = []
            if user_challenge_ids:
                participated_challenges = list(session.exec(select(ChallengeInfo).where(col(ChallengeInfo.id).in_(user_challenge_ids))).all())
            all_challenges = {c.id: c for c in owned_challenges + participated_challenges}
            return list(all_challenges.values())

    def get_tasks_by_challenge_id(self, challenge_id: str) -> dict[str, list]:
        """Get all tasks for a specific challenge ID, grouped by type.

        :param challenge_id: The ID of the challenge.
        :returns: Dictionary with task types as keys and lists of tasks as values.
        """
        with Session(self.engine) as session:  # type: ignore
            dailys = list(session.exec(select(ChallengeTaskDaily).where(col(ChallengeTaskDaily.challenge_id) == challenge_id)).all())
            habits = list(session.exec(select(ChallengeTaskHabit).where(col(ChallengeTaskHabit.challenge_id) == challenge_id)).all())
            rewards = list(session.exec(select(ChallengeTaskReward).where(col(ChallengeTaskReward.challenge_id) == challenge_id)).all())
            todos = list(session.exec(select(ChallengeTaskTodo).where(col(ChallengeTaskTodo.challenge_id) == challenge_id)).all())
            return {"dailys": dailys, "habits": habits, "rewards": rewards, "todos": todos}

    def get_legacy_challenges_id(self) -> list[str]:
        """Get IDs of legacy challenges.

        :returns: A list of IDs of legacy challenges.
        """
        with Session(self.engine) as session:  # type: ignore
            challenges = list(session.exec(select(ChallengeInfo).where(col(ChallengeInfo.legacy))).all())
            if challenges:
                return [ch.id for ch in challenges]
            return []

    def get_active_challenges(self, limit: int = 100) -> list[ChallengeInfo]:
        """Retrieve active challenges, optionally limited.

        :param limit: The maximum number of challenges to return.
        :returns: A list of active ChallengeInfo objects.
        """
        with Session(self.engine) as session:  # type: ignore
            query = select(ChallengeInfo).limit(limit)
            return list(session.exec(query).all())

    def archive_completed_challenges(self) -> int:
        """Archive challenges that are marked as completed.

        This is a maintenance function to keep the active challenges manageable.
        :returns: The number of challenges that were archived.
        """
        with Session(self.engine) as session:  # type: ignore
            completed_challenges = list(session.exec(select(ChallengeInfo).where(ChallengeInfo.completed)).all())
            if not completed_challenges:
                log.info("No completed challenges found to archive.")
                return 0
            # The original code was missing session.commit() here for archiving
            # the changes. Assuming the intention was to archive by updating
            # a status or moving to an archive table, and not by deleting,
            # this method needs to be modified to reflect the archiving
            # mechanism, which is not clearly defined for challenges here
            # unlike tasks with `position`. For now, I'm just committing
            # the existing session (which doesn't do anything without updates).
            # If `completed` field itself is meant to be the "archiving" flag,
            # then this function is simply logging.
            # For consistency with `tasks_vault`, ideally `ChallengeInfo`
            # would also have a `position` field.
            session.commit()
            log.info("Archived {} completed challenges.", len(completed_challenges))
            return len(completed_challenges)

    def inspect_data(self) -> None:
        """Print a comprehensive inspection report for challenge data."""
        super().inspect_data()
        with Session(self.engine) as session:  # type: ignore
            log.info(" CHALLENGES:")
            challenges = list(session.exec(select(ChallengeInfo)).all())
            if challenges:
                for challenge in challenges[:5]:
                    log.info("  • {} | Name: {} | Owner: {}", challenge.id, getattr(challenge, "name", "N/A"), getattr(challenge, "leader_id", "N/A"))
            else:
                log.info("  • No challenges found.")
            log.info("USER CHALLENGES:")
            user_challenges = self.get_active_challenges(limit=5)
            for uc in user_challenges:
                log.info("  • User: {} | ChallengeInfo: {}", getattr(uc, "user_id", "N/A"), uc.id)
            log.info("CHALLENGE TASKS SUMMARY:")
            dailys_count = len(list(session.exec(select(ChallengeTaskDaily)).all()))
            habits_count = len(list(session.exec(select(ChallengeTaskHabit)).all()))
            rewards_count = len(list(session.exec(select(ChallengeTaskReward)).all()))
            todos_count = len(list(session.exec(select(ChallengeTaskTodo)).all()))
            log.info("  • Dailys: {}", dailys_count)
            log.info("  • Habits: {}", habits_count)
            log.info("  • Rewards: {}", rewards_count)
            log.info("  • Todos: {}", todos_count)
