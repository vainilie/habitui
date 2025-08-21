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
    """Abstract base model for all challenge task types.

    :param challenge_id: The ID of the challenge this task belongs to.
    :param type: The type of task (e.g., habit, daily).
    :param text: The text/description of the task.
    :param notes: Additional notes for the task.
    :param value: The task's value.
    :param priority: The task's priority.
    :param attribute: The character attribute associated with the task.
    :param by_habitica: True if the task was created by Habitica.
    :param created_at: Timestamp when the task was created.
    :param updated_at: Timestamp when the task was last updated.
    :param challenge: Dictionary containing challenge-specific metadata.
    :param group: Dictionary containing group-specific metadata.
    :param reminders: List of reminder objects for the task.
    """

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
        """Clean text fields by replacing emoji shortcodes.

        :param v: The input text.
        :returns: The cleaned string.
        """
        return validators.replace_emoji_shortcodes(v)

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _parse_dates(cls, v: Any) -> datetime.datetime | None:
        """Parse date strings into timezone-aware datetime objects.

        :param v: The date string.
        :returns: A datetime object, or None.
        """
        return validators.parse_datetime(v)

    @field_validator("attribute", mode="before")
    @classmethod
    def _normalize_attr(cls, v: Any) -> str | None:
        """Normalize attribute names.

        :param v: The attribute value.
        :returns: The normalized attribute name, or None.
        """
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
        """Clean text fields by replacing emoji shortcodes.

        :param v: The input text.
        :returns: The cleaned string.
        """
        return validators.replace_emoji_shortcodes(v)

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _parse_dates(cls, v: Any) -> datetime.datetime | None:
        """Parse date strings into timezone-aware datetime objects.

        :param v: The date string.
        :returns: A datetime object, or None.
        """
        return validators.parse_datetime(v)

    @classmethod
    def _flatten_api_data(
        cls,
        data: Box,
        user_id: str | None = None,
        user_challenge_ids: set[str] | None = None,
        task_challenge_ids: set[str] | None = None,
    ) -> dict[str, Any]:
        """Flatten Box API data into a dictionary suitable for model validation.

        :param data: The raw API data as a Box object.
        :param user_id: The ID of the current user.
        :param user_challenge_ids: Set of challenge IDs the user has joined.
        :param task_challenge_ids: Set of challenge IDs associated with user's tasks.
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
        """Create a ChallengeInfo instance from API data, including relationship status.

        :param data: The raw API data for the challenge as a Box object.
        :param user_context: The user's collection for contextual information.
        :param task_challenge_ids: Set of challenge IDs associated with user's tasks.
        :returns: A `ChallengeInfo` instance.
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


# --- Concrete Challenge Task Models ---


class ChallengeTaskReward(ChallengeTaskBase, table=True):
    """Represent a reward task within a challenge.

    Inherits from `ChallengeTaskBase`.
    """

    __tablename__ = "challenge_task_reward"  # type: ignore
    type: TaskType = TaskType.REWARD


class ChallengeTaskHabit(ChallengeTaskBase, table=True):
    """Represent a habit task within a challenge.

    :param up: True if the habit has an 'up' (positive) component.
    :param down: True if the habit has a 'down' (negative) component.
    :param counter_up: Counter for positive clicks.
    :param counter_down: Counter for negative clicks.
    :param frequency: Frequency of the habit.
    """

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
    """Represent a To-Do task within a challenge.

    :param date: The due date of the todo.
    :param checklist: List of checklist items.
    """

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
        """Parse the due date string into a datetime object.

        :param v: The due date string.
        :returns: A datetime object, or None.
        """
        return validators.parse_datetime(v)


class ChallengeTaskDaily(ChallengeTaskBase, table=True):
    """Represent a daily task within a challenge.

    :param frequency: Frequency of the daily.
    :param every_x: Repeats every X days/weeks/months/years.
    :param start_date: Start date for the daily.
    :param streak: Current streak for the daily.
    :param is_due: True if the daily is due.
    :param yester_daily: True if the daily was due yesterday and missed.
    :param checklist: List of checklist items.
    :param repeat: Dictionary of days of the week to repeat.
    :param days_of_month: Specific days of the month to repeat.
    :param weeks_of_month: Specific weeks of the month to repeat.
    :param next_due: List of next due dates.
    """

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
        """Parse the start date string into a datetime object.

        :param v: The start date string.
        :returns: A datetime object, or None.
        """
        return validators.parse_datetime(v)

    @field_validator("next_due", mode="before")
    @classmethod
    def _parse_next_due_dates(cls, value: Any) -> list[datetime.datetime | None]:
        """Parse a list of next due date strings into datetime objects.

        :param value: A list of next due date strings.
        :returns: A list of datetime objects, with None for unparseable entries.
        """
        if not value:
            return []
        if isinstance(value, list):
            return [
                validators.parse_datetime(date_str)
                for date_str in value
                if date_str is not None
            ]
        return []


# --- Collection Orchestrator ---


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

        This method acts as a dispatcher to the appropriate specialized constructor.

        :param challenges_data: Raw API data for challenges.
        :param challenge_tasks_data: Raw API data for challenge tasks.
        :param user: User context for challenge relationships.
        :param tasks: Task context for challenge relationships.
        :returns: A populated `ChallengeCollection` instance.
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
        """Get list of user challenge IDs for validation purposes.

        :returns: A list of user challenge IDs.
        """
        return [challenge.id for challenge in self.user_challenges]

    def get_task_challenge_ids(self) -> list[str]:
        """Get list of task challenge IDs for validation purposes.

        :returns: A list of task challenge IDs.
        """
        return [challenge.id for challenge in self.task_challenges]

    def add_challenge_from_dict(
        self,
        challenge_data: dict[str, Any],
        user: UserCollection | None = None,
        tasks: TaskCollection | None = None,
    ) -> bool:
        """Add a challenge from a dictionary.

        :param challenge_data: Dictionary with challenge data.
        :param user: Optional UserCollection for user ID and validating user challenges.
        :returns: True if the challenge was added successfully, False otherwise.
        """
        try:
            # Get existing challenge IDs for validation
            user_challenge_ids = {c.id for c in self.user_challenges}
            task_challenge_ids = (
                {c.challenge_id for c in tasks.all_tasks if c.challenge_id}
                if tasks
                else set()
            )

            # Get user_id
            user_id = user.profile.id if user else None

            # Process data using Box for normalization
            data = Box(challenge_data, default_box=True, camel_killer_box=True)

            # Flatten data using the existing method
            flat_data = ChallengeInfo._flatten_api_data(  # noqa: SLF001
                data,
                user_id,
                user_challenge_ids,
                task_challenge_ids,
            )

            # Validate and create the challenge
            new_challenge = ChallengeInfo.model_validate(flat_data)

            # Check if the challenge already exists
            if any(challenge.id == new_challenge.id for challenge in self.challenges):
                log.warning("Challenge with ID {} already exists", new_challenge.id)
                return False

            # Add the challenge to the collection
            self.challenges.append(new_challenge)

            log.info("Challenge {} added successfully", new_challenge.id)

        except (ValidationError, KeyError) as e:
            log.error("Failed to add challenge from dict: {}", e)
            return False
        else:
            return True

    def remove_challenge_by_id(self, challenge_id: str) -> bool:
        """Remove a challenge by its ID.

        :param challenge_id: ID of the challenge to remove.
        :returns: True if the challenge was removed successfully, False if not found.
        """
        try:
            # Find the challenge by ID
            challenge_to_remove = None
            for i, challenge in enumerate(self.challenges):
                if challenge.id == challenge_id:
                    challenge_to_remove = self.challenges.pop(i)
                    break

            if challenge_to_remove:
                log.info("Challenge {} removed successfully", challenge_id)
                return True
            log.warning("Challenge with ID {} not found", challenge_id)

        except Exception as e:
            log.error("Failed to remove challenge {}: {}", challenge_id, e)
            return False
        else:
            return False

    def get_challenge_by_id(self, challenge_id: str) -> ChallengeInfo | None:
        """Get a challenge by its ID.

        :param challenge_id: ID of the challenge to find.
        :returns: The challenge if found, None if it does not exist.
        """
        try:
            for challenge in self.challenges:
                if challenge.id == challenge_id:
                    return challenge

            log.debug("Challenge with ID {} not found", challenge_id)

        except Exception as e:
            log.error("Failed to get challenge {}: {}", challenge_id, e)
            return None
        else:
            return None

    def find_challenge_by_id(self, challenge_id: str) -> ChallengeInfo | None:
        """Find a challenge by its ID using next() for efficiency.

        :param challenge_id: ID of the challenge to find.
        :returns: The challenge if found, None if it does not exist.
        """
        try:
            return next((c for c in self.challenges if c.id == challenge_id), None)

        except Exception as e:
            log.error("Failed to find challenge {}: {}", challenge_id, e)
            return None

    def get_challenge_by_id_with_validation(
        self,
        challenge_id: str,
        raise_if_not_found: bool = False,
    ) -> ChallengeInfo | None:
        """Get a challenge by its ID with additional validation.

        :param challenge_id: ID of the challenge to find.
        :param raise_if_not_found: If True, raises an exception if not found.
        :returns: The challenge if found, None if it does not exist.
        :raises ValueError: If raise_if_not_found=True and the challenge does not exist or invalid ID.
        """
        if not challenge_id or not isinstance(challenge_id, str):
            log.error("Invalid challenge_id provided: {}", challenge_id)
            if raise_if_not_found:
                msg = f"Invalid challenge_id: {challenge_id}"
                raise ValueError(msg)
            return None

        try:
            challenge = next((c for c in self.challenges if c.id == challenge_id), None)

            if challenge is None and raise_if_not_found:
                msg = f"Challenge with ID '{challenge_id}' not found"
                raise ValueError(msg)

        except ValueError:
            raise  # Re-raise ValueError
        except Exception as e:
            log.error("Failed to get challenge {}: {}", challenge_id, e)
            if raise_if_not_found:
                raise
            return None
        else:
            return challenge

    def remove_challenge_by_id_efficient(self, challenge_id: str) -> bool:
        """Remove a challenge by its ID efficiently.

        :param challenge_id: ID of the challenge to remove.
        :returns: True if the challenge was removed successfully, False if not found.
        """
        try:
            original_length = len(self.challenges)
            self.challenges = [c for c in self.challenges if c.id != challenge_id]

            if len(self.challenges) < original_length:
                log.info("Challenge {} removed successfully", challenge_id)
                return True
            log.warning("Challenge with ID {} not found", challenge_id)

        except Exception as e:
            log.error("Failed to remove challenge {}: {}", challenge_id, e)
            return False
        else:
            return False

    def get_joined_challenges(self) -> dict[str, ChallengeInfo]:
        joined = {}
        for challenge in self.challenges:
            if challenge.joined:
                joined[challenge.id] = challenge
        return joined

    def get_owned_challenges(self) -> dict[str, ChallengeInfo]:
        owned = {}
        for challenge in self.challenges:
            if challenge.owned:
                owned[challenge.id] = challenge
        return owned

    def get_all_challenges(self) -> dict[str, ChallengeInfo]:
        all_challenges = {}
        for challenge in self.challenges:
            all_challenges[challenge.id] = challenge
        return all_challenges

    def get_legacy_challenges(self) -> dict[str, ChallengeInfo]:
        legacy = {}
        for challenge in self.challenges:
            if challenge.legacy:
                legacy[challenge.id] = challenge
        return legacy

    @property
    def all_tasks(self) -> list[Any]:
        """Return a single list containing all primary tasks."""
        return [
            *self.challenge_tasks_todo,
            *self.challenge_tasks_daily,
            *self.challenge_tasks_habit,
            *self.challenge_tasks_reward,
        ]
