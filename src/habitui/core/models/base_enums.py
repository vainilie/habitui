# ♥♥─── Model Enums ────────────────────────────────────────────────────
from __future__ import annotations

from enum import Enum, StrEnum


class TaskType(StrEnum):
    """Enumeration for different types of tasks."""

    HABIT = "habit"
    DAILY = "daily"
    TODO = "todo"
    REWARD = "reward"


class ScoreDirection(StrEnum):
    """Enumeration for the scoring direction of a task."""

    UP = "up"
    DOWN = "down"


class Attribute(StrEnum):
    """Enumeration for character attributes."""

    STRENGTH = "str"
    INTELLIGENCE = "int"
    PERCEPTION = "per"
    CONSTITUTION = "con"


class Priority(float, Enum):
    """Enumeration for task priority levels as numeric values."""

    TRIVIAL = 0.1
    EASY = 1.0
    MEDIUM = 1.5
    HARD = 2.0


class Frequency(StrEnum):
    """Enumeration for the frequency of recurring tasks."""

    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class TodoStatus(StrEnum):
    """Status categories for To-Do tasks."""

    COMPLETED = "completed"
    READY_TO_COMPLETE = "ready_to_complete"
    IN_PROGRESS = "in_progress"
    AVAILABLE = "available"
    UPCOMING = "upcoming"
    SCHEDULED = "scheduled"
    OVERDUE = "overdue"
    SOMEDAY = "someday"


class DailyStatus(StrEnum):
    """Status categories for Daily tasks."""

    COMPLETED_TODAY = "completed_today"
    COMPLETED_YESTERDAY = "completed_yesterday"
    READY_TO_COMPLETE = "ready_to_complete"
    IN_PROGRESS = "in_progress"
    DUE_TODAY = "due_today"
    DUE_YESTERDAY = "due_yesterday"
    MISSED_YESTERDAY = "missed_yesterday"
    INACTIVE = "inactive"
    SCHEDULED_FUTURE = "scheduled_future"


class HabitStatus(StrEnum):
    """Qualitative evaluation of Habits based on value."""

    NEUTRAL = "neutral"
    ON_TRACK = "on_track"
    FLOW = "flow"
    STRUGGLING = "struggling"
    EFFORT = "effort"
    CONFLICTING = "conflicting"
    NEGLECTED = "neglected"


class RewardStatus(StrEnum):
    """Status of a reward task based on affordability."""

    AFFORDABLE = "affordable"
    UNAFFORDABLE = "unaffordable"


class TaskStatus(StrEnum):
    """General-purpose task status for subtasks."""

    COMPLETED = "completed"
    AVAILABLE = "available"
    UNKNOWN = "unknown"
    READY_TO_COMPLETE = "ready_to_complete"
    IN_PROGRESS = "in_progress"
    UPCOMING = "upcoming"
    SCHEDULED = "scheduled"
    OVERDUE = "overdue"
    SOMEDAY = "someday"


class TaskKeepOption(StrEnum):
    """Options for deciding whether to keep or remove individual tasks."""

    KEEP = "keep"
    REMOVE = "remove"


class ChallengeTaskKeepOption(StrEnum):
    """Options for managing tasks when a user leaves a challenge."""

    KEEP_ALL = "keep-all"
    REMOVE_ALL = "remove-all"


class TagsCategory(StrEnum):
    """Fixed categories for root parent tags."""

    ATTRIBUTE = "ATTRIBUTE"
    OWNERSHIP = "OWNERSHIP"


class TagsTrait(StrEnum):
    CHALLENGE = "challenge"
    PERSONAL = "personal"
    LEGACY = "legacy"
    STRENGTH = "str"
    INTELLIGENCE = "int"
    PERCEPTION = "per"
    CONSTITUTION = "con"
    NO_ATTRIBUTE = "no_attr"
