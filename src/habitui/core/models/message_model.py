# ♥♥─── HabiTui Message Models ─────────────────────────────────────────────────

from __future__ import annotations

import datetime
from typing import Any, Self

from box import Box
from pydantic import model_validator
from sqlmodel import Column, Field

from habitui.config.app_config import app_config

from .base_model import HabiTuiSQLModel
from .validators import PydanticJSON, parse_datetime, replace_emoji_shortcodes


# ─── Base Message Model ───────────────────────────────────────────────────────
class MessageBase(HabiTuiSQLModel):
    """Base model for any message type, containing common fields and logic.

    :param timestamp: The time the message was sent.
    :param text: The formatted message text.
    :param unformatted_text: The raw message text.
    :param user: The display name of the sender.
    :param username: The username of the sender.
    :param uuid: The unique identifier of the sender.
    :param user_class: The character class of the sender.
    :param sent: A flag indicating if the message was sent by the current user.
    :param owner_id: The owner ID of the message.
    :param unique_message_id: A unique ID for the message.
    :param likes: A dictionary of user IDs who liked the message.
    :param position: The display order of the message.
    :param by_me: True if the message was sent by the authenticated user.
    :param by_system: True if the message is a system message.
    """

    timestamp: datetime.datetime
    text: str
    unformatted_text: str
    user: str | None = None
    username: str | None = None
    uuid: str
    user_class: str | None = None
    sent: bool = False
    owner_id: str | None = None
    unique_message_id: str | None = None
    likes: dict[str, bool] = Field(default_factory=dict, sa_column=Column(PydanticJSON))
    position: int | None = None
    by_me: bool = False
    by_system: bool = False

    @model_validator(mode="before")
    @classmethod
    def _parse_common_fields(cls, data: Any) -> Any:
        """Parses common fields from a raw data dictionary or Box."""
        data_box = data if isinstance(data, Box) else Box(data, camel_killer_box=True, default_box=True)

        data_box["text"] = replace_emoji_shortcodes(data_box.text)
        data_box["unformatted_text"] = replace_emoji_shortcodes(data_box.unformatted_text)
        data_box["user"] = replace_emoji_shortcodes(data_box.user)
        data_box["username"] = replace_emoji_shortcodes(data_box.username)

        data_box["timestamp"] = parse_datetime(data_box.timestamp)

        data_box["by_me"] = data_box.uuid == app_config.habitica.user_id
        data_box["by_system"] = data_box.uuid == "system"
        data_box["likes"] = data_box.get("likes") or {}

        if styles := data_box.userStyles:
            data_box["user_class"] = styles.stats.get("class")

        return data_box.to_dict()

    @classmethod
    def from_api_dict(cls, data: dict[str, Any] | Box, position: int) -> Self:
        """Factory method to create a message instance from API data.

        :param data: The raw API data for the message.
        :param position: The display order of the message.
        :returns: A MessageBase instance.
        """
        payload = dict(data) if isinstance(data, Box) else data
        return cls.model_validate({**payload, "position": position})


# ─── User Message ─────────────────────────────────────────────────────────────
class UserMessage(MessageBase, table=True):
    """Represents a direct user-to-user message in the database."""

    __tablename__ = "user_message"  # type: ignore


# ─── Party Message ────────────────────────────────────────────────────────────
class PartyMessage(MessageBase, table=True):
    """Represents a party chat message, extending UserMessage with info fields.

    :param group_id: The ID of the party/group.
    :param has_info: True if the message contains structured info (e.g., spell cast).
    :param info_type: The type of info (e.g., 'spell', 'quest_start').
    """

    __tablename__ = "party_message"  # type: ignore

    group_id: str | None = None
    has_info: bool = False
    info_type: str | None = None
    info_user: str | None = None
    info_class: str | None = None
    info_spell: str | None = None
    info_times: float | None = None
    info_quest: str | None = None
    info_items: dict[str, Any] = Field(default_factory=dict, sa_column=Column(PydanticJSON))
    info_target: str | None = None
    info_boss_damage: float | None = None
    info_user_damage: float | None = None
    likes: dict[str, bool] = Field(default_factory=dict, sa_column=Column(PydanticJSON))

    @model_validator(mode="before")
    @classmethod
    def _parse_party_specific_fields(cls, data: Any) -> Any:
        """Parses party-specific 'info' block from raw data."""
        data_box = data if isinstance(data, Box) else Box(data, camel_killer_box=True, default_box=True)

        if info := data_box.info:
            data_box["has_info"] = True
            data_box["info_type"] = info.type
            data_box["info_user"] = info.user or ""
            data_box["info_class"] = info.get("class") or ""
            data_box["info_spell"] = info.spell or ""
            data_box["info_times"] = info.times or 0.0
            data_box["info_quest"] = info.quest or ""
            data_box["info_items"] = info.get("items") or {}
            data_box["info_target"] = info.target or ""
            data_box["info_boss_damage"] = info.bossDamage or 0.0
            data_box["info_user_damage"] = info.userDamage or 0.0

        return data_box.to_dict()
