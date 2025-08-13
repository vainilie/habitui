# ♥♥─── Tag Modal Builders Using Generic Base Classes ─────────────────────

from __future__ import annotations

from typing import Any

from habitui.ui import icons
from habitui.core.models.tag_model import TagsTrait, TagComplex
from habitui.tui.generic.edit_modal import FieldType, FormField, GenericEditModal
from habitui.tui.generic.confirm_modal import GenericConfirmModal


# ─── Tag Confirmation Modals ───────────────────────────────────────────────────


def create_tag_delete_modal(tag: TagComplex) -> GenericConfirmModal:
    """Create a confirmation modal for tag deletion."""
    # Determine warning level based on tag type
    is_parent = tag.is_parent()
    has_subtags = is_parent  # Assuming parents have subtags

    if is_parent:
        question = (
            f"Are you sure you want to delete the parent tag '{tag.name}'?\n\n"
            f"{icons.WARNING} This will also delete all its subtags and cannot be undone."
        )
        confirm_variant = "error"
        icon = icons.WARNING
    else:
        question = f"Are you sure you want to delete the tag '{tag.name}'?"
        confirm_variant = "warning"
        icon = icons.QUESTION_CIRCLE

    return GenericConfirmModal(
        question=question,
        title="Delete Tag",
        confirm_text="Delete",
        cancel_text="Cancel",
        confirm_variant=confirm_variant,
        icon=icon,
    )


def create_tag_changes_confirm_modal(
    tag_name: str,
    changes: dict[str, Any],
) -> GenericConfirmModal:
    """Create a confirmation modal for tag changes."""
    return GenericConfirmModal(
        question=f"Save changes to tag '{tag_name}'?",
        changes=changes,
        title="Confirm Tag Changes",
        changes_formatter=_format_tag_changes,
        icon=icons.EDIT,
    )


def _format_tag_changes(changes: dict[str, Any]) -> list[tuple[str, str]]:
    formatted = []

    for key, value in changes.items():
        if key == "name":
            formatted.append(("Name", value))
        elif key == "attribute":
            # Map attribute values to display names
            attr_map = {
                "str": "Strength",
                "int": "Intelligence",
                "con": "Constitution",
                "per": "Perception",
            }
            display_value = attr_map.get(value, value.title() if value else "None")
            formatted.append(("Attribute", display_value))
        elif key == "parent_id":
            formatted.append(("Parent", "Updated" if value else "Removed"))
        elif key == "position":
            formatted.append(("Position", str(value)))
        else:
            formatted.append((key.replace("_", " ").title(), str(value)))

    return formatted


# ─── Tag Edit Modals ───────────────────────────────────────────────────────────


def create_tag_edit_modal(
    tag: TagComplex,
    available_parents: list[TagComplex] | None = None,
) -> GenericEditModal:
    """Create an edit modal for an existing tag."""
    # Build parent options if tag is a subtag
    parent_options = None
    if tag.is_subtag() and available_parents:
        parent_options = [("", "No Parent")] + [
            (parent.id, parent.name)
            for parent in available_parents
            if parent.is_parent()
        ]

    # Build attribute options for subtags
    attribute_options = [
        ("", "No Attribute"),
        ("str", "Strength"),
        ("int", "Intelligence"),
        ("con", "Constitution"),
        ("per", "Perception"),
    ]

    fields = [
        FormField(
            id="name",
            label="Tag Name",
            field_type=FieldType.TEXT,
            placeholder="Enter tag name",
            required=True,
        ),
    ]

    # Add parent selection for subtags
    if tag.is_subtag() and parent_options:
        fields.append(
            FormField(
                id="parent_id",
                label="Parent Tag",
                field_type=FieldType.SELECT,
                options=parent_options,
                help_text="Select the parent category for this tag",
            ),
        )

    # Add attribute selection for subtags
    if tag.is_subtag():
        fields.append(
            FormField(
                id="attribute",
                label="Attribute",
                field_type=FieldType.SELECT,
                options=attribute_options,
                help_text="Select the RPG attribute for this life area",
            ),
        )

    original_data = {
        "name": tag.name,
        "parent_id": tag.parent_id or "",
        "attribute": tag.attribute or "",
    }

    return GenericEditModal(
        title=f"Edit Tag: {tag.name}",
        fields=fields,
        original_data=original_data,
        icon=icons.EDIT,
        auto_focus="name",
    )


def create_tag_create_modal(
    tag_type: str = "subtag",
    available_parents: list[TagComplex] | None = None,
    default_parent_id: str | None = None,
) -> GenericEditModal:
    """Create a modal for creating a new tag."""
    is_creating_subtag = tag_type == "subtag"

    # Build parent options for subtags
    parent_options = None
    if is_creating_subtag and available_parents:
        parent_options = [
            (parent.id, parent.name)
            for parent in available_parents
            if parent.is_parent()
        ]

    # Build attribute options
    attribute_options = [
        ("", "No Attribute"),
        ("str", "Strength"),
        ("int", "Intelligence"),
        ("con", "Constitution"),
        ("per", "Perception"),
    ]

    fields = [
        FormField(
            id="name",
            label="Tag Name",
            field_type=FieldType.TEXT,
            placeholder="Enter tag name",
            required=True,
        ),
    ]

    # Add fields specific to subtags
    if is_creating_subtag:
        if parent_options:
            fields.append(
                FormField(
                    id="parent_id",
                    label="Parent Tag",
                    field_type=FieldType.SELECT,
                    options=parent_options,
                    required=True,
                    help_text="Select the parent category for this tag",
                ),
            )

        fields.append(
            FormField(
                id="attribute",
                label="Attribute",
                field_type=FieldType.SELECT,
                options=attribute_options,
                help_text="Select the RPG attribute for this life area",
            ),
        )

    original_data = {
        "name": "",
        "parent_id": default_parent_id or "",
        "attribute": "",
    }

    title = "Create New Subtag" if is_creating_subtag else "Create New Tag"

    return GenericEditModal(
        title=title,
        fields=fields,
        original_data=original_data,
        save_text="Create",
        icon=icons.PLUS,
        auto_focus="name",
        track_changes=False,  # Return all data for creation
    )


# ─── Specialized Tag Creation Shortcuts ────────────────────────────────────────


def create_strength_tag_modal(
    strength_parent: TagComplex,
) -> GenericEditModal:
    """Quick modal for creating a strength-based life area tag."""
    return create_tag_create_modal(
        tag_type="subtag",
        available_parents=[strength_parent],
        default_parent_id=strength_parent.id,
    )


def create_life_area_modal(
    attribute_parents: list[TagComplex],
    default_attribute: str | None = None,
) -> GenericEditModal:
    """Modal for creating a life area tag with attribute selection."""
    modal = create_tag_create_modal(
        tag_type="subtag",
        available_parents=attribute_parents,
    )

    # Pre-select attribute if provided
    if default_attribute:
        modal.original_data["attribute"] = default_attribute
        # Find and pre-select corresponding parent
        for parent in attribute_parents:
            if (
                (parent.trait == TagsTrait.STRENGTH and default_attribute == "str")
                or (
                    parent.trait == TagsTrait.INTELLIGENCE
                    and default_attribute == "int"
                )
                or (
                    parent.trait == TagsTrait.CONSTITUTION
                    and default_attribute == "con"
                )
                or (parent.trait == TagsTrait.PERCEPTION and default_attribute == "per")
            ):
                modal.original_data["parent_id"] = parent.id
                break

    return modal


# ─── Batch Operations Modals ───────────────────────────────────────────────────


def create_batch_tag_delete_modal(tag_count: int) -> GenericConfirmModal:
    """Create confirmation modal for batch tag deletion."""
    return GenericConfirmModal(
        question=f"Are you sure you want to delete {tag_count} selected tags?",
        title="Batch Delete Tags",
        confirm_text=f"Delete {tag_count} Tags",
        cancel_text="Cancel",
        confirm_variant="error",
        icon=icons.WARNING,
        custom_content=[
            # Could add Static widgets showing affected tags
        ],
    )


def create_reorder_confirm_modal(reorder_count: int) -> GenericConfirmModal:
    """Create confirmation modal for tag reordering."""
    return GenericConfirmModal(
        question=f"Apply new order to {reorder_count} tags?",
        title="Confirm Reorder",
        confirm_text="Apply Order",
        cancel_text="Cancel",
        confirm_variant="success",
        icon=icons.SORT,
    )


# ─── Usage Examples ────────────────────────────────────────────────────────────


def show_tag_workflow_example():
    """Example of how to use the tag modals in a workflow."""

    # Example workflow for editing a tag
    async def edit_tag_workflow(tag: TagComplex, collection):
        # 1. Show edit modal
        edit_modal = create_tag_edit_modal(tag, collection.parents)
        result = await app.push_screen_wait_for_return(edit_modal)

        if result:
            if result:  # Changes detected
                confirm_modal = create_tag_changes_confirm_modal(tag.name, result)
                confirmed = await app.push_screen_wait_for_return(confirm_modal)

                if confirmed:
                    # 3. Apply changes
                    collection.update_tag(tag.id, result)

    # Example workflow for deleting a tag
    async def delete_tag_workflow(tag: TagComplex, collection):
        # 1. Show delete confirmation
        delete_modal = create_tag_delete_modal(tag)
        confirmed = await app.push_screen_wait_for_return(delete_modal)

        if confirmed:
            # 2. Perform deletion
            collection.remove_tag(tag.id)

    # Example workflow for creating a tag
    async def create_tag_workflow(collection, parent_id=None):
        # 1. Show creation modal
        create_modal = create_tag_create_modal(
            available_parents=collection.parents,
            default_parent_id=parent_id,
        )
        result = await app.push_screen_wait_for_return(create_modal)

        if result:  # User provided data
            # 2. Create new tag
            new_tag = TagComplex(**result)
            collection.add_tag(new_tag)
