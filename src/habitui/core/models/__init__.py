# ♥♥─── HabiTui Base Model Initialization ──────────────────────────────────────
"""Initialize the base models package."""

from __future__ import annotations

from .tag_model import TagComplex, TagCollection
from .base_enums import Priority, TaskType, Attribute, Frequency, TagsTrait, TaskStatus, TodoStatus, DailyStatus, HabitStatus, RewardStatus, TagsCategory, ScoreDirection, TaskKeepOption, ChallengeTaskKeepOption
from .base_model import ContentMetadata, HabiTuiSQLModel, HabiTuiBaseModel
from .task_model import AnyTask, TaskTodo, TaskDaily, TaskHabit, TaskReward, TaskChecklist, TaskCollection, TaskStatusType, ChallengeInTask
from .user_model import UserHistory, UserProfile, UserStatsRaw, UserCollection, UserTasksOrder, UserTimestamps, ChallengeInUser, UserPreferences, UserAchievements, UserCurrentState, UserNotifications, UserStatsComputed
from .party_model import PartyInfo, PartyCollection
from .content_model import GearItem, QuestItem, SpellItem, ContentCollection
from .message_model import UserMessage, PartyMessage
from .creation_model import TodoCreate, DailyCreate, HabitCreate, RewardCreate, ReminderCreate, TaskBaseCreate, ChallengeCreate, TaskCreatePayload, DailyRepeatPattern, ChecklistItemCreate
from .challenge_model import ChallengeInfo, ChallengeTaskTodo, ChallengeTaskDaily, ChallengeTaskHabit, ChallengeCollection, ChallengeTaskReward


__all__ = [
    "AnyTask",
    "Attribute",
    "Attribute",
    "ChallengeCollection",
    "ChallengeCreate",
    "ChallengeInTask",
    "ChallengeInUser",
    "ChallengeInfo",
    "ChallengeTaskDaily",
    "ChallengeTaskHabit",
    "ChallengeTaskKeepOption",
    "ChallengeTaskKeepOption",
    "ChallengeTaskReward",
    "ChallengeTaskTodo",
    "ChecklistItemCreate",
    "ContentCollection",
    "ContentMetadata",
    "ContentMetadata",
    "DailyCreate",
    "DailyRepeatPattern",
    "DailyStatus",
    "DailyStatus",
    "Frequency",
    "Frequency",
    "GearItem",
    "HabiTuiBaseModel",
    "HabiTuiBaseModel",
    "HabiTuiSQLModel",
    "HabiTuiSQLModel",
    "HabitCreate",
    "HabitStatus",
    "HabitStatus",
    "PartyCollection",
    "PartyInfo",
    "PartyMessage",
    "Priority",
    "Priority",
    "QuestItem",
    "ReminderCreate",
    "RewardCreate",
    "RewardStatus",
    "RewardStatus",
    "ScoreDirection",
    "ScoreDirection",
    "SpellItem",
    "TagCollection",
    "TagComplex",
    "TagsCategory",
    "TagsCategory",
    "TagsTrait",
    "TaskBaseCreate",
    "TaskChecklist",
    "TaskCollection",
    "TaskCreatePayload",
    "TaskDaily",
    "TaskHabit",
    "TaskKeepOption",
    "TaskKeepOption",
    "TaskReward",
    "TaskStatus",
    "TaskStatus",
    "TaskStatusType",
    "TaskTodo",
    "TaskType",
    "TaskType",
    "TodoCreate",
    "TodoStatus",
    "TodoStatus",
    "UserAchievements",
    "UserCollection",
    "UserCurrentState",
    "UserHistory",
    "UserMessage",
    "UserNotifications",
    "UserPreferences",
    "UserProfile",
    "UserStatsComputed",
    "UserStatsRaw",
    "UserTasksOrder",
    "UserTimestamps",
]
