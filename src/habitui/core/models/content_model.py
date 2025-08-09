# ♥♥─── HabiTui Content Models ─────────────────────────────────────────────────
"""SQLModels for game content entities like gear, spells, and quests."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TypeVar

from box import Box
from pydantic import Field as PydanticField
from pydantic import ValidationError, field_validator
from sqlmodel import Column, Field

from habitui.ui.custom_logger import log

from .base_model import HabiTuiBaseModel, HabiTuiSQLModel
from .validators import PydanticJSON, replace_emoji_shortcodes

T_ContentItem = TypeVar("T_ContentItem", bound="GameContentItem")

SuccessfulResponseData = dict[str, Any] | list[dict[str, Any]] | list[Any] | None


# ─── Base Item Model ──────────────────────────────────────────────────────────
class GameContentItem(HabiTuiSQLModel, ABC):
    """Abstract base model for game content items (gear, quests, spells).

    :param id: The primary key, same as the content key.
    :param key: The unique content key from the API.
    :param text: The user-facing name or text.
    :param notes: Additional notes or description.
    """

    id: str = Field(primary_key=True, index=True)
    key: str
    text: str
    notes: str

    @field_validator("text", "notes", mode="before")
    @classmethod
    def _validate_text_fields(cls, v: Any) -> str:
        """Cleans and replaces emoji shortcodes in text fields.

        :param v: The input value for the text field.
        :returns: The cleaned string.
        """
        return replace_emoji_shortcodes(str(v))

    @classmethod
    @abstractmethod
    def from_api_box(cls: type[T_ContentItem], *args: Any, **kwargs: Any) -> T_ContentItem:
        """Abstract factory method to create an instance from an API data box.

        :param args: Positional arguments for the factory method.
        :param kwargs: Keyword arguments for the factory method.
        :raises NotImplementedError: This method must be implemented by subclasses.
        """
        raise NotImplementedError


# ─── Gear Item ────────────────────────────────────────────────────────────────
class GearItem(GameContentItem, table=True):
    """Represents a piece of game gear.

    :param klass: The character class this gear belongs to.
    :param type: The type of gear (e.g., "armor", "weapon").
    :param special_class: Special class designation for bonus effects.
    :param two_handed: True if the weapon requires two hands.
    :param value: Purchase value of the gear.
    :param strength: Strength bonus.
    :param intelligence: Intelligence bonus.
    :param constitution: Constitution bonus.
    :param perception: Perception bonus.
    """

    __tablename__ = "gear_item"  # type: ignore

    klass: str
    type: str
    special_class: str | None = None
    two_handed: bool = False
    value: int
    strength: float = PydanticField(alias="str")
    intelligence: float = PydanticField(alias="int")
    constitution: float = PydanticField(alias="con")
    perception: float = PydanticField(alias="per")

    @classmethod
    def from_api_box(cls, key: str, data: Box) -> GearItem:
        """Creates GearItem from an API data box.

        :param key: The unique key of the gear item.
        :param data: The raw API data as a Box object.
        :returns: A GearItem instance.
        """
        return cls.model_validate({
            "key": key,
            "id": key,
            "text": data.text,
            "klass": data.klass,
            "notes": data.notes,
            "type": data.type,
            "special_class": data.special_class,
            "two_handed": data.two_handed or False,
            "value": data.value or 0,
            "str": data.get("str", 0.0),
            "int": data.get("int", 0.0),
            "con": data.get("con", 0.0),
            "per": data.get("per", 0.0),
        })


# ─── Spell Item ───────────────────────────────────────────────────────────────
class SpellItem(GameContentItem, table=True):
    """Represents a class spell.

    :param klass: The character class this spell belongs to.
    :param mana: Mana cost of the spell.
    :param target: Target type of the spell.
    :param immediate_use: True if the spell is used immediately upon purchase.
    :param limited: True if the spell has limited uses.
    :param level: Minimum user level to use the spell.
    :param previous_purchase: True if the spell was previously purchased.
    :param purchase_type: How the spell is purchased.
    :param silent: True if casting the spell does not generate chat messages.
    :param value: Gold cost of the spell.
    """

    __tablename__ = "spell_item"  # type: ignore

    klass: str
    mana: int
    target: str
    immediate_use: bool = False
    limited: bool = False
    level: int = Field(0, alias="lvl")
    previous_purchase: bool = False
    purchase_type: str | None = None
    silent: bool = False
    value: int = 0

    @classmethod
    def from_api_box(cls, key: str, class_key: str, data: Box) -> SpellItem:
        """Creates SpellItem from an API data box.

        :param key: The unique key of the spell item.
        :param class_key: The class key the spell belongs to.
        :param data: The raw API data as a Box object.
        :returns: A SpellItem instance.
        """
        return cls.model_validate({
            "key": key,
            "id": key,
            "klass": class_key,
            "text": data.text,
            "notes": data.notes,
            "mana": data.mana or 0,
            "target": data.target or "",
            "immediate_use": data.immediate_use or False,
            "limited": data.limited or False,
            "lvl": data.lvl or 0,
            "previous_purchase": data.previous_purchase or False,
            "purchase_type": data.purchase_type,
            "silent": data.silent or False,
            "value": data.value or 0,
        })


# ─── Quest Item ───────────────────────────────────────────────────────────────
class QuestItem(GameContentItem, table=True):
    """Represents a quest, with flattened boss and drop info.

    :param value: Value of the quest.
    :param category: Category of the quest.
    :param completion: Completion type of the quest.
    :param gold_value: Gold reward for completing the quest.
    :param addl_notes: Additional notes for the quest.
    :param completion_chat: Chat message upon completion.
    :param level: Minimum user level for the quest.
    :param is_boss_quest: True if the quest involves a boss.
    :param boss_name: Name of the boss.
    :param boss_hp: Boss's HP.
    :param boss_str: Boss's strength.
    :param boss_def: Boss's defense.
    :param has_rage: True if the boss has a rage mechanic.
    :param rage_title: Title of the rage ability.
    :param rage_description: Description of the rage ability.
    :param rage_value: Value associated with rage.
    :param rage_healing: Healing from rage.
    :param rage_effect: Effect of rage.
    :param rage_mp_drain: MP drain from rage.
    :param rage_progress_drain: Progress drain from rage.
    :param rage_bailey: Bailey effect from rage.
    :param rage_stables: Stables effect from rage.
    :param rage_market: Market effect from rage.
    :param rage_quests: Quests effect from rage.
    :param rage_seasonal_shop: Seasonal shop effect from rage.
    :param rage_tavern: Tavern effect from rage.
    :param rage_guide: Guide effect from rage.
    :param has_desesperation: True if the boss has a desperation mechanic.
    :param desesperation_def: Desperation defense.
    :param desesperation_str: Desperation strength.
    :param desesperation_text: Desperation text.
    :param desesperation_threshold: Desperation threshold.
    :param drop_exp: Experience from drops.
    :param drop_gp: Gold from drops.
    :param drop_items: Items from drops.
    :param has_collect: True if the quest involves collecting items.
    :param collect_items: Items to collect.
    """

    __tablename__ = "quest_item"  # type: ignore

    value: int = 0
    category: str
    completion: str
    gold_value: int = 0
    addl_notes: str | None = None
    completion_chat: str | None = None
    level: int = Field(0, alias="lvl")
    is_boss_quest: bool = False
    boss_name: str | None = None
    boss_hp: int | None = None
    boss_str: float | None = None
    boss_def: int | None = None
    has_rage: bool = False
    rage_title: str | None = None
    rage_description: str | None = None
    rage_value: int | None = None
    rage_healing: float | None = None
    rage_effect: str | None = None
    rage_mp_drain: float | None = None
    rage_progress_drain: float | None = None
    rage_bailey: str | None = None
    rage_stables: str | None = None
    rage_market: str | None = None
    rage_quests: str | None = None
    rage_seasonal_shop: str | None = None
    rage_tavern: str | None = None
    rage_guide: str | None = None

    has_desesperation: bool = False
    desesperation_def: int | None = None
    desesperation_str: float | None = None
    desesperation_text: str | None = None
    desesperation_threshold: int | None = None

    drop_exp: float | None = None
    drop_gp: float | None = None
    drop_items: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(PydanticJSON))
    has_collect: bool = False
    collect_items: list[dict[str, Any]] | None = Field(None, sa_column=Column(PydanticJSON))

    @classmethod
    def from_api_box(cls, key: str, data: Box) -> QuestItem:
        """Creates QuestItem from an API data box, flattening nested data.

        :param key: The unique key of the quest item.
        :param data: The raw API data as a Box object.
        :returns: A QuestItem instance.
        """
        flat_data: dict[str, Any] = {
            "key": key,
            "id": key,
            "text": data.text,
            "notes": data.notes,
            "value": data.value or 0,
            "category": data.category,
            "completion": data.completion,
            "gold_value": data.gold_value or 0,
            "addl_notes": data.addl_notes,
            "completion_chat": data.completion_chat,
            "lvl": data.lvl or 0,
        }

        if boss := data.boss:
            flat_data.update({
                "is_boss_quest": True,
                "boss_name": boss.name,
                "boss_hp": boss.hp or 0,
                "boss_str": boss.get("str", 0.0),
                "boss_def": boss.get("def", 0),
            })
            if rage := boss.rage:
                flat_data.update({
                    "has_rage": True,
                    "rage_title": rage.title,
                    "rage_description": rage.description,
                    "rage_value": rage.value or 0,
                    "rage_healing": rage.healing or 0.0,
                    "rage_effect": rage.effect,
                    "rage_mp_drain": rage.mp_drain or 0.0,
                    "rage_progress_drain": rage.progress_drain or 0.0,
                    "rage_bailey": rage.bailey,
                    "rage_stables": rage.stables,
                    "rage_market": rage.market,
                    "rage_quests": rage.quests,
                    "rage_seasonal_shop": rage.seasonal_shop,
                    "rage_tavern": rage.tavern,
                    "rage_guide": rage.guide,
                })
            if desp := boss.desesperation:
                flat_data.update({
                    "has_desesperation": True,
                    "desesperation_def": desp.get("def", 0),
                    "desesperation_str": desp.get("str", 0.0),
                    "desesperation_text": desp.text,
                    "desesperation_threshold": desp.threshold or 0,
                })

        if drop := data.drop:
            flat_data.update({
                "drop_exp": float(drop.exp or 0),
                "drop_gp": float(drop.gp or 0),
                "drop_items": drop["items"] or [],
            })

        if collect := data.collect:
            flat_data["has_collect"] = True
            flat_data["collect_items"] = [{"key": k, "text": v.text, "count": v.count or 0} for k, v in collect.items()]

        return cls.model_validate(flat_data)


# ─── Main General Collection ──────────────────────────────────────────────────
class ContentCollection(HabiTuiBaseModel):
    """A Pydantic model that holds all parsed game content.

    :param gear: Dictionary of gear items.
    :param quests: Dictionary of quest items.
    :param spells: Dictionary of spell items.
    """

    gear: dict[str, GearItem] = PydanticField(default_factory=dict)
    quests: dict[str, QuestItem] = PydanticField(default_factory=dict)
    spells: dict[str, SpellItem] = PydanticField(default_factory=dict)

    @classmethod
    def from_api_data(cls, raw_content: SuccessfulResponseData) -> ContentCollection:
        """Parses raw API data into a ContentCollection.

        :param raw_content: The raw content data from the API.
        :returns: A populated ContentCollection instance.
        """
        api_box = Box(raw_content, default_box=True, camel_killer_box=True, default_box_attr=None)
        return cls(
            gear=cls._parse_content_items(api_box.gear.flat, GearItem, "gear"),
            quests=cls._parse_content_items(api_box.quests, QuestItem, "quest"),
            spells=cls._parse_spells(api_box.spells),
        )

    @staticmethod
    def _parse_content_items(box_data: Box, model_cls: type[T_ContentItem], type_name: str) -> dict[str, T_ContentItem]:
        """Generic parser for simple key-value content items.

        :param box_data: Box object containing the raw data.
        :param model_cls: The target `GameContentItem` subclass.
        :param type_name: The name of the content type (for logging).
        :returns: A dictionary of parsed content items.
        """
        parsed_items = {}
        for key, data in box_data.items():
            try:
                parsed_items[key] = model_cls.from_api_box(key, data)
            except (ValidationError, TypeError, ValueError) as e:
                log.warning("Failed to parse {} item '{}': {}", type_name, key, e)
        return parsed_items

    @staticmethod
    def _parse_spells(spells_box: Box) -> dict[str, SpellItem]:
        """Specific parser for spell items due to their nested structure.

        :param spells_box: Box object containing raw spell data.
        :returns: A dictionary of parsed spell items.
        """
        parsed_spells = {}
        for class_key, class_spells in spells_box.items():
            for spell_key, spell_data in class_spells.items():
                try:
                    parsed_spells[spell_key] = SpellItem.from_api_box(spell_key, class_key, spell_data)
                except (ValidationError, TypeError, ValueError) as e:
                    log.warning("Failed to parse spell '{}' (class {}): {}", spell_key, class_key, e)
        return parsed_spells

    def get_quest(self, key: str) -> QuestItem:
        """Retrieves a quest by its key.

        :param key: The key of the quest.
        :returns: The `QuestItem` or None if not found.
        """
        return self.quests.get(key)  # pyright: ignore[reportReturnType]

    def get_gear(self, key: str) -> GearItem | None:
        """Retrieves a gear item by its key.

        :param key: The key of the gear item.
        :returns: The `GearItem` or None if not found.
        """
        return self.gear.get(key)

    def get_spell(self, key: str) -> SpellItem | None:
        """Retrieves a spell by its key.

        :param key: The key of the spell.
        :returns: The `SpellItem` or None if not found.
        """
        return self.spells.get(key)

    def get_spells_by_class(self, character_class: str) -> list[SpellItem]:
        """Retrieves all spells belonging to a specific character class.

        :param character_class: The character class (e.g., "warrior").
        :returns: A list of `SpellItem` instances.
        """
        return [spell for spell in self.spells.values() if spell.klass == character_class]
