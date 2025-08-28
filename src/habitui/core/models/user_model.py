# ♥♥─── HabiTui User Models ────────────────────────────────────────────────────
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self
import datetime

from box import Box
from humps import decamelize
from pydantic import field_validator
from sqlmodel import Field, Column

from habitui.ui import icons
from habitui.utils import DateTimeHandler
from habitui.custom_logger import log

from .tag_model import TagComplex
from .base_model import HabiTuiSQLModel, HabiTuiBaseModel
from .validators import PydanticJSON, parse_datetime
from .message_model import UserMessage


if TYPE_CHECKING:
    from .content_model import QuestItem, SpellItem, ContentCollection


# ─── Challenge In User ────────────────────────────────────────────────────────
class ChallengeInUser(HabiTuiSQLModel, table=True):
    """Represent a challenge a user is participating in.

    :param id: The ID of the challenge.
    """

    __tablename__ = "challenge_in_user"  # type: ignore

    @classmethod
    def from_api_id(cls, challenge_id: str) -> Self:
        """Create an instance from a challenge ID string.

        :param challenge_id: The ID of the challenge.
        :returns: A `ChallengeInUser` instance.
        """
        return cls(id=challenge_id)


# ─── User Profile ─────────────────────────────────────────────────────────────
class UserProfile(HabiTuiSQLModel, table=True):
    """Core user profile information.

    :param username: The user's username.
    :param name: The user's display name.
    :param blurb: The user's blurb/motto.
    :param party_id: The ID of the user's current party.
    """

    __tablename__ = "user_profile"  # type: ignore
    username: str
    name: str | None = None
    blurb: str | None = None
    party_id: str | None = None

    @classmethod
    def from_api_box(cls, data: Box) -> Self:
        """Create an instance from the main API data box.

        :param data: The raw API user data as a Box object.
        :returns: A `UserProfile` instance.
        """
        return cls(id=data.id, username=data.auth.local.username, name=data.profile.name, blurb=data.profile.blurb, party_id=data.party.get("_id"))


# ─── User Stats Raw ───────────────────────────────────────────────────────────
class UserStatsRaw(HabiTuiSQLModel, table=True):
    """Raw stats directly from the Habitica API.

    :param level: Current experience level.
    :param class_name: Character class.
    :param hp: Current health points.
    :param mp: Current mana points.
    :param exp: Current experience.
    :param gp: Current gold.
    :param balance: Account balance.
    :param gems: Number of gems.
    :param base_max_hp: Base maximum HP.
    :param base_max_mp: Base maximum MP.
    :param to_next_level: Experience needed to next level.
    :param buffs: dictionary of active buffs.
    :param equipped_gear: List of equipped gear IDs.
    """

    __tablename__ = "user_stats_raw"  # type: ignore
    level: int = Field(alias="lvl")
    class_name: str = Field(alias="klass", default="warrior")
    hp: float = 0.0
    mp: float = 0.0
    exp: float = 0.0
    gp: float = 0.0
    balance: float = 1.0
    gems: int = 0
    base_max_hp: int = 50
    base_max_mp: int = 0
    to_next_level: int = 0
    buffs: dict[str, Any] = Field(default_factory=dict, sa_column=Column(PydanticJSON))
    equipped_gear: list[str] = Field(default_factory=list, sa_column=Column(PydanticJSON))

    @classmethod
    def from_api_box(cls, data: Box) -> Self:
        """Create an instance from the main API data box.

        :param data: The raw API user data as a Box object.
        :returns: A `UserStatsRaw` instance.
        """
        stats = data.stats
        balance = data.balance
        return cls(
            id=data.id,
            lvl=stats.lvl,
            klass=stats.get("class", "warrior"),
            hp=stats.hp,
            mp=stats.mp,
            exp=stats.exp,
            gp=stats.gp,
            base_max_hp=stats.max_health,
            base_max_mp=stats.max_mp,
            to_next_level=stats.to_next_level,
            buffs=stats.buffs,
            equipped_gear=[decamelize(gear) for gear in data["items"].gear.get("equipped", {}).values()],
            balance=balance,
            gems=(balance * 4) if balance is not None else 0,
        )


# ─── User Current State ───────────────────────────────────────────────────────
class UserCurrentState(HabiTuiSQLModel, table=True):
    """Current game state and progress for the user.

    :param sleep_mode: True if user is in sleep mode.
    :param needs_cron: True if user needs cron to run.
    :param strength: User's raw strength stat.
    :param constitution: User's raw constitution stat.
    :param intelligence: User's raw intelligence stat.
    :param perception: User's raw perception stat.
    :param current_quest_key: Key of the current active quest.
    :param current_quest_active: True if current quest is active.
    :param current_quest_progress: Progress details of the current quest.
    :param current_quest_completed: Status of current quest completion.
    :param training: User's training status.
    """

    __tablename__ = "user_current_state"  # type: ignore
    sleep_mode: bool = False
    needs_cron: bool = False
    strength: float = Field(alias="str", default=0.0)
    constitution: float = Field(alias="con", default=0.0)
    intelligence: float = Field(alias="int", default=0.0)
    perception: float = Field(alias="per", default=0.0)
    current_quest_key: str | None = None
    current_quest_active: bool = Field(default=False)
    current_quest_progress: dict[str, Any] | None = Field(default=None, sa_column=Column(PydanticJSON))
    current_quest_completed: str | None = None
    training: dict[str, Any] | None = Field(default=None, sa_column=Column(PydanticJSON))

    @classmethod
    def from_api_box(cls, data: Box) -> Self:
        """Create an instance from the main API data box.

        :param data: The raw API user data as a Box object.
        :returns: A `UserCurrentState` instance.
        """
        stats = data.stats
        quest = data.party.quest
        return cls(
            id=data.id,
            sleep_mode=data.preferences.sleep,
            needs_cron=data.needs_cron,
            current_quest_key=quest.key or None,
            current_quest_active=quest.active or False,
            current_quest_progress=quest.progress or None,
            current_quest_completed=quest.completed or None,
            training=data.stats.training,
            str=stats.get("str", 0.0),
            con=stats.con,
            int=stats.get("int", 0.0),
            per=stats.per,
        )


# ─── User History ─────────────────────────────────────────────────────────────
class UserHistory(HabiTuiSQLModel, table=True):
    """Historical data for user experience and todos.

    :param exp: List of experience history entries.
    :param todos: List of todo history entries.
    """

    __tablename__ = "user_history"  # type: ignore
    exp: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(PydanticJSON))
    todos: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(PydanticJSON))

    @classmethod
    def from_api_box(cls, data: Box) -> Self:
        """Create an instance from the history sub-object.

        :param data: The raw API user data as a Box object.
        :returns: A `UserHistory` instance.
        """
        history_data = data.history.to_dict() if data.history else {}
        return cls(id=data.id, **history_data)


# ─── User Tasks Order ─────────────────────────────────────────────────────────
class UserTasksOrder(HabiTuiSQLModel, table=True):
    """Custom sort order for user's tasks.

    :param habits: List of habit IDs in custom order.
    :param dailys: List of daily IDs in custom order.
    :param todos: List of todo IDs in custom order.
    :param rewards: List of reward IDs in custom order.
    """

    __tablename__ = "user_tasks_order"  # type: ignore
    habits: list[str] = Field(default_factory=list, sa_column=Column(PydanticJSON))
    dailys: list[str] = Field(default_factory=list, sa_column=Column(PydanticJSON))
    todos: list[str] = Field(default_factory=list, sa_column=Column(PydanticJSON))
    rewards: list[str] = Field(default_factory=list, sa_column=Column(PydanticJSON))

    @classmethod
    def from_api_box(cls, data: Box) -> Self:
        """Create an instance from the tasksOrder sub-object.

        :param data: The raw API user data as a Box object.
        :returns: A `UserTasksOrder` instance.
        """
        tasks_data = data.tasks_order.to_dict() if data.tasks_order else {}
        return cls(id=data.id, **tasks_data)


# ─── User Preferences ─────────────────────────────────────────────────────────
class UserPreferences(HabiTuiSQLModel, table=True):
    """User-specific preferences and settings.

    :param day_start: Hour of day when tasks reset.
    :param timezone_offset: Timezone offset in minutes.
    :param timezone_offset_at_last_cron: Timezone offset at last cron run.
    :param sleep: True if user is in sleep mode.
    """

    __tablename__ = "user_preferences"  # type: ignore
    day_start: int = Field(default=0, ge=0, le=23)
    timezone_offset: int | None = None
    timezone_offset_at_last_cron: int | None = None
    sleep: bool = False

    @classmethod
    def from_api_box(cls, data: Box) -> Self:
        """Create an instance from the preferences sub-object.

        :param data: The raw API user data as a Box object.
        :returns: A `UserPreferences` instance.
        """
        prefs_data = data.preferences.to_dict() if data.preferences else {}
        return cls(id=data.id, **prefs_data)


# ─── User Achievements ────────────────────────────────────────────────────────
class UserAchievements(HabiTuiSQLModel, table=True):
    """User's achievements and streaks.

    :param login_incentives: Number of login incentives.
    :param perfect: Number of perfect days.
    :param streak: Current daily streak.
    :param challenges: List of challenge IDs achieved.
    :param quests: dictionary of quest achievements.
    """

    __tablename__ = "user_achievements"  # type: ignore
    login_incentives: int = 0
    perfect: int = 0
    streak: int = 0
    challenges: list[str] = Field(default_factory=list, sa_column=Column(PydanticJSON))
    quests: dict[str, int] = Field(default_factory=dict, sa_column=Column(PydanticJSON))

    @classmethod
    def from_api_box(cls, data: Box) -> Self:
        """Create an instance from the achievements sub-object.

        :param data: The raw API user data as a Box object.
        :returns: A `UserAchievements` instance.
        """
        ach_data = data.achievements.to_dict() if data.achievements else {}
        ach_data["login_incentives"] = data.login_incentives
        return cls(id=data.id, **ach_data)


# ─── User Notifications ───────────────────────────────────────────────────────
class UserNotifications(HabiTuiSQLModel, table=True):
    """User notifications and inbox status.

    :param inbox_new_message_count: Number of new messages in inbox.
    :param new_messages: dictionary of new messages.
    :param notifications: List of notifications.
    :param current_quest_rsvp_needed: True if RSVP is needed for current quest.
    :param current_quest_completed_trigger: Quest completed trigger status.
    """

    __tablename__ = "user_notifications"  # type: ignore
    inbox_new_message_count: int = 0
    new_messages: dict[str, Any] = Field(default_factory=dict, sa_column=Column(PydanticJSON))
    notifications: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(PydanticJSON))
    current_quest_rsvp_needed: bool = False
    current_quest_completed_trigger: str | None = None

    @classmethod
    def from_api_box(cls, data: Box) -> Self:
        """Create an instance from various notification-related fields.

        :param data: The raw API user data as a Box object.
        :returns: A `UserNotifications` instance.
        """
        return cls(id=data.id, inbox_new_message_count=data.inbox.new_messages, new_messages=data.new_messages, notifications=data.notifications, current_quest_rsvp_needed=data.party.quest.rsvp_needed, current_quest_completed_trigger=data.party.quest.completed or None)


# ─── User Timestamps ──────────────────────────────────────────────────────────
class UserTimestamps(HabiTuiSQLModel, table=True):
    """Important user-related timestamps.

    :param account_created_at: Timestamp of account creation.
    :param last_login_at: Timestamp of last login.
    :param account_updated_at: Timestamp of last account update.
    """

    __tablename__ = "user_timestamps"  # type: ignore
    account_created_at: datetime.datetime | None = None
    last_login_at: datetime.datetime | None = None
    account_updated_at: datetime.datetime | None = None

    @field_validator("last_login_at", "account_updated_at", "account_updated_at", mode="before")
    @classmethod
    def _parse_start_date(cls, v: Any) -> datetime.datetime | None:
        """Parse the start date string into a datetime object.

        :param v: The start date string.
        :returns: A datetime object, or None.
        """
        return parse_datetime(v)

    @classmethod
    def from_api_box(cls, data: Box) -> Self:
        """Create an instance from the auth.timestamps sub-object.

        :param data: The raw API user data as a Box object.
        :returns: A `UserTimestamps` instance.
        """
        timestamps = data.auth.timestamps
        return cls(id=data.id, account_created_at=timestamps.created, last_login_at=timestamps.logged_in, account_updated_at=timestamps.updated)


# ─── User Stats Computed ──────────────────────────────────────────────────────
class UserStatsComputed(HabiTuiSQLModel, table=True):
    """Calculated stats based on raw stats, gear, and buffs.

    :param effective_strength: Calculated effective strength.
    :param effective_constitution: Calculated effective constitution.
    :param effective_intelligence: Calculated effective intelligence.
    :param effective_perception: Calculated effective perception.
    :param effective_max_mp: Calculated effective maximum MP.
    :param stealth: User's stealth value.
    :param boss_str: Boss strength if user is on a boss quest.
    """

    __tablename__ = "user_stats_computed"  # type: ignore
    effective_strength: float = 0.0
    effective_constitution: float = 0.0
    effective_intelligence: float = 0.0
    effective_perception: float = 0.0
    effective_max_mp: float = 0.0
    stealth: float = 0.0
    boss_str: float = 0.0
    gear_bonus_int: float = 0.0
    gear_bonus_str: float = 0.0
    gear_bonus_con: float = 0.0
    gear_bonus_per: float = 0.0

    @classmethod
    def from_dependencies(cls, user_id: str, raw_stats: UserStatsRaw, user_state: UserCurrentState, content_vault: ContentCollection) -> Self:
        """Calculate all effective stats and returns an instance.

        :param user_id: The user's ID.
        :param raw_stats: User's raw stats.
        :param user_state: User's current game state.
        :param content_vault: Access to game content data.
        :returns: A `UserStatsComputed` instance.
        """
        level_bonus = round(min(50.0, raw_stats.level / 2), 0)
        gear_bonuses = {"strength": 0.0, "constitution": 0.0, "intelligence": 0.0, "perception": 0.0}
        for key in raw_stats.equipped_gear:
            if gear := content_vault.get_gear(key):
                multiplier = 1.5 if gear.special_class == raw_stats.class_name else 1.0
                for stat in gear_bonuses:
                    gear_bonuses[stat] += getattr(gear, stat, 0.0) * multiplier
        eff_str = user_state.strength + raw_stats.buffs.get("str", 0) + gear_bonuses["strength"] + level_bonus
        eff_con = user_state.constitution + raw_stats.buffs.get("con", 0) + gear_bonuses["constitution"] + level_bonus
        eff_int = user_state.intelligence + raw_stats.buffs.get("int", 0) + gear_bonuses["intelligence"] + level_bonus
        eff_per = user_state.perception + raw_stats.buffs.get("per", 0) + gear_bonuses["perception"] + level_bonus
        boss_str = 0.0
        if (quest_key := user_state.current_quest_key) and (quest := content_vault.get_quest(decamelize(quest_key))) and quest.is_boss_quest and quest.boss_str is not None:
            boss_str = quest.boss_str
        return cls(
            id=user_id,
            effective_strength=eff_str,
            effective_constitution=eff_con,
            effective_intelligence=eff_int,
            effective_perception=eff_per,
            effective_max_mp=(eff_int * 2 + 30),
            stealth=raw_stats.buffs.get("stealth", 0),
            boss_str=boss_str,
            gear_bonus_str=gear_bonuses["strength"],
            gear_bonus_int=gear_bonuses["intelligence"],
            gear_bonus_con=gear_bonuses["constitution"],
            gear_bonus_per=gear_bonuses["perception"],
        )


# ─── User Collection ──────────────────────────────────────────────────────────
def format_date(date_obj: datetime.datetime) -> str:
    if hasattr(date_obj, "strftime"):
        return DateTimeHandler(timestamp=date_obj).format_local(fmt="%MM,%Y")
    return str(date_obj) if date_obj else "N/A"


def get_class_icon(obj: str) -> str:
    """Get class information with icon."""
    class_icons = {"wizard": icons.WIZARD, "mage": icons.WIZARD, "healer": icons.HEALER, "warrior": icons.WARRIOR, "rogue": icons.ROGUE, "no class": icons.USER}
    return class_icons.get(obj.lower(), icons.USER)


class UserCollection(HabiTuiBaseModel):
    """Complete collection of all parsed user data.

    :param profile: User profile information.
    :param raw_stats: Raw user statistics.
    :param user_state: Current game state.
    :param computed_stats: Computed user statistics.
    :param preferences: User preferences.
    :param history: User history data.
    :param tasks_order: Custom task order.
    :param achievements: User achievements.
    :param notifications: User notifications.
    :param timestamps: Important user-related timestamps.
    :param simple_tags: List of user's simple tags.
    :param inbox: List of user's inbox messages.
    :param challenges: List of challenges user is participating in.
    """

    profile: UserProfile
    raw_stats: UserStatsRaw
    user_state: UserCurrentState
    computed_stats: UserStatsComputed
    preferences: UserPreferences
    history: UserHistory
    tasks_order: UserTasksOrder
    achievements: UserAchievements
    notifications: UserNotifications
    timestamps: UserTimestamps
    simple_tags: list[TagComplex]
    inbox: list[UserMessage]
    challenges: list[ChallengeInUser]

    @classmethod
    def from_api_data(cls, raw_data: dict[str, Any], content_vault: ContentCollection) -> Self:
        """Parse raw API data into a structured UserCollection instance.

        :param raw_data: The raw API response for the user profile.
        :param content_vault: Access to game content data for stat calculations.
        :returns: A populated UserCollection instance.
        """
        data = Box(raw_data, default_box=True, camel_killer_box=True)
        profile = UserProfile.from_api_box(data)
        raw_stats = UserStatsRaw.from_api_box(data)
        user_state = UserCurrentState.from_api_box(data)
        preferences = UserPreferences.from_api_box(data)
        history = UserHistory.from_api_box(data)
        tasks_order = UserTasksOrder.from_api_box(data)
        achievements = UserAchievements.from_api_box(data)
        notifications = UserNotifications.from_api_box(data)
        timestamps = UserTimestamps.from_api_box(data)
        tags = [TagComplex.model_validate({**tag.to_dict(), "position": i}) for i, tag in enumerate(data.tags or [])]
        challenges = [ChallengeInUser.from_api_id(cid) for cid in data.challenges or []]
        inbox_msgs = (data.inbox.messages or {}).values()
        inbox = [UserMessage.from_api_dict(msg, i) for i, msg in enumerate(inbox_msgs)]
        computed_stats = UserStatsComputed.from_dependencies(user_id=data.id, raw_stats=raw_stats, user_state=user_state, content_vault=content_vault)
        return cls(profile=profile, raw_stats=raw_stats, user_state=user_state, computed_stats=computed_stats, preferences=preferences, history=history, tasks_order=tasks_order, achievements=achievements, notifications=notifications, timestamps=timestamps, simple_tags=tags, inbox=inbox, challenges=challenges)

    def get_current_quest_data(self, content_vault: ContentCollection) -> QuestItem | None:
        """Get current quest data from game content."""
        if self.user_state.current_quest_key:
            log.info(content_vault.get_quest(key=decamelize(self.user_state.current_quest_key)))
            return content_vault.get_quest(key=decamelize(self.user_state.current_quest_key))
        return None

    def available_spells(self, content_vault: ContentCollection) -> dict[str, SpellItem | float]:
        """Get current quest data from game content."""
        spells_info = {"affordable": [], "non_affordable": [], "current_mana": self.raw_stats.mp}
        spells = content_vault.get_spells_by_class(character_class=self.raw_stats.class_name)
        for spell in spells:
            if self.raw_stats.mp >= spell.mana:
                spells_info["affordable"].append(spell)
            else:
                spells_info["non_affordable"].append(spell)
        return spells_info

    # ──────────────────────────────────────────────────────────────────────────────
    def get_effective_strength(self) -> float:
        """Get effective strength.

        :returns: The user's effective strength.
        """
        return self.computed_stats.effective_strength

    def get_effective_constitution(self) -> float:
        """Get effective constitution.

        :returns: The user's effective constitution.
        """
        return self.computed_stats.effective_constitution

    def get_stealth(self) -> float:
        """Get stealth value.

        :returns: The user's stealth value.
        """
        return self.computed_stats.stealth

    def is_sleeping(self) -> bool:
        """Check if user is in sleep mode.

        :returns: True if the user is in sleep mode, False otherwise.
        """
        return self.user_state.sleep_mode

    def get_tag_by_id(self, tag_id: str) -> TagComplex | None:
        """Get a specific tag by its ID.

        :param tag_id: The ID of the tag.
        :returns: The `TagComplex` instance, or None if not found.
        """
        return next((tag for tag in self.simple_tags if tag.id == tag_id), None)

    def get_inbox_by_senders(self) -> dict[str, dict[Any, Any]]:
        senders: dict[str, dict] = {}
        for msg in self.inbox:
            sender = msg.uuid
            if sender not in senders:
                sender_name = msg.user if not msg.by_me else None
                sender_username = msg.username if not msg.by_me else None
                senders[sender] = {"uuid": msg.uuid, "sender_name": sender_name, "sender_username": sender_username, "last_time": msg.timestamp, "last_by_me": msg.by_me, "messages": []}
            senders[sender]["messages"].append(msg)
            if not msg.by_me and not senders[sender]["sender_name"]:
                senders[sender]["sender_name"] = msg.user
                senders[sender]["sender_username"] = msg.username
        return senders

    def get_display_data(self) -> dict[str, Any]:
        quest_name = ""
        current_quest_key = ""
        if self.user_state.current_quest_key:
            current_quest_key = self.user_state.current_quest_key
            quest_name = f"{current_quest_key.capitalize()}"  # type: ignore
        status_parts = []
        if self.user_state.current_quest_completed:
            status_parts.append(icons.CHECK)
        if self.notifications.current_quest_completed_trigger:
            status_parts.append("(Get rewards!)")
        status_suffix = " " + " ".join(status_parts) if status_parts else ""
        display_text = f"{icons.QUEST} {quest_name}{status_suffix}"
        return {
            "display_name": self.profile.name or "Unknown User",
            "class_name": self.raw_stats.class_name or "no class",
            "klass_icon": get_class_icon(self.raw_stats.class_name.lower()),
            "sleep": "Resting" if self.is_sleeping() else "Awake",
            "day_start": self.preferences.day_start,
            "needs_cron": self.user_state.needs_cron,
            "hp": {"current": int(self.raw_stats.hp), "max": int(self.raw_stats.base_max_hp)},
            "xp": {"current": int(self.raw_stats.exp), "max": self.raw_stats.to_next_level},
            "mp": {"current": int(self.raw_stats.mp), "max": int(self.computed_stats.effective_max_mp)},
            "level": self.raw_stats.level,
            "gold": int(self.raw_stats.gp),
            "gems": int(self.raw_stats.gems or 0),
            "intelligence": int(self.computed_stats.effective_intelligence),
            "perception": int(self.computed_stats.effective_perception),
            "strength": int(self.computed_stats.effective_strength),
            "constitution": int(self.computed_stats.effective_constitution),
            "account_created": format_date(self.timestamps.account_created_at) if self.timestamps.account_created_at else "Unknown",
            "login_days": self.achievements.login_incentives,
            "perfect_days": self.achievements.perfect,
            "streak_count": self.achievements.streak,
            "challenges_won": len(self.achievements.challenges or []),
            "quests_completed": len(self.achievements.quests or []),
            "username": self.profile.username or "Unknown",
            "bio": self.profile.blurb or "No biography available.",
            "has_quest": bool(current_quest_key),
            "quest_name": "No active quest" if not current_quest_key else quest_name,
            "quest_display_text": "No active quest" if not current_quest_key else display_text,
            "quest_completed": False if not current_quest_key else self.user_state.current_quest_completed,
            "rsvp": self.notifications.current_quest_rsvp_needed,
        }
