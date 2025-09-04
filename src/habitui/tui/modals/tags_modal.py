# ♥♥─── Tag Modal Builders Using Generic Base Classes ─────────────────────
from __future__ import annotations

from typing import Any

from habitui.ui import icons
from habitui.core.models.tag_model import TagComplex
from habitui.tui.generic.edit_modal import FieldType, FormField, GenericEditModal
from habitui.tui.generic.confirm_modal import GenericConfirmModal


# ─── Tag Confirmation Modals ───────────────────────────────────────────────────
def create_tag_delete_modal(tag: TagComplex) -> GenericConfirmModal:
    """Create a confirmation modal for tag deletion."""
    question = f"Are you sure you want to delete the tag '{tag.name}'?"
    confirm_variant = "warning"
    icon = icons.QUESTION_CIRCLE
    return GenericConfirmModal(question=question, title="Delete Tag", confirm_text="Delete", cancel_text="Cancel", confirm_variant=confirm_variant, icon=icon)


def create_tag_changes_confirm_modal(tag_name: str, changes: dict[str, Any]) -> GenericConfirmModal:
    """Create a confirmation modal for tag changes."""
    return GenericConfirmModal(question=f"Save changes to tag '{tag_name}'?", changes=changes, title="Confirm Tag Changes", changes_formatter=_format_tag_changes, icon=icons.EDIT)


def _format_tag_changes(changes: dict[str, Any]) -> list[tuple[str, str]]:
    formatted = []
    for key, value in changes.items():
        if key == "name":
            formatted.append(("Name", value))
    return formatted


# ─── Tag Edit Modals ───────────────────────────────────────────────────────────
def create_tag_edit_modal(tag: TagComplex) -> GenericEditModal:
    """Create an edit modal for an existing tag."""
    fields = [FormField(id="name", label="Tag Name", field_type=FieldType.TEXT, placeholder="Enter tag name", required=True)]
    original_data = {"name": tag.name}
    return GenericEditModal(title=f"Edit Tag: {tag.name}", fields=fields, original_data=original_data, icon=icons.EDIT, auto_focus="name")


def create_tag_create_modal() -> GenericEditModal:
    """Create a modal for creating a new tag."""
    fields = [FormField(id="name", label="Tag Name", field_type=FieldType.TEXT, placeholder="Enter tag name", required=True)]
    title = "Create New Tag"
    return GenericEditModal(title=title, fields=fields, save_text="Create", icon=icons.PLUS, auto_focus="name", track_changes=False)


# ─── Batch Operations Modals ───────────────────────────────────────────────────
def create_batch_tag_delete_modal(tag_list: list[TagComplex], tag_uses: dict) -> GenericConfirmModal:
    """Create confirmation modal for batch tag deletion."""
    tag_list_render = [f"• {tag.name} ({tag_uses.get(tag.id, 0)} tasks affected)\n" for tag in tag_list]
    return GenericConfirmModal(question=f"Are you sure you want to delete {len(tag_list)} selected tags?", title="Batch Delete Tags", confirm_text=f"Delete {len(tag_list)} Tags", cancel_text="Cancel", confirm_variant="error", icon=icons.WARNING, custom_content=tag_list_render)


def create_reorder_confirm_modal() -> GenericConfirmModal:
    """Create confirmation modal for tag reordering."""
    return GenericConfirmModal(question="Apply new order to all tags?", title="Confirm Reorder", confirm_text="Apply Order", cancel_text="Cancel", confirm_variant="success", icon=icons.SORT)
