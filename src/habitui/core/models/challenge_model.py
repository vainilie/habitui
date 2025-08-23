# ♥♥─── HabiTui Challenge Models ───────────────────────────────────────────────

from __future__ import annotations

from typing import Any, Self
import datetime

from box import Box
from pydantic import ValidationError, field_validator
from sqlmodel import Field, Column

from habitui.core.models import validators
from habitui.custom_logger import log

from .base_enums import TaskType, Frequency
from .base_model import HabiTuiSQLModel, HabiTuiBaseModel
from .task_model import TaskCollection, ChallengeInTask
from .user_model import UserCollection, ChallengeInUser


class ChallengeTaskBase(HabiTuiSQLModel, table=False):
    """Abstract base model for all challenge task types."""

    challenge_id: str = Field(index=True)
    type: TaskType
    text: str
    notes: str | None = None
    value: float = 0.0
    priority: float = 1.0
    attribute: str | None = None
    by_habitica: bool = False
    created_at: datetime.datetime
    updated_at: datetime.datetime
    challenge: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(validators.PydanticJSON),
    )
    group: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(validators.PydanticJSON),
    )
    reminders: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(validators.PydanticJSON),
    )

    @field_validator("text", "notes", mode="before")
    @classmethod
    def _clean_text(cls, v: Any) -> str:
        """Clean text fields by replacing emoji shortcodes."""
        return validators.replace_emoji_shortcodes(v)

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _parse_dates(cls, v: Any) -> datetime.datetime | None:
        """Parse date strings into timezone-aware datetime objects."""
        return validators.parse_datetime(v)

    @field_validator("attribute", mode="before")
    @classmethod
    def _normalize_attr(cls, v: Any) -> str | None:
        """Normalize attribute names."""
        return validators.normalize_attribute(v)


class ChallengeInfo(HabiTuiSQLModel, table=True):
    """Represent a single Habitica Challenge and its metadata.

    :param name: The full name of the challenge.
    :param short_name: A shorter name for the challenge.
    :param summary: A brief summary of the challenge.
    :param description: Full description of the challenge.
    :param prize: Prize awarded for the challenge.
    :param member_count: Number of members in the challenge.
    :param created_at: Timestamp when the challenge was created.
    :param updated_at: Timestamp when the challenge was last updated.
    :param group_name: Name of the group hosting the challenge.
    :param group_type: Type of the group.
    :param group_id: ID of the group.
    :param leader_id: User ID of the challenge leader.
    :param leader_username: Username of the challenge leader.
    :param leader_name: Display name of the challenge leader.
    :param owned: True if the current user owns this challenge.
    :param joined: True if the current user has joined this challenge.
    :param left: True if the current user has left this challenge.
    :param legacy: True if it's a legacy challenge.
    :param completed: True if the challenge is completed.
    :param winner: ID of the challenge winner.
    :param categories: List of challenge categories.
    :param habits: List of habit task IDs in this challenge.
    :param dailys: List of daily task IDs in this challenge.
    :param todos: List of todo task IDs in this challenge.
    :param rewards: List of reward task IDs in this challenge.
    """

    __tablename__ = "challenge_info"  # type: ignore

    name: str
    short_name: str | None = None
    summary: str | None = None
    description: str | None = None
    prize: int = 0
    member_count: int = 0
    created_at: datetime.datetime | None = None
    updated_at: datetime.datetime | None = None

    group_name: str | None = None
    group_type: str | None = None
    group_id: str | None = None

    leader_id: str | None = None
    leader_username: str | None = None
    leader_name: str | None = None

    owned: bool = False
    joined: bool = False
    left: bool = False
    legacy: bool = False
    completed: bool = False
    winner: str | None = None

    categories: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(validators.PydanticJSON),
    )
    habits: list[str] = Field(
        default_factory=list,
        sa_column=Column(validators.PydanticJSON),
    )
    dailys: list[str] = Field(
        default_factory=list,
        sa_column=Column(validators.PydanticJSON),
    )
    todos: list[str] = Field(
        default_factory=list,
        sa_column=Column(validators.PydanticJSON),
    )
    rewards: list[str] = Field(
        default_factory=list,
        sa_column=Column(validators.PydanticJSON),
    )

    @field_validator(
        "name",
        "short_name",
        "summary",
        "description",
        "leader_name",
        "group_name",
        mode="before",
    )
    @classmethod
    def _clean_text(cls, v: Any) -> str:
        """Clean text fields by replacing emoji shortcodes."""
        return validators.replace_emoji_shortcodes(v)

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _parse_dates(cls, v: Any) -> datetime.datetime | None:
        """Parse date strings into timezone-aware datetime objects."""
        return validators.parse_datetime(v)

    @classmethod
    def _flatten_api_data(
        cls,
        data: Box,
        user_id: str | None = None,
        user_challenge_ids: set[str] | None = None,
        task_challenge_ids: set[str] | None = None,
    ) -> dict[str, Any]:
        """Flatten Box API data into a dictionary for model validation.

        :param data: The raw API data as a Box object.
        :param user_id: The ID of the current user.
        :param user_challenge_ids: Set of challenge IDs the user has joined.
        :param task_challenge_ids: Set of challenge IDs from user's tasks.
        :returns: A dictionary with flattened data.
        """
        flat_data = data.copy()

        if group := data.group:
            flat_data["group_name"] = group.name
            flat_data["group_id"] = group.id
            flat_data["group_type"] = group.type

            if group.name != "Tavern":
                flat_data["legacy"] = True

        if leader := data.leader:
            flat_data["leader_id"] = leader.id
            flat_data["leader_name"] = leader.profile.name

            if local_auth := leader.auth.get("local"):
                flat_data["leader_username"] = local_auth.username

        if t_order := data.tasks_order:
            flat_data.update(t_order.to_dict())

        if (
            user_id
            and user_challenge_ids is not None
            and task_challenge_ids is not None
        ):
            flat_data["owned"] = data.leader and data.leader.id == user_id
            flat_data["joined"] = (
                data.id in user_challenge_ids or data.id in task_challenge_ids
            )
            flat_data["left"] = (
                data.id in user_challenge_ids and data.id not in task_challenge_ids
            )

        return flat_data.to_dict()

    @classmethod
    def from_api_data(
        cls,
        data: Box,
        user_context: UserCollection | None,
        task_challenge_ids: set[str],
    ) -> Self:
        """Create a ChallengeInfo instance from API data.

        :param data: The raw API data for the challenge.
        :param user_context: The user's collection for contextual info.
        :param task_challenge_ids: Set of challenge IDs from user's tasks.
        :returns: A ChallengeInfo instance.
        """
        user_id = user_context.profile.id if user_context else None
        user_challenge_ids = (
            {c.id for c in user_context.challenges} if user_context else set()
        )

        flat_data = cls._flatten_api_data(
            data,
            user_id,
            user_challenge_ids,
            task_challenge_ids,
        )

        return cls.model_validate(flat_data)


# ─── Concrete Challenge Task Models ──────────────────────────────────────────


class ChallengeTaskReward(ChallengeTaskBase, table=True):
    """Represents a reward task within a challenge."""

    __tablename__ = "challenge_task_reward"  # type: ignore
    type: TaskType = TaskType.REWARD


class ChallengeTaskHabit(ChallengeTaskBase, table=True):
    """Represents a habit task within a challenge."""

    __tablename__ = "challenge_task_habit"  # type: ignore
    type: TaskType = TaskType.HABIT
    up: bool = True
    down: bool = True
    counter_up: int = Field(default=0)
    counter_down: int = Field(default=0)
    frequency: Frequency = Frequency.DAILY
    challenge: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(validators.PydanticJSON),
    )
    group: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(validators.PydanticJSON),
    )
    reminders: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(validators.PydanticJSON),
    )


class ChallengeTaskTodo(ChallengeTaskBase, table=True):
    """Represents a To-Do task within a challenge."""

    __tablename__ = "challenge_task_todo"  # type: ignore
    type: TaskType = TaskType.TODO
    date: datetime.datetime | None = None
    checklist: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(validators.PydanticJSON),
    )
    challenge: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(validators.PydanticJSON),
    )
    group: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(validators.PydanticJSON),
    )
    reminders: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(validators.PydanticJSON),
    )

    @field_validator("date", mode="before")
    @classmethod
    def _parse_due_date(cls, v: Any) -> datetime.datetime | None:
        """Parse the due date string into a datetime object."""
        return validators.parse_datetime(v)


class ChallengeTaskDaily(ChallengeTaskBase, table=True):
    """Represents a daily task within a challenge."""

    __tablename__ = "challenge_task_daily"  # type: ignore
    type: TaskType = TaskType.DAILY

    frequency: Frequency = Frequency.WEEKLY
    every_x: int = 1
    start_date: datetime.datetime | None = None

    streak: int = 0
    is_due: bool = Field(default=False)
    yester_daily: bool = Field(default=False)

    checklist: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(validators.PydanticJSON),
    )
    repeat: dict[str, bool] = Field(
        default_factory=dict,
        sa_column=Column(validators.PydanticJSON),
    )
    days_of_month: list[int] = Field(
        default_factory=list,
        sa_column=Column(validators.PydanticJSON),
    )
    weeks_of_month: list[int] = Field(
        default_factory=list,
        sa_column=Column(validators.PydanticJSON),
    )
    next_due: list[datetime.datetime | None] = Field(
        default_factory=list,
        sa_column=Column(validators.PydanticJSON),
    )
    challenge: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(validators.PydanticJSON),
    )
    group: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(validators.PydanticJSON),
    )
    reminders: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(validators.PydanticJSON),
    )

    @field_validator("start_date", mode="before")
    @classmethod
    def _parse_start_date(cls, v: Any) -> datetime.datetime | None:
        """Parse the start date string into a datetime object."""
        return validators.parse_datetime(v)

    @field_validator("next_due", mode="before")
    @classmethod
    def _parse_next_due_dates(cls, value: Any) -> list[datetime.datetime | None]:
        """Parse a list of next due date strings into datetime objects."""
        if not value:
            return []

        if isinstance(value, list):
            return [
                validators.parse_datetime(date_str)
                for date_str in value
                if date_str is not None
            ]

        return []


# ─── Collection Orchestrator ─────────────────────────────────────────────────


class ChallengeCollection(HabiTuiBaseModel):
    """A collection of all challenges and their associated tasks.

    :param challenges: List of challenge metadata.
    :param user_challenges: List of challenges the user is associated with.
    :param task_challenges: List of challenges associated with user's tasks.
    :param challenge_tasks_daily: List of daily tasks within challenges.
    :param challenge_tasks_habit: List of habit tasks within challenges.
    :param challenge_tasks_reward: List of reward tasks within challenges.
    :param challenge_tasks_todo: List of todo tasks within challenges.
    """

    challenge_tasks_daily: list[ChallengeTaskDaily] = Field(default_factory=list)
    challenge_tasks_habit: list[ChallengeTaskHabit] = Field(default_factory=list)
    challenge_tasks_reward: list[ChallengeTaskReward] = Field(default_factory=list)
    challenge_tasks_todo: list[ChallengeTaskTodo] = Field(default_factory=list)
    challenges: list[ChallengeInfo] = Field(default_factory=list)
    task_challenges: list[ChallengeInTask] = Field(default_factory=list)
    user_challenges: list[ChallengeInUser] = Field(default_factory=list)

    @classmethod
    def from_api_data(
        cls,
        challenges_data: list[dict[str, Any]] | None = None,
        challenge_tasks_data: list[dict[str, Any]] | None = None,
        user: UserCollection | None = None,
        tasks: TaskCollection | None = None,
    ) -> Self:
        """Parse raw API data into a ChallengeCollection.

        :param challenges_data: Raw API data for challenges.
        :param challenge_tasks_data: Raw API data for challenge tasks.
        :param user: User context for challenge relationships.
        :param tasks: Task context for challenge relationships.
        :returns: A populated ChallengeCollection instance.
        """
        if challenges_data and challenge_tasks_data:
            return cls.from_combined_data(
                challenges_data,
                challenge_tasks_data,
                user,
                tasks,
            )

        if challenges_data:
            return cls.from_challenges_data(challenges_data, user, tasks)

        if challenge_tasks_data:
            return cls.from_challenge_tasks_data(challenge_tasks_data, user, tasks)

        return cls(
            user_challenges=user.challenges if user else [],
            task_challenges=tasks.challenges if tasks else [],
        )

    @classmethod
    def from_challenges_data(
        cls,
        raw_challenges: list[dict],
        user: UserCollection | None,
        tasks: TaskCollection | None,
    ) -> Self:
        """Create a collection from challenge metadata only.

        :param raw_challenges: Raw API data for challenges.
        :param user: User context for challenge relationships.
        :param tasks: Task context for challenge relationships.
        :returns: A populated `ChallengeCollection` instance.
        """
        user_challenge_ids = {c.id for c in user.challenges} if user else set()
        task_challenge_ids = (
            {c.challenge_id for c in tasks.all_tasks if c.challenge_id}
            if tasks
            else set()
        )

        parsed_challenges = cls._parse_challenges_list(
            raw_challenges,
            user,
            user_challenge_ids,
            task_challenge_ids,
        )

        return cls(
            challenges=parsed_challenges,
            user_challenges=user.challenges if user else [],
            task_challenges=tasks.challenges if tasks else [],
        )

    @classmethod
    def from_challenge_tasks_data(
        cls,
        raw_tasks: list[dict],
        user: UserCollection | None = None,
        tasks: TaskCollection | None = None,
    ) -> Self:
        """Create a collection from challenge task data only.

        :param raw_tasks: Raw API data for challenge tasks.
        :param user: User context for challenge relationships.
        :param tasks: Task context for challenge relationships.
        :returns: A populated `ChallengeCollection` instance.
        """
        dailies, habits, rewards, todos = cls._parse_tasks_list(raw_tasks)

        return cls(
            user_challenges=user.challenges if user else [],
            task_challenges=tasks.challenges if tasks else [],
            challenge_tasks_daily=dailies,
            challenge_tasks_habit=habits,
            challenge_tasks_reward=rewards,
            challenge_tasks_todo=todos,
        )

    @classmethod
    def from_combined_data(
        cls,
        raw_challenges: list[dict[str, Any]],
        raw_tasks: list[dict[str, Any]],
        user: UserCollection | None,
        tasks: TaskCollection | None,
    ) -> Self:
        """Create a collection from both challenge metadata and task data.

        :param raw_challenges: Raw API data for challenges.
        :param raw_tasks: Raw API data for challenge tasks.
        :param user: User context for challenge relationships.
        :param tasks: Task context for challenge relationships.
        :returns: A populated `ChallengeCollection` instance.
        """
        collection_from_challenges = cls.from_challenges_data(
            raw_challenges,
            user,
            tasks,
        )

        dailies, habits, rewards, todos = cls._parse_tasks_list(raw_tasks)

        collection_from_challenges.challenge_tasks_daily = dailies
        collection_from_challenges.challenge_tasks_habit = habits
        collection_from_challenges.challenge_tasks_reward = rewards
        collection_from_challenges.challenge_tasks_todo = todos

        return collection_from_challenges

    @staticmethod
    def _parse_challenges_list(
        raw_challenges: list[dict],
        user: UserCollection | None,
        user_challenge_ids: set[str],
        task_challenge_ids: set[str],
    ) -> list[ChallengeInfo]:
        """Parse a list of raw challenge dictionaries into ChallengeInfo models.

        :param raw_challenges: List of raw challenge dictionaries.
        :param user: User context for challenge relationships.
        :param user_challenge_ids: Set of challenge IDs the user has joined.
        :param task_challenge_ids: Set of challenge IDs associated with user's tasks.
        :returns: A list of `ChallengeInfo` instances.
        """
        parsed_list = []
        user_id = user.profile.id if user else None

        for raw_challenge in raw_challenges:
            try:
                data = Box(raw_challenge, default_box=True, camel_killer_box=True)

                flat_data = ChallengeInfo._flatten_api_data(  # noqa: SLF001
                    data,
                    user_id,
                    user_challenge_ids,
                    task_challenge_ids,
                )

                parsed_list.append(ChallengeInfo.model_validate(flat_data))

            except (ValidationError, KeyError) as e:
                log.error(
                    "Failed to parse challenge {}: {}",
                    raw_challenge.get("id", "N/A"),
                    e,
                )

        return parsed_list

    @staticmethod
    def _parse_tasks_list(
        raw_tasks: list[dict],
    ) -> tuple[
        list[ChallengeTaskDaily],
        list[ChallengeTaskHabit],
        list[ChallengeTaskReward],
        list[ChallengeTaskTodo],
    ]:
        """Parse and categorizes a list of raw challenge task dictionaries.

        :param raw_tasks: List of raw challenge task dictionaries.
        :returns: A tuple of task lists.
        """
        collections: dict[str, list[Any]] = {
            "daily": [],
            "habit": [],
            "reward": [],
            "todo": [],
        }
        factories = {
            "daily": ChallengeTaskDaily.model_validate,
            "habit": ChallengeTaskHabit.model_validate,
            "reward": ChallengeTaskReward.model_validate,
            "todo": ChallengeTaskTodo.model_validate,
        }

        for raw_task in raw_tasks:
            try:
                task_type_str = raw_task.get("type")
                if factory := factories.get(task_type_str):  # type: ignore
                    if "challenge" in raw_task and "id" in raw_task["challenge"]:
                        raw_task["challenge_id"] = raw_task["challenge"]["id"]

                    collections[task_type_str].append(factory(raw_task))  # type: ignore

            except (ValidationError, KeyError) as e:
                log.error(
                    "Failed to parse challenge task {}: {}",
                    raw_task.get("id", "N/A"),
                    e,
                )

        return (
            collections["daily"],
            collections["habit"],
            collections["reward"],
            collections["todo"],
        )

    def get_user_challenge_ids(self) -> list[str]:
        """Get a list of challenge IDs the user has joined."""
        return [challenge.id for challenge in self.user_challenges]

    def get_task_challenge_ids(self) -> list[str]:
        """Get a list of challenge IDs associated with the user's tasks."""
        return [challenge.id for challenge in self.task_challenges]

    def add_challenge_from_dict(
        self,
        challenge_data: dict[str, Any],
        user: UserCollection | None = None,
        tasks: TaskCollection | None = None,
    ) -> bool:
        """Add a challenge from a dictionary.

        :param challenge_data: Dictionary with challenge data.
        :param user: Optional UserCollection for context.
        :param tasks: Optional TaskCollection for context.
        :returns: True if the challenge was added successfully.
        """
        try:
            user_challenge_ids = {c.id for c in self.user_challenges}
            task_challenge_ids = (
                {c.challenge_id for c in tasks.all_tasks if c.challenge_id}
                if tasks
                else set()
            )
            user_id = user.profile.id if user else None
            data = Box(challenge_data, default_box=True, camel_killer_box=True)

            flat_data = ChallengeInfo._flatten_api_data(  # noqa: SLF001
                data,
                user_id,
                user_challenge_ids,
                task_challenge_ids,
            )

            new_challenge = ChallengeInfo.model_validate(flat_data)

            if any(c.id == new_challenge.id for c in self.challenges):
                log.warning("Challenge with ID {} already exists", new_challenge.id)

                return False

            self.challenges.append(new_challenge)
            log.info("Challenge {} added successfully", new_challenge.id)

            return True

        except (ValidationError, KeyError) as e:
            log.error("Failed to add challenge from dict: {}", e)

            return False

    def remove_challenge_by_id(self, challenge_id: str) -> bool:
        """Remove a challenge by its ID.

        :param challenge_id: ID of the challenge to remove.
        :returns: True if the challenge was removed successfully.
        """
        initial_len = len(self.challenges)
        self.challenges = [c for c in self.challenges if c.id != challenge_id]
        was_removed = len(self.challenges) < initial_len

        if was_removed:
            log.info("Challenge {} removed successfully", challenge_id)
        else:
            log.warning("Challenge with ID {} not found", challenge_id)

        return was_removed

    def find_challenge_by_id(self, challenge_id: str) -> ChallengeInfo | None:
        """Find a challenge by its ID.

        :param challenge_id: ID of the challenge to find.
        :returns: The challenge if found, otherwise None.
        """
        if not challenge_id or not isinstance(challenge_id, str):
            log.error("Invalid challenge_id provided: {}", challenge_id)

            return None

        return next((c for c in self.challenges if c.id == challenge_id), None)

    def get_joined_challenges(self) -> dict[str, ChallengeInfo]:
        """Get a dictionary of all challenges the user has joined."""
        return {
            c.id: c
            for c in sorted(
                (c for c in self.challenges if c.joined),
                key=lambda c: c.created_at or datetime.datetime.min,
                reverse=True,
            )
        }

    def get_owned_challenges(self) -> dict[str, ChallengeInfo]:
        """Get a dictionary of all challenges the user owns."""
        return {
            c.id: c
            for c in sorted(
                (c for c in self.challenges if c.owned),
                key=lambda c: c.created_at or datetime.datetime.min,
                reverse=True,
            )
        }

    def get_all_challenges(self) -> dict[str, ChallengeInfo]:
        """Get a dictionary of all challenges."""
        return {
            c.id: c
            for c in sorted(
                self.challenges,
                key=lambda c: c.created_at or datetime.datetime.min,
                reverse=True,
            )
        }

    def get_legacy_challenges(self) -> dict[str, ChallengeInfo]:
        """Get a dictionary of all legacy challenges."""
        return {
            c.id: c
            for c in sorted(
                (c for c in self.challenges if c.legacy),
                key=lambda c: c.created_at or datetime.datetime.min,
                reverse=True,
            )
        }

    @property
    def all_tasks(self) -> list[Any]:
        """Return a single list containing all challenge tasks."""
        return [
            *self.challenge_tasks_todo,
            *self.challenge_tasks_daily,
            *self.challenge_tasks_habit,
            *self.challenge_tasks_reward,
        ]
