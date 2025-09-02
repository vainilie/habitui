# ♥♥─── Task Vault ────────────────────────────────────────────────────────────
from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar, Protocol, cast
from datetime import timedelta

from sqlmodel import Session, select

from habitui.custom_logger import log
from habitui.config.app_config import app_config
from habitui.core.models.task_model import TaskTodo, TaskDaily, TaskHabit, TaskReward, TaskChecklist, TaskCollection

from .base_vault import DATABASE_FILE_NAME, BaseVault, SaveStrategy


if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.sql.expression import ColumnElement
TIMEOUT = timedelta(minutes=app_config.cache.live_minutes)


class PositionableModel(Protocol):
    """Protocol for models that have a 'position' field."""

    position: int


T = TypeVar("T", bound=PositionableModel)
AnyTask = TaskTodo | TaskDaily | TaskHabit | TaskReward | TaskChecklist
SuccessfulResponseData = dict[str, Any] | list[dict[str, Any]] | list[Any] | None


# ─── Task Vault ───────────────────────────────────────────────────────────────
class TaskVault(BaseVault[TaskCollection]):
    """Vault implementation for managing task-related content."""

    def __init__(self, vault_name: str = "tasks_vault", db_url: str | None = None, echo: bool = False) -> None:
        """Initialize the TaskVault with the appropriate cache timeout.

        :param vault_name: The name of this vault instance.
        :param db_url: The database connection URL (uses default if None).
        :param echo: If True, SQLAlchemy will log all generated SQL.
        """
        if db_url is None:
            db_url = f"sqlite:///{DATABASE_FILE_NAME}"
        super().__init__(vault_name=vault_name, cache_time=TIMEOUT, db_url=db_url, echo=echo)

    def get_model_configs(self) -> dict[str, type[AnyTask]]:
        """Return the mapping of content types to their model classes."""
        return {"todos": TaskTodo, "dailys": TaskDaily, "habits": TaskHabit, "rewards": TaskReward, "subtasks": TaskChecklist}

    def save(self, content: TaskCollection, strategy: SaveStrategy = "smart", debug: bool = False) -> None:
        """Save task content to the database using a specified strategy.

        :param content: A TaskCollection object containing all task types.
        :param strategy: The save strategy ('smart', 'incremental', 'force_recreate').
        :param debug: If True, enables detailed logging for changes.
        """
        with Session(self.engine) as session:  # type: ignore
            log.info("Starting tasks database sync with '{}' strategy.", strategy)
            if content.todos:
                self._save_item_list(session, TaskTodo, content.todos, strategy, "todos", debug=debug)
            if content.dailys:
                self._save_item_list(session, TaskDaily, content.dailys, strategy, "dailys", debug=debug)
            if content.habits:
                self._save_item_list(session, TaskHabit, content.habits, strategy, "habits", debug=debug)
            if content.rewards:
                self._save_item_list(session, TaskReward, content.rewards, strategy, "rewards", debug=debug)
            if content.subtasks:
                self._save_item_list(session, TaskChecklist, content.subtasks, strategy, "subtasks", debug=debug)
            session.commit()
            log.info("Tasks database sync completed.")

    def save_recent_tasks(self, task_type: str, recent_tasks: Sequence[AnyTask], strategy: SaveStrategy = "smart", debug: bool = False) -> None:
        """Save recent tasks of a specific type without affecting older tasks.

        :param task_type: The type of task ('todos', 'dailys', 'habits', 'rewards', 'subtasks').
        :param recent_tasks: A list of new or updated tasks.
        :param strategy: The save strategy to apply to the recent items.
        :param debug: If True, enables detailed logging for changes.
        """
        model_configs = self.get_model_configs()
        if task_type not in model_configs:
            error = "Unknown task type: {}", task_type
            raise ValueError(error)
        model_class = model_configs[task_type]
        with Session(self.engine) as session:  # type: ignore
            self._save_item_list(session, model_class, recent_tasks, strategy, task_type, debug=debug, append_mode=True)
            session.commit()

    def save_recent_todos(self, recent_todos: list[TaskTodo], **kwargs: Any) -> None:
        """Save recent todos.

        :param recent_todos: A list of new or updated TaskTodo items.
        :param kwargs: Additional keyword arguments to pass to `save_recent_tasks`.
        """
        self.save_recent_tasks("todos", recent_todos, **kwargs)

    def save_recent_dailys(self, recent_dailys: list[TaskDaily], **kwargs: Any) -> None:
        """Save recent dailys.

        :param recent_dailys: A list of new or updated TaskDaily items.
        :param kwargs: Additional keyword arguments to pass to `save_recent_tasks`.
        """
        self.save_recent_tasks("dailys", recent_dailys, **kwargs)

    def save_recent_habits(self, recent_habits: list[TaskHabit], **kwargs: Any) -> None:
        """Save recent habits.

        :param recent_habits: A list of new or updated TaskHabit items.
        :param kwargs: Additional keyword arguments to pass to `save_recent_tasks`.
        """
        self.save_recent_tasks("habits", recent_habits, **kwargs)

    def save_recent_rewards(self, recent_rewards: list[TaskReward], **kwargs: Any) -> None:
        """Save recent rewards.

        :param recent_rewards: A list of new or updated TaskReward items.
        :param kwargs: Additional keyword arguments to pass to `save_recent_tasks`.
        """
        self.save_recent_tasks("rewards", recent_rewards, **kwargs)

    def save_recent_subtasks(self, recent_subtasks: list[TaskChecklist], **kwargs: Any) -> None:
        """Save recent subtasks.

        :param recent_subtasks: A list of new or updated TaskChecklist items.
        :param kwargs: Additional keyword arguments to pass to `save_recent_tasks`.
        """
        self.save_recent_tasks("subtasks", recent_subtasks, **kwargs)

    def load(self) -> TaskCollection:
        """Load all active task content from the database.

        :return: A TaskCollection object containing all active tasks.
        """
        with Session(self.engine) as session:  # type: ignore

            def load_active(model: type[T]) -> list[T]:
                position_col = cast("ColumnElement", model.position)
                stmt = select(model).where(position_col < self.ARCHIVE_POSITION_START).order_by(position_col)
                return list(session.exec(stmt).all())

            todos = load_active(TaskTodo)
            dailys = load_active(TaskDaily)
            habits = load_active(TaskHabit)
            rewards = load_active(TaskReward)
            subtasks = list(session.exec(select(TaskChecklist)).all())
            return TaskCollection(todos=todos, dailys=dailys, habits=habits, rewards=rewards, subtasks=subtasks, challenges=[])

    def get_active_tasks(self, task_type: str, limit: int = 100) -> Sequence[AnyTask]:
        """Retrieve active (non-archived) tasks of a specific type.

        :param task_type: The type of task to retrieve.
        :param limit: The maximum number of tasks to return.
        :return: A list of active tasks of the specified type.
        """
        model_configs = self.get_model_configs()
        if task_type not in model_configs:
            error = "Unknown task type: {}", task_type
            raise ValueError(error)
        model_class = model_configs[task_type]
        with Session(self.engine) as session:  # type: ignore
            position_col = cast("ColumnElement", model_class.position)
            query = select(model_class).where(model_class.position < self.ARCHIVE_POSITION_START).order_by(position_col).limit(limit)
            return list(session.exec(query).all())

    def get_active_todos(self, limit: int = 100) -> Sequence[AnyTask]:
        """Get active todos.

        :param limit: The maximum number of todos to return.
        :return: A list of active TaskTodo items.
        """
        return self.get_active_tasks("todos", limit)

    def get_active_dailys(self, limit: int = 100) -> Sequence[AnyTask]:
        """Get active dailys.

        :param limit: The maximum number of dailys to return.
        :return: A list of active TaskDaily items.
        """
        return self.get_active_tasks("dailys", limit)

    def get_active_habits(self, limit: int = 100) -> Sequence[AnyTask]:
        """Get active habits.

        :param limit: The maximum number of habits to return.
        :return: A list of active TaskHabit items.
        """
        return self.get_active_tasks("habits", limit)

    def get_active_rewards(self, limit: int = 100) -> Sequence[AnyTask]:
        """Get active rewards.

        :param limit: The maximum number of rewards to return.
        :return: A list of active TaskReward items.
        """
        return self.get_active_tasks("rewards", limit)

    def get_active_subtasks(self, limit: int = 100) -> Sequence[AnyTask]:
        """Get active subtasks.

        :param limit: The maximum number of subtasks to return.
        :return: A list of active TaskChecklist items.
        """
        return self.get_active_tasks("subtasks", limit)

    def archive_tasks_by_count(self, task_type: str, keep_count: int = 1000) -> int:
        """Archive older tasks of a specific type. Keeps only the most recent ones.

        :param task_type: The type of task to archive.
        :param keep_count: The number of recent tasks to keep active.
        :return: The number of tasks that were archived.
        """
        model_configs = self.get_model_configs()
        if task_type not in model_configs:
            error = "Unknown task type: {}", task_type
            raise ValueError(error)
        model_class = model_configs[task_type]
        with Session(self.engine) as session:  # type: ignore
            position_col = cast("ColumnElement", model_class.position)
            tasks_to_archive = list(session.exec(select(model_class).where(model_class.position < self.ARCHIVE_POSITION_START).order_by(position_col.desc()).offset(keep_count)).all())
            if not tasks_to_archive:
                log.info("No old {} found to archive.", task_type)
                return 0
            next_pos = self._get_next_archive_position(session, model_class)
            for i, task in enumerate(tasks_to_archive):
                task.position = next_pos + i
            session.commit()
            log.info("Archived {} old {} tasks.", len(tasks_to_archive), task_type)
            return len(tasks_to_archive)

    def archive_all_old_tasks(self, keep_count: int = 500) -> dict[str, int]:
        """Archive old tasks for all task types.

        :param keep_count: The number of recent tasks to keep active for each type.
        :return: A dictionary mapping task types to the number of archived tasks.
        """
        results = {}
        for task_type in self.get_model_configs():
            results[task_type] = self.archive_tasks_by_count(task_type, keep_count)
        return results

    def inspect_data(self) -> None:
        """Print a comprehensive inspection report for task data."""
        super().inspect_data()
        with Session(self.engine) as session:  # type: ignore
            log.info("TASK SUMMARY:")
            for task_type, model_class in self.get_model_configs().items():
                if hasattr(model_class, "position"):
                    active_count = len(session.exec(select(model_class).where(model_class.position < self.ARCHIVE_POSITION_START)).all())
                    archived_count = len(session.exec(select(model_class).where(model_class.position >= self.ARCHIVE_POSITION_START)).all())
                else:
                    active_count = len(session.exec(select(model_class)).all())
                    archived_count = 0
                log.info("  • {}: {} active, {} archived", task_type.capitalize(), active_count, archived_count)
            log.info("RECENT TODOS (first 3):")
            for todo in self.get_active_todos(limit=3):
                title = getattr(todo, "title", getattr(todo, "text", ""))[:50]
                log.info("  • {} [pos: {}] {}...", todo.id, getattr(todo, "position", "N/A"), title)
            log.info("RECENT dailys (first 3):")
            for daily in self.get_active_dailys(limit=3):
                title = getattr(daily, "title", getattr(daily, "text", ""))[:50]
                log.info("  • {} [pos: {}] {}...", daily.id, getattr(daily, "position", "N/A"), title)
