# ♥♥─── Generic Edit Modal for Textual Applications ──────────────────────
from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any
from dataclasses import dataclass
from collections.abc import Callable

from textual import on
from textual.screen import ModalScreen
from textual.binding import Binding
from textual.widgets import Input, Label, Button, Select, Static, Switch, ListItem, ListView, TextArea
from textual.containers import Vertical, Container, Horizontal

from habitui.ui import icons
from habitui.custom_logger import log
from habitui.core.models.content_model import SpellItem


if TYPE_CHECKING:
    from textual.app import ComposeResult


# ─── Enums ─────────────────────────────────────────────────────────────────────
class FieldType(Enum):
    """Defines the types of form fields available."""

    TEXT = "text"
    INTEGER = "integer"
    TEXTAREA = "textarea"
    PASSWORD = "password"
    EMAIL = "email"
    SELECT = "select"
    SWITCH = "switch"
    STATIC = "static"
    OPTION_LIST = "option_list"


# ─── Data Classes ──────────────────────────────────────────────────────────────
@dataclass
class FormField:
    """Configuration for a single form field.

    :param id: Unique identifier for the field.
    :param label: Text label displayed next to the field.
    :param field_type: The type of input widget to use.
    :param default_value: Default value for the field.
    :param placeholder: Placeholder text for input fields.
    :param options: List of (value, label) tuples for select fields.
    :param option_items: List of objects with display properties for option_list fields.
    :param option_formatter: Function to format option_list items (obj) -> (title, subtitle, description).
    :param classes: CSS classes to apply to the widget.
    :param required: True if the field is mandatory.
    :param validation: Optional custom validation function.
    :param min_value: Minimum allowed value for integer fields.
    :param max_value: Maximum allowed value for integer fields.
    :param language: Code editor language for TextArea fields (e.g., "markdown").
    :param help_text: Additional help text displayed below the field.
    """

    id: str
    label: str
    field_type: FieldType
    default_value: Any = ""
    placeholder: str = ""
    options: list[tuple[Any, str]] | None = None
    option_items: list[Any] | None = None
    option_formatter: Callable[[Any], tuple[str, str, str]] | None = None
    classes: str = ""
    required: bool = False
    validation: Callable[[Any], tuple[bool, str]] | None = None
    min_value: int | None = None
    max_value: int | None = None
    language: str = "markdown"
    help_text: str = ""


# ─── Modal Screen ──────────────────────────────────────────────────────────────
class GenericEditModal(ModalScreen):
    """A reusable modal screen for editing various types of forms.

    This modal dynamically generates form fields based on provided configurations
    and handles data collection, validation, and change tracking.
    """

    BINDINGS = [Binding("escape", "cancel", "Cancel", show=False), Binding("ctrl+s", "save", "Save", show=False)]

    def __init__(self, title: str, fields: list[FormField], original_data: dict[str, Any] | None = None, save_text: str = "Save", cancel_text: str = "Cancel", icon: str = icons.EDIT, track_changes: bool = True, auto_focus: str | None = None) -> None:  # noqa: PLR0917
        """Initialize the GenericEditModal.

        :param title: The title displayed at the top of the modal.
        :param fields: A list of `FormField` objects defining the form structure.
        :param original_data: A dictionary containing the initial values for the fields.
        :param save_text: The text displayed on the save button.
        :param cancel_text: The text displayed on the cancel button.
        :param icon: An icon string to display in the modal title.
        :param track_changes: If True, only modified fields are returned on save.
        :param auto_focus: The ID of the field to automatically focus on modal open.
        """
        super().__init__()
        self.modal_title = title
        self.fields = fields
        self.original_data = original_data or {}
        self.save_text = save_text
        self.cancel_text = cancel_text
        self.icon = icon
        self.track_changes = track_changes
        self.auto_focus = auto_focus
        self._selected_option = None

    def compose(self) -> ComposeResult:  # noqa: C901, PLR0912
        """Compose the child widgets for the modal screen."""
        with Container(classes="input-edit"):
            input_screen = Vertical(classes="input-edit-body")
            input_screen.border_title = f"{self.icon} {self.modal_title}"
            with input_screen:
                for field in self.fields:
                    # Field label
                    if field.field_type != FieldType.STATIC:
                        label_text = field.label
                        if field.required:
                            label_text += " *"
                        yield Label(label_text, classes=f"input-label {field.classes}")
                    # Field widget based on type
                    original_value = self.original_data.get(field.id, field.default_value)
                    if field.field_type == FieldType.TEXT:
                        yield Input(placeholder=field.placeholder, value=str(original_value), id=field.id, classes=f"input-line {field.classes}")
                    elif field.field_type == FieldType.INTEGER:
                        yield Input(placeholder=field.placeholder, value=str(original_value), type="integer", id=field.id, classes=f"input-line {field.classes}")
                    elif field.field_type == FieldType.PASSWORD:
                        yield Input(placeholder=field.placeholder, value=str(original_value), password=True, id=field.id, classes=f"input-line {field.classes}")
                    elif field.field_type == FieldType.EMAIL:
                        yield Input(placeholder=field.placeholder, value=str(original_value), id=field.id, classes=f"input-line {field.classes}")
                    elif field.field_type == FieldType.TEXTAREA:
                        yield TextArea.code_editor(str(original_value), language=field.language, id=field.id, classes=f"input-box {field.classes}")
                    elif field.field_type == FieldType.SELECT and field.options:
                        select_widget = Select(options=field.options, value=original_value, id=field.id, classes=f"input-select {field.classes}")
                        yield select_widget
                    elif field.field_type == FieldType.OPTION_LIST and field.option_items:
                        # Create option list with selectable items
                        option_list = ListView(classes=f"option-list {field.classes}")
                        with option_list:
                            for item in field.option_items:
                                if field.option_formatter:
                                    title, subtitle, description = field.option_formatter(item)
                                    list_item = ListItem(Label(description, classes="option-description"), classes="option-item")
                                    list_item.border_title = title
                                    list_item.border_subtitle = subtitle
                                else:
                                    list_item = ListItem(Label(str(item), classes="option-description"), classes="option-item")
                                # Store the original item data
                                list_item.data_item = item
                                yield list_item
                        yield option_list
                    elif field.field_type == FieldType.SWITCH:
                        yield Switch(value=bool(original_value), id=field.id, classes=f"input-switch {field.classes}")
                    elif field.field_type == FieldType.STATIC:
                        yield Static(field.label, classes=f"input-static {field.classes}")
                    # Help text
                    if field.help_text:
                        yield Label(field.help_text, classes="input-help")
                # Buttons
                with Horizontal(classes="modal-buttons"):
                    yield Button(self.cancel_text, id="cancel", variant="default")
                    yield Button(self.save_text, id="save", variant="success")

    def on_mount(self) -> None:
        """Focus on specified field when modal opens."""
        if self.auto_focus:
            try:
                widget = self.query_one(f"#{self.auto_focus}")
                widget.focus()
            except Exception as e:
                log.exception(e)

    @on(ListView.Highlighted)
    def option_selected(self, event: ListView.Highlighted) -> None:
        """Handle option list selection."""
        if event.list_view.classes and "option-list" in event.list_view.classes and event.item and hasattr(event.item, "data_item"):
            self._selected_option = event.item.data_item

    @staticmethod
    def _validate_field(field: FormField, value: Any) -> tuple[bool, str]:
        """Validate a single field value.

        :param field: The `FormField` configuration for the field.
        :param value: The current value of the field.
        :returns: A tuple containing a boolean (True if valid, False otherwise) and an error message string (empty if valid).
        """
        # Required validation
        if field.required and not value:
            return False, f"{field.label} is required"
        # Type-specific validation
        if field.field_type == FieldType.INTEGER:
            try:
                int_value = int(value) if value else 0
                if field.min_value is not None and int_value < field.min_value:
                    return False, f"{field.label} must be at least {field.min_value}"
                if field.max_value is not None and int_value > field.max_value:
                    return (False, f"{field.label} must be no more than {field.max_value}")
            except ValueError:
                return False, f"{field.label} must be a valid number"
        # Custom validation
        if field.validation:
            return field.validation(value)
        return True, ""

    def _collect_form_data(self) -> tuple[dict[str, Any], list[str]]:
        """Collect all form data and validate it.

        :returns: A tuple containing the collected data dictionary and a list of error messages.
        """
        data = {}
        errors = []
        for field in self.fields:
            if field.field_type == FieldType.STATIC:
                continue
            try:
                if field.field_type == FieldType.TEXTAREA:
                    widget = self.query_one(f"#{field.id}", TextArea)
                    value = widget.text
                elif field.field_type == FieldType.SWITCH:
                    widget = self.query_one(f"#{field.id}", Switch)
                    value = widget.value
                elif field.field_type == FieldType.SELECT:
                    widget = self.query_one(f"#{field.id}", Select)
                    value = widget.value
                elif field.field_type == FieldType.OPTION_LIST:
                    # For option list, return the selected item or None
                    value = self._selected_option
                else:  # Input types
                    widget = self.query_one(f"#{field.id}", Input)
                    value = widget.value
                    # Convert integer fields
                    if field.field_type == FieldType.INTEGER:
                        value = int(value) if value else 0
                # Validate field
                is_valid, error_msg = self._validate_field(field, value)
                if not is_valid:
                    errors.append(error_msg)
                data[field.id] = value
            except Exception as e:
                errors.append(f"Error reading {field.label}: {e}")
        return data, errors

    def _has_changes(self, new_data: dict[str, Any]) -> bool:
        """Check if any data has changed compared to original data.

        :param new_data: The newly collected form data.
        :returns: True if changes are detected or `track_changes` is False, False otherwise.
        """
        if not self.track_changes:
            return True
        for field_id, new_value in new_data.items():
            original_value = self.original_data.get(field_id)
            if new_value != original_value:
                return True
        return False

    @on(Button.Pressed, "#cancel")
    def cancel_edit(self) -> None:
        """Handle the cancel button press."""
        self.dismiss()

    @on(Button.Pressed, "#save")
    def save_changes(self) -> None:
        """Collect and validates form changes, then dismisses the modal."""
        data, errors = self._collect_form_data()
        if errors:
            # In a real application, you would display these errors to the user,
            # for example, using a notification or by highlighting fields.
            # For now, we simply prevent saving.
            return
        if self.track_changes:
            if not self._has_changes(data):
                self.dismiss()
                return
            # Return only changed fields
            changes = {field_id: new_value for field_id, new_value in data.items() if new_value != self.original_data.get(field_id)}
            self.dismiss(changes)
        else:
            self.dismiss(data)

    def action_cancel(self) -> None:
        self.dismiss()

    def action_save(self) -> None:
        self.save_changes()


# ─── Specialized Modal Builders ────────────────────────────────────────────────
def create_profile_edit_modal(name: str = "", bio: str = "", day_start: int = 0) -> GenericEditModal:
    """Create a pre-configured modal for editing user profile information.

    :param name: The initial name value.
    :param bio: The initial biography value.
    :param day_start: The initial day start hour value.
    :returns: An instance of `GenericEditModal` configured for profile editing.
    """
    fields = [
        FormField(id="name", label="Name:", field_type=FieldType.TEXT, placeholder="Your display name", classes="input-line"),
        FormField(id="day_start", label="Day Start Hour (0-23):", field_type=FieldType.INTEGER, placeholder="0", classes="input-line", min_value=0, max_value=23),
        FormField(id="bio", label="Bio (Markdown):", field_type=FieldType.TEXTAREA, classes="input-box"),
    ]
    original_data = {"name": name, "day_start": day_start, "bio": bio}
    return GenericEditModal(title="Edit Profile", fields=fields, original_data=original_data, icon=icons.USER, auto_focus="name")


def create_spell_selection_modal(available_spells: list[Any], user_mp: int) -> GenericEditModal:
    """Create a modal for selecting spells to cast.

    :param available_spells: List of available spell objects.
    :param user_mp: Current user MP for display.
    :returns: An instance of `GenericEditModal` configured for spell selection.
    """

    def spell_formatter(spell: SpellItem) -> tuple[str, str, str]:
        """Format spell for display in option list."""
        title = f"{icons.WAND} {spell.text}"
        subtitle = f"{icons.MANA} {spell.mana} MP {icons.TARGET} {spell.target}"
        description = spell.notes or "No description available"
        return title, subtitle, description

    fields = [
        FormField(id="spell", label="Select a spell to cast:", field_type=FieldType.OPTION_LIST, option_items=available_spells, option_formatter=spell_formatter, classes="spell-selection", required=True),
        FormField(id="current_mp_info", label=f"{icons.MANA} Current MP: {user_mp}", field_type=FieldType.STATIC, classes="mp-info"),
    ]
    return GenericEditModal(title="Cast Spell", fields=fields, icon=icons.WAND, track_changes=False, save_text="Cast", cancel_text="Cancel")


def create_task_edit_modal(title: str = "", description: str = "", priority: str = "medium") -> GenericEditModal:
    """Create a pre-configured modal for editing task details.

    :param title: The initial task title.
    :param description: The initial task description.
    :param priority: The initial task priority.
    :returns: An instance of `GenericEditModal` configured for task editing.
    """
    fields = [
        FormField(id="title", label="Task Title:", field_type=FieldType.TEXT, placeholder="Enter task title", required=True),
        FormField(id="priority", label="Priority:", field_type=FieldType.SELECT, options=[("low", "Low"), ("medium", "Medium"), ("high", "High"), ("urgent", "Urgent")]),
        FormField(id="description", label="Description:", field_type=FieldType.TEXTAREA),
        FormField(id="active", label="Active:", field_type=FieldType.SWITCH, default_value=True),
    ]
    return GenericEditModal(title="Edit Task", fields=fields, original_data={"title": title, "description": description, "priority": priority}, icon=icons.EDIT)


def create_settings_modal() -> GenericEditModal:
    """Create a pre-configured modal for application settings.

    :returns: An instance of `GenericEditModal` configured for settings.
    """
    fields = [
        FormField(id="theme", label="Theme:", field_type=FieldType.SELECT, options=[("light", "Light"), ("dark", "Dark"), ("auto", "Auto")]),
        FormField(id="notifications", label="Enable Notifications:", field_type=FieldType.SWITCH, default_value=True),
        FormField(id="api_url", label="API URL:", field_type=FieldType.TEXT, placeholder="https://habitica.com/api/v3"),
        FormField(id="info", label="Settings are saved automatically", field_type=FieldType.STATIC, classes="settings-info"),
    ]
    return GenericEditModal(title="Settings", fields=fields, icon=icons.GEAR, track_changes=False)  # Replaced emoji with icon from habitui.ui  # Return all data, not just changes
