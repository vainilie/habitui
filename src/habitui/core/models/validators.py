# ♥♥─── Model Validators and Helpers ───────────────────────────────────
"""Validation functions and helper logic for HabiTui models."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlmodel import (
    JSON as SA_JSON,
    TypeDecorator,
)
import emoji_data_python
from sqlalchemy.dialects.postgresql import JSONB

from habitui.utils import DateTimeHandler

from .base_enums import TaskStatus, TodoStatus, DailyStatus, HabitStatus


if TYPE_CHECKING:
    import datetime

    from box import Box

    from .user_model import UserCollection
HIGHEST_VALUE: int = 5
HIGH_VALUE: int = 2
LOW_VALUE: int = -2
LOWEST_VALUE: int = -5
WEEK_IN_DAYS: int = 7


def replace_emoji_shortcodes(value: Any) -> str:
    """Replace emoji shortcodes (e.g., :smile:) with Unicode characters."""
    return emoji_data_python.replace_colons(str(value or "")).strip()


def normalize_attribute(value: str | None) -> str | None:
    """Convert abbreviated character attributes to their full names."""
    if not value:
        return None
    attribute_map = {"str": "strength", "per": "perception", "con": "constitution", "int": "intelligence"}
    return attribute_map.get(value.lower(), value)


# ─── Datetime & Type Validators ──────────────────────────────────────────────
def parse_datetime(value: Any) -> datetime.datetime | None:
    """Parse a string or other type into a timezone-aware UTC datetime object."""
    if not value:
        return None
    return DateTimeHandler(timestamp=value).utc_datetime


def parse_to_float(value: Any, default: float = 0.0) -> float:
    """Convert a value to a float, returning a default on failure."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


class PydanticJSON(TypeDecorator):
    """Custom SQLAlchemy type for storing Python dicts/lists as JSON."""

    impl = JSONB().with_variant(SA_JSON(), "sqlite")
    cache_ok = True

    def process_bind_param(self, value: Any | None, _dialect: Any) -> Any | None:
        """Process the value for binding to a query parameter."""
        if value is None:
            return None
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        return value

    def process_result_value(self, value: Any | None, _dialect: Any) -> Any | None:
        """Process the value returned from a DB query."""
        return value


# ─── Status Calculation (Habitica-specific logic) ─────────────────────────────
def _determine_habit_status_by_value(value: float) -> HabitStatus:
    """Determine habit status based on a numerical value."""
    if value > HIGHEST_VALUE:
        return HabitStatus.FLOW
    if value < LOWEST_VALUE:
        return HabitStatus.STRUGGLING
    if value > HIGH_VALUE:
        return HabitStatus.ON_TRACK
    if value < LOW_VALUE:
        return HabitStatus.EFFORT
    if LOW_VALUE <= value <= HIGH_VALUE:
        return HabitStatus.CONFLICTING
    return HabitStatus.NEUTRAL


def _determine_negative_habit_status(value: float) -> HabitStatus:
    """Determine status for a negative habit based on its value."""
    if value < LOWEST_VALUE:
        return HabitStatus.STRUGGLING
    if value < LOW_VALUE:
        return HabitStatus.EFFORT
    if value > HIGH_VALUE:
        return HabitStatus.CONFLICTING
    return HabitStatus.NEUTRAL


def _determine_positive_habit_status(value: float) -> HabitStatus:
    """Determine status for a positive habit based on its value."""
    if value > HIGHEST_VALUE:
        return HabitStatus.FLOW
    if value > HIGH_VALUE:
        return HabitStatus.ON_TRACK
    if value < LOW_VALUE:
        return HabitStatus.CONFLICTING
    return HabitStatus.NEUTRAL


def habit_status(up: bool, down: bool, value: float) -> HabitStatus:
    """Calculate the overall status for a habit."""
    if not up and not down:
        return HabitStatus.NEGLECTED
    if up and not down:
        return _determine_positive_habit_status(value)
    if not up and down:
        return _determine_negative_habit_status(value)
    return _determine_habit_status_by_value(value)


def _get_date_based_todo_status(due_date: datetime.datetime) -> TodoStatus:
    """Determine ToDo status based on its due date."""
    now_utc = DateTimeHandler.get_utc_now()
    due_date_handler = DateTimeHandler(timestamp=due_date)
    due_date_utc = due_date_handler.utc_datetime
    if due_date_utc is None:
        return TodoStatus.SOMEDAY
    if due_date_utc < now_utc:
        return TodoStatus.OVERDUE
    delta_days = (due_date_utc - now_utc).days
    if delta_days <= WEEK_IN_DAYS:
        return TodoStatus.UPCOMING
    return TodoStatus.SCHEDULED


def todo_status(completed: bool, checklist_progress: float, due_date: datetime.datetime | None) -> TodoStatus:
    """Calculate the overall status for a todo."""
    if completed:
        return TodoStatus.COMPLETED
    if checklist_progress >= 1.0:
        return TodoStatus.READY_TO_COMPLETE
    if checklist_progress > 0.0:
        return TodoStatus.IN_PROGRESS
    if due_date is None:
        return TodoStatus.SOMEDAY
    return _get_date_based_todo_status(due_date)


def _get_daily_completion_status(completed: bool, due_today: bool, due_yesterday: bool) -> DailyStatus | None:
    """Determine daily completion status."""
    if completed:
        if due_today:
            return DailyStatus.COMPLETED_TODAY
        if due_yesterday:
            return DailyStatus.COMPLETED_YESTERDAY
    return None


def _get_daily_progress_status(checklist_progress: float) -> DailyStatus:
    """Determine daily progress status."""
    if checklist_progress >= 1.0:
        return DailyStatus.READY_TO_COMPLETE
    if checklist_progress > 0.0:
        return DailyStatus.IN_PROGRESS
    return DailyStatus.DUE_TODAY


def daily_status(completed: bool, due_today: bool, due_yesterday: bool, checklist_progress: float, cron: float) -> DailyStatus:
    """Calculate the overall status for a daily."""
    completion_status = _get_daily_completion_status(completed, due_today, due_yesterday)
    if completion_status:
        return completion_status
    if cron is True and due_yesterday:
        return DailyStatus.MISSED_YESTERDAY
    if due_today:
        return _get_daily_progress_status(checklist_progress)
    if checklist_progress > 0.0:
        return DailyStatus.IN_PROGRESS
    if due_yesterday:
        return DailyStatus.DUE_YESTERDAY
    return DailyStatus.INACTIVE


def calculate_task_damage(data: Box, user: UserCollection) -> None:
    """Calculate and sets user and party damage on the task data."""
    data["user_damage"] = 0.0
    data["party_damage"] = 0.0
    should_apply_damage = False
    if user.is_sleeping() is True and user.get_stealth() >= 1:
        should_apply_damage = False
    if data.is_due is True and not data.completed:
        should_apply_damage = True
    if not should_apply_damage:
        return
    effective_con = user.get_effective_constitution()
    # Clamp task value to a specific range
    task_value_clamped = max(-47.27, min(data.value, 21.27))
    base_damage_factor = 0.9747**task_value_clamped
    checklist_mitigation_factor = 1.0 - data.checklist_progress
    effective_damage_factor = base_damage_factor * checklist_mitigation_factor
    # Calculate user HP damage with constitution mitigation
    user_con_mitigation = max(0.1, 1.0 - (effective_con / 250.0))
    hp_damage_to_user = effective_damage_factor * user_con_mitigation * data.priority * 2.0
    data.user_damage = max(0.0, round(hp_damage_to_user, 1))
    # Calculate boss damage for party quests
    boss_strength = user.computed_stats.boss_str
    if boss_strength and boss_strength > 0:
        # Apply different scaling for high vs low priority tasks
        party_damage_factor = effective_damage_factor * data.priority if data.priority < 1 else effective_damage_factor
        damage_to_boss = party_damage_factor * boss_strength
        data.party_damage = max(0.0, round(damage_to_boss, 1))


# ─── API Data Extraction & Processing ─────────────────────────────────────────
def extract_subtasks(raw_checklist: list[Box] | None, parent_task_id: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Extract subtasks, calculates stats, and prepares data for model creation."""
    stats = {"checklist_total": 0, "checklist_completed": 0, "checklist_progress": 0.0, "checklist": []}
    if not raw_checklist:
        return [], stats
    subtask_models_data = []
    for i, item in enumerate(raw_checklist):
        is_completed = item.get("completed", False)
        subtask_models_data.append({"id": item.id, "text": item.text, "completed": is_completed, "status": TaskStatus.COMPLETED if is_completed else TaskStatus.AVAILABLE, "parent_task_id": parent_task_id, "position": i})
    total = len(subtask_models_data)
    completed = sum(1 for item in subtask_models_data if item["completed"])
    progress = float(completed) / total if total > 0 else 0.0
    stats.update({"checklist_total": total, "checklist_completed": completed, "checklist_progress": progress, "checklist": [item["id"] for item in subtask_models_data]})
    return subtask_models_data, stats


def parse_nested_challenge(challenge_box: Box | None, task_id: str) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Parse nested challenge data from API response."""
    task_updates: dict[str, bool] = {"challenge": False}
    if not challenge_box:
        return None, task_updates
    # Initialize challenge-related updates
    new_updates = {"challenge": True, "challenge_id": challenge_box.id, "challenge_task_id": challenge_box.task_id, "challenge_shortname": challenge_box.short_name, "challenge_broken": False, "task_broken": False, "challenge_winner": None}
    task_updates.update(new_updates)
    broken_tasks: list[str] = []
    broken_status = challenge_box.get("broken")
    if broken_status:
        task_updates["task_broken"] = True
        broken_tasks.append(task_id)
        if broken_status == "TASK_DELETED":
            task_updates["challenge_broken"] = False
        else:
            task_updates["challenge_broken"] = True
            if broken_status == "CHALLENGE_CLOSED":
                task_updates["challenge_winner"] = challenge_box.get("winner")
    challenge_model = {"id": challenge_box.id, "short_name": challenge_box.short_name, "broken": task_updates["challenge_broken"], "winner": task_updates["challenge_winner"], "tasks_ids": [task_id], "broken_tasks_ids": broken_tasks}
    return challenge_model, task_updates


def clean_tag_name(name: str) -> str:
    """Clean a tag name by replacing emoji shortcodes and stripping whitespace."""
    cleaned = emoji_data_python.replace_colons(name)
    # Use split() without arguments to handle all whitespace, then join with single space
    return " ".join(cleaned.strip().split())
