# ♥♥─── HabiTui Creation Models ────────────────────────────────────────────────
"""Defines Pydantic models used for creating new entities via the Habitica API."""

from __future__ import annotations

from datetime import date as python_date
from typing import Annotated, Any
from uuid import UUID

from pydantic import Field, field_validator

from .base_enums import Attribute, Frequency, Priority, TaskType
from .base_model import HabiTuiBaseModel
from .validators import replace_emoji_shortcodes


class ChecklistItemCreate(HabiTuiBaseModel):
    """Represents an individual checklist item during task creation.

    :param text: The text of the checklist item.
    """

    text: str

    @field_validator("text", mode="before")
    @classmethod
    def _parse_text(cls, value: Any) -> str:
        """Cleans and replaces emoji shortcodes in the text.

        :param value: The input text.
        :returns: The cleaned text.
        """
        return replace_emoji_shortcodes(value)


class ReminderCreate(HabiTuiBaseModel):
    """Represents a reminder to be set during task creation.

    :param start_date: The date when the reminder starts.
    :param time: The time of the reminder (e.g., "HH:MM").
    """

    start_date: python_date
    time: str


class DailyRepeatPattern(HabiTuiBaseModel):
    """Defines the weekly repeat pattern for a Daily task.

    :param su: Repeat on Sunday.
    :param m: Repeat on Monday.
    :param t: Repeat on Tuesday.
    :param w: Repeat on Wednesday.
    :param th: Repeat on Thursday.
    :param f: Repeat on Friday.
    :param s: Repeat on Saturday.
    """

    su: bool = Field(True, description="Repeat on Sunday.")
    m: bool = Field(True, description="Repeat on Monday.")
    t: bool = Field(True, description="Repeat on Tuesday.")
    w: bool = Field(True, description="Repeat on Wednesday.")
    th: bool = Field(True, description="Repeat on Thursday.")
    f: bool = Field(True, description="Repeat on Friday.")
    s: bool = Field(True, description="Repeat on Saturday.")


class TaskBaseCreate(HabiTuiBaseModel):
    """Base model with common fields for creating any type of task.

    :param text: The main text/description of the task.
    :param tags: List of tag UUIDs.
    :param alias: An optional alias for the task.
    :param notes: Additional notes for the task.
    """

    text: str = Field(..., min_length=1)
    tags: list[UUID] | None = None
    alias: str | None = None
    notes: str | None = None

    @field_validator("text", "notes", "alias", mode="before")
    @classmethod
    def _parse_text_fields(cls, value: Any) -> str | None:
        """Cleans and replaces emoji shortcodes in text fields.

        :param value: The input text.
        :returns: The cleaned text, or None if input was None.
        """
        return replace_emoji_shortcodes(value) if value is not None else None


class HabitCreate(TaskBaseCreate):
    """Model for creating a new Habit task.

    :param type: Type of the task (always TaskType.HABIT).
    :param attribute: The character attribute associated.
    :param up: True if the habit can be scored positively.
    :param down: True if the habit can be scored negatively.
    :param priority: Priority of the habit.
    """

    type: TaskType = Field(TaskType.HABIT, frozen=True)
    attribute: Attribute | None = None
    up: bool = True
    down: bool = True
    priority: Priority = Priority.EASY


class DailyCreate(TaskBaseCreate):
    """Model for creating a new Daily task.

    :param type: Type of the task (always TaskType.DAILY).
    :param attribute: The character attribute associated.
    :param priority: Priority of the daily.
    :param reminders: List of reminders for the daily.
    :param frequency: Frequency of the daily.
    :param repeat: Weekly repeat pattern.
    :param every_x: Repeats every X days/weeks/months/years.
    :param days_of_month: Specific days of the month to repeat.
    :param weeks_of_month: Specific weeks of the month to repeat.
    :param start_date: Start date for the daily.
    :param collapse_checklist: True to collapse checklist in UI.
    :param checklist: List of checklist items.
    """

    type: TaskType = Field(TaskType.DAILY, frozen=True)
    attribute: Attribute | None = None
    priority: Priority = Priority.EASY
    reminders: list[ReminderCreate] | None = None
    frequency: Frequency = Frequency.WEEKLY
    repeat: DailyRepeatPattern = Field(default_factory=DailyRepeatPattern)  # type: ignore
    every_x: int = Field(1, ge=1)
    days_of_month: list[int] | None = None
    weeks_of_month: list[int] | None = None
    start_date: python_date | None = None
    collapse_checklist: bool = False
    checklist: list[ChecklistItemCreate] | None = None


class TodoCreate(TaskBaseCreate):
    """Model for creating a new To-Do task.

    :param type: Type of the task (always TaskType.TODO).
    :param attribute: The character attribute associated.
    :param date: Due date for the todo.
    :param priority: Priority of the todo.
    :param reminders: List of reminders for the todo.
    :param collapse_checklist: True to collapse checklist in UI.
    :param checklist: List of checklist items.
    """

    type: TaskType = Field(TaskType.TODO, frozen=True)
    attribute: Attribute | None = None
    date: python_date | None = None
    priority: Priority = Priority.EASY
    reminders: list[ReminderCreate] | None = None
    collapse_checklist: bool = False
    checklist: list[ChecklistItemCreate] | None = None


class RewardCreate(TaskBaseCreate):
    """Model for creating a new Reward task.

    :param type: Type of the task (always TaskType.REWARD).
    :param value: Gold value of the reward.
    """

    type: TaskType = Field(TaskType.REWARD, frozen=True)
    value: float = Field(0.0, ge=0)


TaskCreatePayload = Annotated[HabitCreate | DailyCreate | TodoCreate | RewardCreate, Field(discriminator="type")]


class ChallengeCreate(HabiTuiBaseModel):
    """Model for creating a new Challenge.

    :param group: UUID of the group where the challenge will be created.
    :param name: Name of the challenge.
    :param short_name: Short name of the challenge.
    :param summary: Summary of the challenge.
    :param description: Description of the challenge.
    :param prize: Prize value for the challenge winner.
    """

    group: UUID
    name: str = Field(..., min_length=1, max_length=150)
    short_name: str = Field(..., min_length=1, max_length=30)
    summary: str | None = Field(None, max_length=250)
    description: str | None = None
    prize: int = Field(0, ge=0)

    @field_validator("name", "short_name", "summary", "description", mode="before")
    @classmethod
    def _parse_text_fields(cls, value: Any) -> str | None:
        """Cleans and replaces emoji shortcodes in text fields.

        :param value: The input text.
        :returns: The cleaned text, or None if input was None.
        """
        return replace_emoji_shortcodes(value) if value is not None else None
