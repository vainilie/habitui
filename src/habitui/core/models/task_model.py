# ♥♥─── HabiTui Task Models ────────────────────────────────────────────────────

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, cast
from datetime import date, datetime

from pydantic import PrivateAttr, field_validator
from sqlmodel import Field, Column

from habitui.utils import DateTimeHandler
from habitui.custom_logger import log

from .base_enums import (
    Frequency,
    TaskStatus,
    TodoStatus,
    DailyStatus,
    HabitStatus,
    RewardStatus,
)
from .base_model import HabiTuiSQLModel, HabiTuiBaseModel
from .validators import (
    PydanticJSON,
    habit_status,
    normalize_attribute,
    calculate_task_damage,
    replace_emoji_shortcodes,
)


if TYPE_CHECKING:
    from collections.abc import Iterator

    from box import Box

    from .user_model import UserCollection


SuccessfulResponseData = dict[str, Any] | list[dict[str, Any]] | list[Any] | None


# ─── BASE MODELS ────────────────────────────────────────────────────────────────
class ChallengeInTask(HabiTuiSQLModel, table=True):
    """Represent a challenge linked to a task."""

    __tablename__ = "challenge_in_task"  # type: ignore

    id: str = Field(alias="id", primary_key=True)
    short_name: str
    broken: bool
    winner: str | None
    tasks_ids: list[str] = Field(default_factory=list, sa_column=Column(PydanticJSON))
    broken_tasks_ids: list[str] = Field(
        default_factory=list,
        sa_column=Column(PydanticJSON),
    )


# ─── TaskChecklist ──────────────────────────────────────────────────────────────────
class TaskChecklist(HabiTuiSQLModel, table=True):
    """TaskChecklist model for checklist items."""

    __tablename__ = "task_checklist"  # type: ignore
    type: str = "TaskChecklist"
    status: TaskStatus = Field(default=TaskStatus.AVAILABLE)
    text: str
    completed: bool = Field(default=False)
    parent_task_id: str = Field(index=True)
    position: int

    @field_validator("text", mode="before")
    @classmethod
    def validate_text_fields(cls, v: Any) -> str:
        """Validate and cleans text fields by replacing emoji shortcodes.

        :param v: The input text.
        :returns: The cleaned string.
        """
        return replace_emoji_shortcodes(v)

    @classmethod
    def from_api_dict(cls, data: dict[str, Any]) -> TaskChecklist:
        """Create instance from API data with user context.

        :param data: The raw API data for the checklist item.
        :returns: A TaskChecklist instance.
        """
        if isinstance(data, dict) and data.get("completed"):
            data["status"] = TaskStatus.COMPLETED
        return cls.model_validate(data)


# ─── TaskReward ───────────────────────────────────────────────────────────────
class TaskReward(HabiTuiSQLModel, table=True):
    """Reward task model."""

    __tablename__ = "task_reward"  # type: ignore

    type: str = Field(default="Reward")
    status: RewardStatus = Field(default=RewardStatus.UNAFFORDABLE)
    text: str = Field(index=True)
    notes: str = Field(default="", index=True)
    value: float = Field(default=0.0)
    priority: float = Field(default=1.0)
    attribute: str | None = Field(default=None)
    position: int
    created_at: datetime
    updated_at: datetime
    challenge: bool = Field(default=False)
    challenge_id: str | None = Field(default=None)
    challenge_shortname: str | None = Field(default=None)
    challenge_task_id: str | None = Field(default=None)
    task_broken: bool = Field(default=False)
    challenge_broken: bool = Field(default=False)
    challenge_winner: str | None = Field(default=None)
    alias: str | None = Field(default=None)
    reminders: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(PydanticJSON),
    )
    tags: list[str] = Field(default_factory=list, sa_column=Column(PydanticJSON))

    @field_validator("text", "notes", "challenge_shortname", mode="before")
    @classmethod
    def validate_text_fields(cls, v: Any) -> str:
        """Validate and cleans text fields by replacing emoji shortcodes.

        :param v: The input text.
        :returns: The cleaned string.
        """
        return replace_emoji_shortcodes(v)

    @field_validator("attribute", mode="before")
    @classmethod
    def validate_attribute(cls, v: Any) -> str | None:
        """Validate and normalizes attribute names.

        :param v: The input attribute.
        :returns: The normalized attribute name.
        """
        return normalize_attribute(v)


# ─── TaskHabit ────────────────────────────────────────────────────────────────
class TaskHabit(HabiTuiSQLModel, table=True):
    """Habit task model with flattened structure."""

    __tablename__ = "task_habit"  # type: ignore

    type: str = Field(default="Habit")
    status: HabitStatus = Field(default=HabitStatus.NEGLECTED)
    text: str = Field(index=True)
    notes: str = Field(default="", index=True)
    value: float = Field(default=0.0)
    priority: float = Field(default=1.0)
    attribute: str | None = Field(default=None)
    position: int
    created_at: datetime
    updated_at: datetime
    challenge: bool = Field(default=False)
    challenge_id: str | None = Field(default=None)
    challenge_shortname: str | None = Field(default=None)
    challenge_task_id: str | None = Field(default=None)
    task_broken: bool = Field(default=False)
    challenge_broken: bool = Field(default=False)
    challenge_winner: str | None = Field(default=None)
    alias: str | None = Field(default=None)
    up: bool = Field(default=True)
    down: bool = Field(default=False)
    counter_up: int = Field(default=0)
    counter_down: int = Field(default=0)
    frequency: Frequency = Field(default=Frequency.WEEKLY)
    history: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(PydanticJSON),
    )
    reminders: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(PydanticJSON),
    )
    tags: list[str] = Field(default_factory=list, sa_column=Column(PydanticJSON))

    @field_validator("text", "notes", "challenge_shortname", mode="before")
    @classmethod
    def validate_text_fields(cls, v: Any) -> str:
        """Validate and cleans text fields by replacing emoji shortcodes.

        :param v: The input text.
        :returns: The cleaned string.
        """
        return replace_emoji_shortcodes(v)

    @field_validator("attribute", mode="before")
    @classmethod
    def validate_attribute(cls, v: Any) -> str | None:
        """Validate and normalizes attribute names.

        :param v: The input attribute.
        :returns: The normalized attribute name.
        """
        return normalize_attribute(v)


# ─── TaskTodo ─────────────────────────────────────────────────────────────────
class TaskTodo(HabiTuiSQLModel, table=True):
    """Todo task model with flattened checklist data."""

    __tablename__ = "task_todo"  # type: ignore

    type: str = Field(default="Todo")
    status: TodoStatus = Field(default=TodoStatus.SOMEDAY)
    text: str = Field(index=True)
    notes: str = Field(default="", index=True)
    value: float = Field(default=0.0)
    priority: float = Field(default=1.0)
    attribute: str | None = Field(default=None)
    position: int
    created_at: datetime
    updated_at: datetime
    challenge: bool = Field(default=False)
    challenge_id: str | None = Field(default=None)
    challenge_shortname: str | None = Field(default=None)
    challenge_task_id: str | None = Field(default=None)
    task_broken: bool = Field(default=False)
    challenge_broken: bool = Field(default=False)
    challenge_winner: str | None = Field(default=None)
    alias: str | None = Field(default=None)
    completed: bool = Field(default=False)
    due_date: datetime | None = Field(default=None)
    checklist_total: int = Field(default=0)
    checklist_completed: int = Field(default=0)
    checklist_progress: float = Field(default=0.0)
    checklist_percentage: int = Field(default=0)
    checklist: list[str] = Field(default_factory=list, sa_column=Column(PydanticJSON))
    reminders: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(PydanticJSON),
    )
    tags: list[str] = Field(default_factory=list, sa_column=Column(PydanticJSON))

    @field_validator("text", "notes", "challenge_shortname", mode="before")
    @classmethod
    def validate_text_fields(cls, v: Any) -> str:
        """Validate and cleans text fields by replacing emoji shortcodes.

        :param v: The input text.
        :returns: The cleaned string.
        """
        return replace_emoji_shortcodes(v)

    @field_validator("attribute", mode="before")
    @classmethod
    def validate_attribute(cls, v: Any) -> str | None:
        """Validate and normalizes attribute names.

        :param v: The input attribute.
        :returns: The normalized attribute name.
        """
        return normalize_attribute(v)


# ─── TaskDaily ────────────────────────────────────────────────────────────────
class TaskDaily(HabiTuiSQLModel, table=True):
    """Daily task model with flattened structure."""

    __tablename__ = "task_daily"  # type: ignore
    type: str = Field(default="Daily")
    status: DailyStatus = Field(default=DailyStatus.INACTIVE)
    text: str
    notes: str = Field(default="")
    value: float = Field(default=0.0)
    priority: float = Field(default=1.0)
    attribute: str | None = Field(default=None)
    position: int
    created_at: datetime
    updated_at: datetime
    challenge: bool = Field(default=False)
    challenge_id: str | None = Field(default=None)
    challenge_shortname: str | None = Field(default=None)
    challenge_task_id: str | None = Field(default=None)
    task_broken: bool = Field(default=False)
    challenge_broken: bool = Field(default=False)
    challenge_winner: str | None = Field(default=None)
    alias: str | None = Field(default=None)
    frequency: Frequency = Field(default=Frequency.WEEKLY)
    repetition_interval: int = Field(default=1)
    start_date: datetime | None = Field(default=None)
    streak: int = Field(default=0)
    completed: bool = Field(default=False)
    due_today: bool = Field(default=False)
    due_yesterday: bool = Field(default=False)
    checklist_total: int = Field(default=0)
    checklist_completed: int = Field(default=0)
    checklist_progress: float = Field(default=0.0)
    user_damage: float = Field(default=0.0)
    party_damage: float = Field(default=0.0)
    is_active: bool = Field(default=True)
    repeat_days: list[int] = Field(default_factory=list, sa_column=Column(PydanticJSON))
    repeat_weeks: list[int] = Field(
        default_factory=list,
        sa_column=Column(PydanticJSON),
    )
    next_due: list[str] = Field(default_factory=list, sa_column=Column(PydanticJSON))
    weekdays: list[str] = Field(default_factory=list, sa_column=Column(PydanticJSON))
    checklist: list[str] = Field(default_factory=list, sa_column=Column(PydanticJSON))
    history: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(PydanticJSON),
    )
    reminders: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(PydanticJSON),
    )
    tags: list[str] = Field(default_factory=list, sa_column=Column(PydanticJSON))

    @field_validator("text", "notes", "challenge_shortname", mode="before")
    @classmethod
    def validate_text_fields(cls, v: Any) -> str:
        """Validate and cleans text fields by replacing emoji shortcodes.

        :param v: The input text.
        :returns: The cleaned string.
        """
        return replace_emoji_shortcodes(v)

    @field_validator("attribute", mode="before")
    @classmethod
    def validate_attribute(cls, v: Any) -> str | None:
        """Validate and normalizes attribute names.

        :param v: The input attribute.
        :returns: The normalized attribute name.
        """
        return normalize_attribute(v)

    @field_validator("next_due", mode="before")
    @classmethod
    def validate_datetime(cls, v: Any) -> list[str]:
        """Validate and formats datetime objects in a list.

        :param v: The input list of datetime objects or strings.
        :returns: A list of formatted datetime strings.
        """
        return [DateTimeHandler(timestamp=d).format_local() for d in v]

    @classmethod
    def from_api_dict(cls, data: Box, user: UserCollection) -> TaskDaily:
        """Create a TaskDaily instance from API data.

        Calculates potential HP damage to user and damage to quest boss.

        :param data: The raw API data for the daily task.
        :param user: The user's data collection for context-aware parsing.
        :returns: A `TaskDaily` instance.
        """
        calculate_task_damage(data, user)
        if not data.next_due and not data.is_due and not data.yester_daily:
            data.is_active = False

        data.due_today = bool(data.is_due)
        data.due_yesterday = bool(data.yester_daily)
        data.weekdays = [k for k, v in data.get("repeat", {}).items() if v]
        data.repetition_interval = data.every_x
        data.repeat_days = data.days_of_month
        data.repeat_weeks = data.weeks_of_month

        return cls.model_validate({**data.to_dict()})


TaskStatusType = TodoStatus | DailyStatus | HabitStatus | RewardStatus
AnyTask = TaskTodo | TaskDaily | TaskHabit | TaskReward


# ─── TaskCollection ──────────────────────────────────────────────────────────
class TaskCollection(HabiTuiBaseModel):
    """Collection of all task types with utility methods for querying and manipulation.

    :param todos: A list of todo tasks.
    :param dailys: A list of daily tasks.
    :param habits: A list of habit tasks.
    :param rewards: A list of reward tasks.
    :param subtasks: A list of all subtasks from todos and dailies.
    :param challenges: A list of challenge metadata.
    """

    _user_vault: UserCollection | None = PrivateAttr(default=None)
    todos: list[TaskTodo] = Field(default_factory=list)
    dailys: list[TaskDaily] = Field(default_factory=list)
    habits: list[TaskHabit] = Field(default_factory=list)
    rewards: list[TaskReward] = Field(default_factory=list)
    subtasks: list[TaskChecklist] = Field(default_factory=list)
    challenges: list[ChallengeInTask] = Field(default_factory=list)

    # --- Properties ---
    @property
    def all_tasks(self) -> list[AnyTask]:
        """Return a single list containing all primary tasks."""
        return [*self.todos, *self.dailys, *self.habits, *self.rewards]

    # --- Class Methods ---
    @classmethod
    def from_api_data(
        cls,
        raw_content: SuccessfulResponseData,
        user_vault: UserCollection,
    ) -> TaskCollection:
        """Parse the raw API response and creates a TaskCollection instance.

        :param raw_content: The complete content data from the API.
        :param user_vault: The user's data collection for context-aware parsing.
        :returns: A TaskCollection instance populated with parsed and validated models.
        """
        from .task_processor import TaskProcessor  # noqa: PLC0415

        processor = TaskProcessor(user_vault)
        if isinstance(raw_content, list):
            return processor.process_tasks(raw_content)
        if isinstance(raw_content, dict):
            return processor.process_tasks([raw_content])
        return processor.process_tasks([])

    # --- Instance Methods ---
    def add_task(self, task: AnyTask) -> None:
        """Add a new task to the appropriate collection list based on its type.

        :param task: The task instance to add.
        """
        if isinstance(task, TaskTodo):
            self.todos.append(task)
        elif isinstance(task, TaskDaily):
            self.dailys.append(task)
        elif isinstance(task, TaskHabit):
            self.habits.append(task)
        elif isinstance(task, TaskReward):
            self.rewards.append(task)
        else:
            log.warning("Attempted to add unknown task type: {}", type(task).__name__)

    def delete_task(self, task_id: str) -> AnyTask | None:
        """Delete a task by its ID from the collection.

        :param task_id: The UUID of the task to delete.
        :returns: The deleted task instance, or None if not found.
        """
        for task_list in (self.todos, self.dailys, self.habits, self.rewards):
            for i, task in enumerate(task_list):
                if task.id == task_id:
                    deleted_task = task_list.pop(i)  # noqa: B909
                    if (
                        isinstance(deleted_task, (TaskTodo, TaskDaily))
                        and hasattr(deleted_task, "checklist")
                        and deleted_task.checklist
                    ):
                        checklist_ids = set(deleted_task.checklist)
                        self.subtasks = [
                            sub for sub in self.subtasks if sub.id not in checklist_ids
                        ]
                    log.info("Task with ID '{}' deleted successfully.", task_id)
                    return deleted_task
        log.warning("Task with ID '{}' not found for deletion.", task_id)
        return None

    def modify_task(self, task_id: str, updates: dict[str, Any]) -> AnyTask | None:
        """Modify a task's attributes.

        Finds a task by ID and updates it with the provided data.

        :param task_id: The UUID of the task to modify.
        :param updates: A dictionary of attributes to update.
        :returns: The updated task instance, or None if the task was not found.
        """
        for task_list in (self.todos, self.dailys, self.habits, self.rewards):
            for i, task in enumerate(task_list):
                if task.id == task_id:
                    task_list[i] = task.model_copy(update=updates)  # type: ignore
                    log.info("Task with ID '{}' modified successfully.", task_id)
                    return task_list[i]
        log.warning("Task with ID '{}' not found for modification.", task_id)
        return None

    def score_task(self, task_id: str, direction: str = "up") -> AnyTask | None:
        """Simulate scoring a task, updating its local state.

        - For **Todos** and **Dailies**: Marks them as complete.
        - For **Habits**: Increments the 'up' or 'down' counter.

        :param task_id: The ID of the task to score.
        :param direction: The direction to score ('up' or 'down'). Only applies to habits.
        :returns: The updated task, or None if not found.
        :raises TypeError: If trying to score a Reward task.
        """
        task = self.get_task_by_id(task_id)
        if not task:
            log.warning("Task with ID '{}' not found for scoring.", task_id)
            return None

        updates: dict[str, Any] = {}
        if isinstance(task, TaskTodo):
            updates["completed"] = True
            updates["status"] = TodoStatus.COMPLETED
        elif isinstance(task, TaskDaily):
            updates["completed"] = True
            updates["status"] = DailyStatus.COMPLETED_TODAY
        elif isinstance(task, TaskHabit):
            if direction == "up" and task.up:
                updates["counter_up"] = task.counter_up + 1
            elif direction == "down" and task.down:
                updates["counter_down"] = task.counter_down + 1
            else:
                log.info(
                    "No change for habit '{}' with direction '{}' (up: {}, down: {}).",
                    task_id,
                    direction,
                    task.up,
                    task.down,
                )
                return task  # No change if direction is invalid for the habit

            updates["status"] = habit_status(
                updates.get("counter_up", task.counter_up) > task.counter_up,
                updates.get("counter_down", task.counter_down) > task.counter_down,
                task.value,
            )
        elif isinstance(task, TaskReward):
            msg = "Rewards cannot be 'scored'. They are purchased."
            log.error("{}", msg)
            raise TypeError(msg)

        log.info("Task with ID '{}' scored successfully.", task_id)
        return self.modify_task(task_id, updates)

    def get_task_by_id(self, task_id: str) -> AnyTask | None:
        """Find a task by its ID across all task types.

        :param task_id: The ID of the task.
        :returns: The matching task, or None if not found.
        """
        return next((task for task in self.all_tasks if task.id == task_id), None)

    def get_tasks_by_status(self, status: TaskStatusType) -> list[AnyTask]:
        """Get all tasks that match a specific status enum.

        :param status: The status to filter by.
        :returns: A list of matching tasks.
        """
        return [
            task
            for task in self.all_tasks
            if hasattr(task, "status") and task.status == status
        ]

    def get_tasks_by_challenge_id(self, challenge_id: str) -> list[AnyTask]:
        """Get all tasks associated with a given challenge ID.

        :param challenge_id: The ID of the challenge.
        :returns: A list of matching tasks.
        """
        return [task for task in self.all_tasks if task.challenge_id == challenge_id]

    def get_tasks_by_broken_status(
        self,
        is_task_broken: bool | None = None,
        is_challenge_broken: bool | None = None,
    ) -> list[AnyTask]:
        """Get tasks by their broken status.

        :param is_task_broken: Filter by tasks that are individually broken.
        :param is_challenge_broken: Filter by tasks part of a broken challenge.
        :returns: A list of matching tasks.
        """
        results = self.all_tasks
        if is_task_broken is not None:
            results = [t for t in results if t.task_broken == is_task_broken]
        if is_challenge_broken is not None:
            results = [t for t in results if t.challenge_broken == is_challenge_broken]
        return results

    def get_tasks_by_date(self, due_date: date) -> list[TaskTodo | TaskDaily]:
        """Get all Todos and Dailies due on a specific date.

        :param due_date: The date to check for.
        :returns: A list of Todos and Dailies due on that date.
        """
        due_todos = [
            todo
            for todo in self.todos
            if todo.due_date and todo.due_date.date() == due_date
        ]
        due_dailies = [
            daily
            for daily in self.dailys
            if any(
                DateTimeHandler(timestamp=d).local_datetime
                and DateTimeHandler(timestamp=d).local_datetime == due_date
                for d in daily.next_due
            )
        ]
        return due_todos + due_dailies

    def get_overdue_todos(self) -> list[TaskTodo]:
        """Get all overdue todo tasks.

        :returns: A list of overdue todo tasks.
        """
        return [todo for todo in self.todos if todo.status == TodoStatus.OVERDUE]

    def get_due_dailies(self) -> list[TaskDaily]:
        """Get all daily tasks that are currently due and not completed.

        :returns: A list of due and incomplete daily tasks.
        """
        return [
            daily for daily in self.dailys if daily.due_today and not daily.completed
        ]

    def delete_multiple_tasks(self, task_ids: list[str]) -> list[AnyTask]:
        """Delete multiple tasks at once.

        :param task_ids: A list of task IDs to delete.
        :returns: A list of the deleted task instances.
        """
        return [
            deleted_task
            for task_id in task_ids
            if (deleted_task := self.delete_task(task_id))
        ]

    def update_multiple_tasks(
        self,
        updates: dict[str, dict[str, Any]],
    ) -> list[AnyTask]:
        """Update multiple tasks at once.

        :param updates: A dictionary where keys are task IDs and values are dictionaries of updates.
        :returns: A list of the updated task instances.
        """
        updated_tasks = []
        for task_id, task_updates in updates.items():
            if updated_task := self.modify_task(task_id, task_updates):
                updated_tasks.append(updated_task)
        return updated_tasks

    def add_checklist_item(
        self,
        task_id: str,
        text: str,
        completed: bool = False,
    ) -> tuple[TaskChecklist | None, AnyTask | None] | None:
        """Add a new subtask (checklist item) to a Todo or Daily.

        :param task_id: The ID of the parent task (must be a Todo or Daily).
        :param text: The text content of the checklist item.
        :param completed: The initial completion status of the item.
        :returns: A tuple containing the new TaskChecklist and the updated parent task, or None if invalid.
        """
        parent_task = self.get_task_by_id(task_id)
        if not isinstance(parent_task, (TaskTodo, TaskDaily)):
            log.warning(
                "Task {} is not a Todo or Daily; cannot add checklist.",
                task_id,
            )
            return None

        # Determine the position for the new subtask
        position = parent_task.checklist_total + 1

        new_subtask = TaskChecklist(
            id=str(uuid.uuid4()),
            text=text,
            completed=completed,
            parent_task_id=task_id,
            status=TaskStatus.COMPLETED if completed else TaskStatus.AVAILABLE,
            position=position,
        )
        self.subtasks.append(new_subtask)

        # Recalculate parent task checklist stats
        total = parent_task.checklist_total + 1
        completed_count = parent_task.checklist_completed + (1 if completed else 0)
        progress = completed_count / total if total > 0 else 0.0

        updates: dict[str, Any] = {
            "checklist": [*parent_task.checklist, new_subtask.id],
            "checklist_total": total,
            "checklist_completed": completed_count,
            "checklist_progress": progress,
        }
        if isinstance(parent_task, TaskTodo):
            updates["checklist_percentage"] = int(progress * 100)

        updated_parent = self.modify_task(task_id, updates)
        log.info(
            "Added checklist item to task '{}'. New item ID: '{}'",
            task_id,
            new_subtask.id,
        )
        return new_subtask, updated_parent

    def update_checklist_item(
        self,
        subtask_id: str,
        updates: dict[str, Any],
    ) -> TaskChecklist | None:
        """Update a checklist item and recalculate parent task progress.

        :param subtask_id: The ID of the subtask to update.
        :param updates: A dictionary of attributes to update for the subtask.
        :returns: The updated TaskChecklist instance, or None if not found.
        """
        for i, subtask in enumerate(self.subtasks):
            if subtask.id == subtask_id:
                old_completed = subtask.completed
                self.subtasks[i] = subtask.model_copy(update=updates)

                # Recalculate parent task progress if completion status changed
                if "completed" in updates and updates["completed"] != old_completed:
                    self._recalculate_parent_progress(subtask.parent_task_id)
                log.info("Checklist item '{}' updated successfully.", subtask_id)
                return self.subtasks[i]
        log.warning("Checklist item with ID '{}' not found for update.", subtask_id)
        return None

    def delete_checklist_item(self, subtask_id: str) -> TaskChecklist | None:
        """Delete a checklist item and update parent task.

        :param subtask_id: The ID of the subtask to delete.
        :returns: The deleted TaskChecklist instance, or None if not found.
        """
        for i, subtask in enumerate(self.subtasks):
            if subtask.id == subtask_id:
                deleted_subtask = self.subtasks.pop(i)
                self._recalculate_parent_progress(subtask.parent_task_id)
                log.info("Checklist item '{}' deleted successfully.", subtask_id)
                return deleted_subtask
        log.warning("Checklist item with ID '{}' not found for deletion.", subtask_id)
        return None

    def _recalculate_parent_progress(self, parent_task_id: str) -> None:
        """Recalculate checklist progress for a parent task.

        :param parent_task_id: The ID of the parent task whose progress needs recalculation.
        """
        parent_subtasks = [
            s for s in self.subtasks if s.parent_task_id == parent_task_id
        ]
        total = len(parent_subtasks)
        completed = sum(1 for s in parent_subtasks if s.completed)
        progress = completed / total if total > 0 else 0.0

        updates = {
            "checklist_total": total,
            "checklist_completed": completed,
            "checklist_progress": progress,
            "checklist": [s.id for s in parent_subtasks],
        }  # Update checklist IDs

        parent_task = self.get_task_by_id(parent_task_id)
        if isinstance(parent_task, TaskTodo):
            updates["checklist_percentage"] = int(progress * 100)

        self.modify_task(parent_task_id, updates)
        log.info(
            "Recalculated checklist progress for parent task '{}'.",
            parent_task_id,
        )

    def get_tag_count(self) -> dict[Any, Any]:
        tags = {}
        for task in self.all_tasks:
            for tag in task.tags:
                if tag not in tags:
                    tags[tag] = 1
                else:
                    tags[tag] += 1
        return dict(sorted(tags.items(), key=lambda x: x[1], reverse=True))

    # ──────────────────────────────────────────────────────────────────────────────
    def __len__(self) -> int:
        """Return the total number of primary tasks."""
        return len(self.all_tasks)

    def __iter__(self) -> Iterator[AnyTask]:
        """Return an iterator over all primary tasks."""
        return iter(self.all_tasks)

    def __getitem__(self, index: int | slice) -> AnyTask | list[AnyTask]:
        """Retrieve a task or slice of tasks from the combined list."""
        if isinstance(index, slice):
            return cast("list[AnyTask]", self.all_tasks[index])
        return self.all_tasks[index]
