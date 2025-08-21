# ♥♥─── HabiTui Tag Models ─────────────────────────────────────────────────────
"""Models for representing Habitica tags and their hierarchical structures."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import TYPE_CHECKING, Any
from collections import defaultdict

from pydantic import Field, ValidationError

from habitui.custom_logger import log
from habitui.config.app_config_model import TagSettings

from .base_enums import Attribute, TagsTrait, TagsCategory
from .base_model import HabiTuiSQLModel, HabiTuiBaseModel


if TYPE_CHECKING:
    from collections.abc import Iterator


# ─── Constants ─────────────────────────────────────────────────────────────────
ATTRIBUTE_SYMBOLS: dict[str, str] = {
    "🜄": "con",  # Water symbol → Constitution
    "🜂": "str",  # Fire symbol → Strength
    "🜁": "int",  # Air symbol → Intelligence
    "🜃": "per",  # Earth symbol → Perception
    "᛭": "legacy",  # Nordic cross symbol → Legacy  # noqa: RUF001
}

SYMBOL_REGEX = re.compile(f"({'|'.join(re.escape(s) for s in ATTRIBUTE_SYMBOLS)})")


class TagType(StrEnum):
    """Tag classification types."""

    BASIC = "basic"
    PARENT = "parent"
    SUBTAG = "subtag"


# ─── Core Tag Models ───────────────────────────────────────────────────────────
class TagComplex(HabiTuiSQLModel, table=True):
    """Extended tag model with hierarchical relationships."""

    __tablename__ = "tag_complex"  # type: ignore
    name: str
    challenge: bool = False
    position: int | None = None

    tag_type: TagType = Field(default=TagType.BASIC)
    trait: TagsTrait | None = Field(default=None)
    attribute: Attribute | None = Field(default=None)
    category: TagsCategory | None = Field(default=None)
    parent_id: str | None = Field(default=None)

    @property
    def display_name(self) -> str:
        """Returns the display name, removing attribute symbols from subtags."""
        if self.is_subtag():
            match = SYMBOL_REGEX.match(self.name)
            if match:
                return self.name[len(match.group(1)) :].strip()
        return self.name

    def is_parent(self) -> bool:
        """Check if this tag is a parent tag."""
        return self.tag_type == TagType.PARENT

    def is_subtag(self) -> bool:
        """Check if this tag is a subtag."""
        return self.tag_type == TagType.SUBTAG

    def is_base(self) -> bool:
        """Check if this tag is a base tag."""
        return self.tag_type == TagType.BASIC

    def has_trait(self) -> str | None:
        """Check if this tag is a base tag."""
        return self.trait


# ─── Tag Factory ───────────────────────────────────────────────────────────────
class TagFactory:
    """Factory for creating tags from raw API data."""

    def __init__(self) -> None:
        self.tag_settings = TagSettings()
        self._build_maps()

    def _build_maps(self) -> None:
        """Build mapping dictionaries for tag ID to trait relationships."""
        self.id_to_attr = {}
        self.attr_to_parent = {}
        if self.tag_settings:
            log.warning("NO HAY TAGSS")
        if self.tag_settings.id_attr_str:
            self.id_to_attr[str(self.tag_settings.id_attr_str)] = "str"
        if self.tag_settings.id_attr_int:
            self.id_to_attr[str(self.tag_settings.id_attr_int)] = "int"
        if self.tag_settings.id_attr_con:
            self.id_to_attr[str(self.tag_settings.id_attr_con)] = "con"
        if self.tag_settings.id_attr_per:
            self.id_to_attr[str(self.tag_settings.id_attr_per)] = "per"

        self.attr_to_parent = {v: k for k, v in self.id_to_attr.items()}

    def _detect_attribute_from_symbol(self, name: str) -> str | None:
        """Detect attribute type from Unicode symbols in tag name."""
        match = SYMBOL_REGEX.search(name)
        return ATTRIBUTE_SYMBOLS.get(match.group(1)) if match else None

    def determine_tag_data(
        self,
        tag_id: str,
        name: str,
    ) -> tuple[
        TagType,
        TagsCategory | None,
        TagsTrait | None,
        Attribute | None,
        str | None,
    ]:
        """Determine tag type, parent_id, and attribute from tag ID and name."""
        tag_id = str(tag_id)

        # Check if it's an attribute parent tag
        if tag_id in self.id_to_attr:
            return (
                TagType.PARENT,
                TagsCategory.ATTRIBUTE,
                self.id_to_attr[tag_id],
                self.id_to_attr[tag_id],
                None,
            )
        if self.tag_settings.id_no_attr and tag_id == str(self.tag_settings.id_no_attr):
            return (
                TagType.PARENT,
                TagsCategory.ATTRIBUTE,
                TagsTrait.NO_ATTRIBUTE,
                None,
                None,
            )

        # Check if it's a challenge parent tag
        if self.tag_settings.id_challenge and tag_id == str(
            self.tag_settings.id_challenge,
        ):
            return (
                TagType.PARENT,
                TagsCategory.OWNERSHIP,
                TagsTrait.CHALLENGE,
                None,
                None,
            )

        # Check if it's a personal parent tag
        if self.tag_settings.id_personal and tag_id == str(
            self.tag_settings.id_personal,
        ):
            return (
                TagType.PARENT,
                TagsCategory.OWNERSHIP,
                TagsTrait.PERSONAL,
                None,
                None,
            )

        # Check if it's a legacy subtag (child of challenge)
        if self.tag_settings.id_legacy and tag_id == str(self.tag_settings.id_legacy):
            challenge_id = (
                str(self.tag_settings.id_challenge)
                if self.tag_settings.id_challenge
                else None
            )
            return (
                TagType.PARENT,
                TagsCategory.OWNERSHIP,
                TagsTrait.LEGACY,
                None,
                challenge_id,
            )

        attr = self._detect_attribute_from_symbol(name)
        if attr == "legacy" and self.tag_settings.id_legacy:
            return TagType.SUBTAG, None, None, None, str(self.tag_settings.id_legacy)

        # Check for attribute symbols in subtag names
        if attr and attr in self.attr_to_parent:
            return (
                TagType.SUBTAG,
                None,
                None,
                Attribute(attr),
                self.attr_to_parent[attr],
            )
        # Default to base tag
        return TagType.BASIC, None, None, None, None

    def create_tag(
        self,
        raw_data: dict[str, Any],
        position: int | None = None,
    ) -> TagComplex:
        """Create a TagComplex instance from raw API data."""
        tag_id = str(raw_data.get("id", ""))
        name = raw_data.get("name", raw_data.get("text", "Unnamed"))
        challenge = raw_data.get("challenge", False)

        tag_type, category, trait, attribute, parent_id = self.determine_tag_data(
            tag_id,
            name,
        )

        model_input = {
            "id": tag_id,
            "name": name,
            "tag_type": tag_type,
            "category": category,
            "trait": trait,
            "parent_id": parent_id,
            "attribute": attribute,
            "challenge": challenge,
            "position": position,
        }

        try:
            return TagComplex.model_validate(model_input)
        except ValidationError as e:
            log.error(
                "Validation failed for tag ID '{}' (name: '{}', type: '{}'): {}",
                tag_id,
                name,
                tag_type,
                e.errors(include_url=False, include_input=False),
            )
            raise


# ─── Tag Collection ────────────────────────────────────────────────────────────
class TagCollection(HabiTuiBaseModel):
    """Collection for managing multiple tags with hierarchical relationships."""

    tags: list[TagComplex] = Field(default_factory=list)

    def _build_index(self) -> None:
        """Build internal index for fast lookups."""
        self._index_by_id = {tag.id: tag for tag in self.tags}

    @classmethod
    def from_api_data(cls, raw_list: list[dict[str, Any]]) -> TagCollection:
        """Create TagCollection from raw API data."""
        factory = TagFactory()
        tags = []

        for i, raw_data in enumerate(raw_list):
            if isinstance(raw_data, dict):
                try:
                    tag = factory.create_tag(raw_data, position=i)
                    tags.append(tag)
                except ValidationError:
                    log.warning("Skipping invalid tag data: {}", raw_data)
                    continue

        return cls(tags=tags)

    # ─── Core CRUD Operations ──────────────────────────────────────────────────
    def add_tag(self, tag: TagComplex) -> None:
        """Add a tag to the collection."""
        if tag.id not in self._index_by_id:
            self.tags.append(tag)
            self._index_by_id[tag.id] = tag
            self._update_positions()
            log.debug("Added tag '{}' (ID: {}...)", tag.name, tag.id[:8])
        else:
            log.debug("Tag '{}' already exists", tag.name)

    def remove_tag(self, tag_id: str) -> bool:
        """Remove a tag by ID."""
        if tag_id in self._index_by_id:
            tag = self._index_by_id.pop(tag_id)
            self.tags = [t for t in self.tags if t.id != tag_id]
            self._update_positions()
            log.debug("Removed tag '{}' (ID: {}...)", tag.name, tag_id[:8])
            return True
        return False

    def update_tag(self, tag_id: str, update_data: dict[str, Any]) -> TagComplex | None:
        """Update an existing tag. Use update_data={'name': 'new_name'} for name updates."""
        tag = self.get_by_id(tag_id)
        if not tag:
            log.warning("Tag with ID '{}...' not found for update", tag_id[:8])
            return None

        # Validate name if provided
        if "name" in update_data and not update_data["name"].strip():
            log.warning("Cannot update tag '{}...' with empty name", tag_id[:8])
            return None

        try:
            # Preserve position if not explicitly updated
            if "position" not in update_data and tag.position is not None:
                update_data["position"] = tag.position

            # Strip name if provided
            if "name" in update_data:
                update_data["name"] = update_data["name"].strip()

            updated_tag = tag.model_copy(update=update_data)

            # Replace in collection
            for i, t in enumerate(self.tags):
                if t.id == tag_id:
                    self.tags[i] = updated_tag
                    self._index_by_id[tag_id] = updated_tag
                    break

            log.debug("Updated tag '{}' (ID: {}...)", updated_tag.name, tag_id[:8])
            return updated_tag

        except ValidationError as e:
            log.error(
                "Validation error updating tag '{}...': {}",
                tag_id[:8],
                e.errors(),
            )
            return None

    def _update_positions(self) -> None:
        """Update position values for all tags."""
        for i, tag in enumerate(self.tags):
            tag.position = i

    # ─── Query Methods ─────────────────────────────────────────────────────────
    def get_by_id(self, tag_id: str) -> TagComplex | None:
        """Get a tag by its ID."""
        return self._index_by_id.get(tag_id)

    def filter_by_name(
        self,
        name_substring: str,
        case_sensitive: bool = False,
    ) -> list[TagComplex]:
        """Filter tags by name substring."""
        if not name_substring:
            return list(self.tags)

        if case_sensitive:
            return [tag for tag in self.tags if name_substring in tag.name]

        substring_lower = name_substring.lower()
        return [tag for tag in self.tags if substring_lower in tag.name.lower()]

    def get_by_category_trait(
        self,
        category: TagsCategory,
        trait: TagsTrait,
    ) -> TagComplex | None:
        """Get tag by category and trait combination."""
        return next(
            (
                tag
                for tag in self.tags
                if tag.category == category and tag.trait == trait
            ),
            None,
        )

    def get_subtags_for_parent(self, parent_id: str) -> list[TagComplex]:
        """Get all subtags for a specific parent."""
        return [tag for tag in self.subtags if tag.parent_id == parent_id]

    def get_by_attribute(self, attribute: str | Attribute) -> list[TagComplex]:
        """Get all tags with a specific attribute."""
        if isinstance(attribute, Attribute):
            # Get subtags for attribute parent
            parent_map = {
                Attribute.STRENGTH: (TagsCategory.ATTRIBUTE, TagsTrait.STRENGTH),
                Attribute.INTELLIGENCE: (
                    TagsCategory.ATTRIBUTE,
                    TagsTrait.INTELLIGENCE,
                ),
                Attribute.CONSTITUTION: (
                    TagsCategory.ATTRIBUTE,
                    TagsTrait.CONSTITUTION,
                ),
                Attribute.PERCEPTION: (TagsCategory.ATTRIBUTE, TagsTrait.PERCEPTION),
            }
            if attribute in parent_map:
                category, trait = parent_map[attribute]
                parent = self.get_by_category_trait(category, trait)
                return self.get_subtags_for_parent(parent.id) if parent else []
            return []

        # String attribute lookup
        return [tag for tag in self.tags if tag.attribute == attribute]

    # ─── Categorization Properties ─────────────────────────────────────────────
    @property
    def parents(self) -> list[TagComplex]:
        """Get all parent tags."""
        return [tag for tag in self.tags if tag.is_parent()]

    @property
    def subtags(self) -> list[TagComplex]:
        """Get all subtags."""
        return [tag for tag in self.tags if tag.is_subtag()]

    @property
    def base_tags(self) -> list[TagComplex]:
        """Get all base tags."""
        return [tag for tag in self.tags if tag.is_base()]

    @property
    def challenge_tags(self) -> list[TagComplex]:
        """Get all challenge-related tags."""
        return [tag for tag in self.tags if tag.challenge]

    @property
    def personal_tags(self) -> list[TagComplex]:
        """Get all non-challenge tags."""
        return [tag for tag in self.tags if not tag.challenge]

    def get_legacy_tags(self) -> list[TagComplex]:
        """Get all legacy area subtags (with ᛭ symbol)."""  # noqa: RUF002
        parent = self.get_by_category_trait(TagsCategory.OWNERSHIP, TagsTrait.LEGACY)
        return self.get_subtags_for_parent(parent.id) if parent else []

    # ─── Grouping Methods ──────────────────────────────────────────────────────
    def group_by(self, key: str) -> dict[str, list[TagComplex]]:
        """Group tags by a specified attribute. Supports 'parent_id', 'attribute', 'category', 'trait'."""
        grouped = defaultdict(list)

        for tag in self.tags:
            if key == "parent_id" and tag.parent_id:
                grouped[tag.parent_id].append(tag)
            elif key == "attribute" and tag.attribute:
                grouped[tag.attribute].append(tag)
            elif hasattr(tag, key):
                value = getattr(tag, key)
                if value:
                    grouped[str(value)].append(tag)

        return dict(grouped)

    # ─── Convenience Parent Getters ───────────────────────────────────────────
    # Consolidated parent getters using the unified method
    def get_personal_parent(self) -> TagComplex | None:
        return self.get_by_category_trait(TagsCategory.OWNERSHIP, TagsTrait.PERSONAL)

    def get_challenge_parent(self) -> TagComplex | None:
        return self.get_by_category_trait(TagsCategory.OWNERSHIP, TagsTrait.CHALLENGE)

    def get_legacy_parent(self) -> TagComplex | None:
        return self.get_by_category_trait(TagsCategory.OWNERSHIP, TagsTrait.LEGACY)

    def get_str_parent(self) -> TagComplex | None:
        return self.get_by_category_trait(TagsCategory.ATTRIBUTE, TagsTrait.STRENGTH)

    def get_int_parent(self) -> TagComplex | None:
        return self.get_by_category_trait(
            TagsCategory.ATTRIBUTE,
            TagsTrait.INTELLIGENCE,
        )

    def get_con_parent(self) -> TagComplex | None:
        return self.get_by_category_trait(
            TagsCategory.ATTRIBUTE,
            TagsTrait.CONSTITUTION,
        )

    def get_per_parent(self) -> TagComplex | None:
        return self.get_by_category_trait(TagsCategory.ATTRIBUTE, TagsTrait.PERCEPTION)

    def get_no_attr_parent(self) -> TagComplex | None:
        return self.get_by_category_trait(
            TagsCategory.ATTRIBUTE,
            TagsTrait.NO_ATTRIBUTE,
        )

    def get_parents_by_category(self, category: TagsCategory) -> list[TagComplex]:
        """Get all parent tags by category."""
        return [tag for tag in self.tags if tag.category == category]

    # ─── Collection Interface ──────────────────────────────────────────────────
    def __len__(self) -> int:
        return len(self.tags)

    def __iter__(self) -> Iterator[TagComplex]:
        return iter(self.tags)

    def __getitem__(self, index: int | slice) -> TagComplex | list[TagComplex]:
        return self.tags[index]

    def __contains__(self, item_or_id: TagComplex | str) -> bool:
        if isinstance(item_or_id, str):
            return item_or_id in self._index_by_id
        return item_or_id in self.tags
