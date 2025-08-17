# ♥♥─── HabiTui Party Models ───────────────────────────────────────────────────

from __future__ import annotations

from typing import Any

from box import Box
from pydantic import model_validator
from sqlmodel import Field, Column

from .base_model import HabiTuiSQLModel, HabiTuiBaseModel
from .validators import PydanticJSON, replace_emoji_shortcodes
from .message_model import PartyMessage as PartyChat


# ─── Party Info ───────────────────────────────────────────────────────────────
class PartyInfo(HabiTuiSQLModel, table=True):
    """Represent a Habitica Party group and its details.

    Fields are self-explanatory from their names. Data is flattened
    from the nested API response during validation.

    :param name: The name of the party.
    :param description: Description of the party.
    :param summary: Summary of the party.
    :param logo: URL to the party logo.
    :param type: Type of the party.
    :param balance: Current balance of the party.
    :param challenge_count: Number of challenges in the party.
    :param member_count: Number of members in the party.
    :param has_leader: True if the party has a leader.
    :param leader_username: Username of the party leader.
    :param leader_id: User ID of the party leader.
    :param leader_name: Display name of the party leader.
    :param has_quest: True if the party has an active quest.
    :param quest_key: Key of the active quest.
    :param quest_active: True if the quest is active.
    :param quest_leader: Leader of the quest.
    :param quest_members: Members participating in the quest.
    :param quest_collect: Collected items in the quest.
    :param quest_collected_items: Collected items, flattened.
    :param quest_rage: Current rage value of the quest boss.
    :param quest_hp: Current HP of the quest boss.
    :param quest_up: Up points for the quest.
    :param quest_down: Down points for the quest.
    """

    __tablename__ = "party_info"  # type: ignore

    name: str
    description: str | None = None
    summary: str | None = None
    logo: str | None = None
    type: str
    balance: int = 0
    challenge_count: int = 0
    member_count: int = 0

    has_leader: bool = False
    leader_username: str | None = None
    leader_id: str | None = None
    leader_name: str | None = None

    has_quest: bool = False
    quest_key: str | None = None
    quest_active: bool = False
    quest_leader: str | None = None
    quest_members: dict[str, bool] = Field(
        default_factory=dict,
        sa_column=Column(PydanticJSON),
    )
    quest_collect: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(PydanticJSON),
    )
    quest_collected_items: Any = Field(
        default_factory=dict,
        sa_column=Column(PydanticJSON),
    )
    quest_rage: float | None = None
    quest_hp: float | None = None
    quest_up: float | None = None
    quest_down: float | None = None

    @model_validator(mode="before")
    @classmethod
    def _flatten_and_clean_data(cls, data: Any) -> Any:
        """Flatten nested API data and cleans text fields before validation.

        :param data: The raw API data for the party.
        :returns: A dictionary with flattened and cleaned data.
        """
        data_box = (
            data
            if isinstance(data, Box)
            else Box(data, camel_killer_box=True, default_box=True)
        )

        data_box["name"] = replace_emoji_shortcodes(data_box.name)
        data_box["description"] = replace_emoji_shortcodes(data_box.description)
        data_box["summary"] = replace_emoji_shortcodes(data_box.summary)

        if leader := data_box.leader:
            data_box["has_leader"] = True
            data_box["leader_id"] = leader.id
            data_box["leader_name"] = replace_emoji_shortcodes(leader.profile.name)
            if local_auth := leader.auth.get("local"):
                data_box["leader_username"] = local_auth.username

        if quest := data_box.quest:
            data_box["has_quest"] = True
            data_box["quest_key"] = quest.key or None
            data_box["quest_leader"] = quest.leader or None
            data_box["quest_members"] = quest.members or {}
            data_box["quest_active"] = quest.active or False
            if progress := quest.progress:
                data_box["quest_collect"] = progress.collect
                data_box["quest_collected_items"] = progress.collected_items
                data_box["quest_rage"] = progress.rage or 0.0
                data_box["quest_hp"] = progress.hp or 0.0
                data_box["quest_up"] = progress.up or 0.0
                data_box["quest_down"] = progress.down or 0.0
        return data_box.to_dict()


# ─── Party Collection ─────────────────────────────────────────────────────────
class PartyCollection(HabiTuiBaseModel):
    """Aggregate party information and chat messages.

    :param party_chat: A list of chat messages.
    :param party_info: The detailed party information.
    """

    party_chat: list[PartyChat]
    party_info: PartyInfo

    @classmethod
    def from_api_data(cls, raw_content: dict[str, Any]) -> PartyCollection:
        """Parse the raw API response into a PartyCollection instance.

        :param raw_content: The complete content data from the API.
        :returns: A populated PartyCollection instance.
        """
        info = PartyInfo.model_validate(raw_content)
        chat = [
            PartyChat.from_api_dict(data=chat_data, position=i)
            for i, chat_data in enumerate(raw_content.get("chat", []))
        ]
        return cls(party_chat=chat, party_info=info)

    def get_chat_messages(self) -> list[PartyChat] | None:
        """Return the list of party chat messages.

        :returns: A list of `PartyChat` messages, or None.
        """
        return self.party_chat

    def get_active_quest_key(self) -> str | None:
        """Return the key of the active quest, if any.

        :returns: The quest key string, or None.
        """
        if self.party_info and self.party_info.has_quest:
            return self.party_info.quest_key
        return None

    def get_system_messages(self, from_quest_start: bool = False) -> list[PartyChat]:
        """Return the list of party system messages.

        :returns: A list of `PartyChat` messages, or None.
        """
        system_messages = []
        for msg in self.party_chat:
            if msg.by_system is True:
                system_messages.append(msg)
                if from_quest_start and msg.info_type == "quest_start":
                    break
        return system_messages

    def get_user_messages(self) -> list[PartyChat]:
        """Return the list of party chat messages.

        :returns: A list of `PartyChat` messages, or None.
        """
        return [msg for msg in self.party_chat if not msg.by_system]

    def get_display_data(self) -> dict[str, Any]:
        data = {
            "display_name": self.party_info.name or "Unknown Party",
            "description": self.party_info.description or "",
            "summary": self.party_info.summary or "",
            "member_count": self.party_info.member_count or 0,
            "leader_name": self.party_info.leader_name or "",
            "leader_username": self.party_info.leader_username or "",
            "leader_id": self.party_info.leader_id or "",
            "has_quest": self.party_info.has_quest,
        }

        if self.party_info.has_quest:
            members = sum(self.party_info.quest_members.values())
            data.update({
                "quest_key": self.party_info.quest_key or "",
                "quest_active": self.party_info.quest_active or False,
                "quest_leader": self.party_info.quest_leader or "",
                "quest_members": members or 0,
                "quest_collect": self.party_info.quest_collect or None,
                "quest_collected_items": self.party_info.quest_collected_items or None,
                "quest_hp": self.party_info.quest_hp or 0,
                "quest_rage": self.party_info.quest_rage or 0,
                "quest_up": self.party_info.quest_up or 0,
                "quest_down": self.party_info.quest_down or 0,
            })

        return data
