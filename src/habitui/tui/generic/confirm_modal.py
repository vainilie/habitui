# ♥♥─── Generic Confirmation Modal and Formatters ───────────────────────────
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from textual import on
from textual.screen import ModalScreen
from textual.binding import Binding
from textual.widgets import Label, Button, Static
from textual.containers import Vertical, Container, Horizontal

from habitui.ui import icons


if TYPE_CHECKING:
    from collections.abc import Callable

    from textual.app import ComposeResult


class GenericConfirmModal(ModalScreen):
    """A reusable confirmation modal that can display changes and custom content."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False),
        Binding("enter", "confirm", "Confirm", show=False),
        Binding("y", "confirm", "Yes", show=False),
        Binding("n", "cancel", "No", show=False),
    ]

    def __init__(  # noqa: PLR0913, PLR0917
        self,
        question: str,
        changes: dict[str, Any] | None = None,
        title: str = "Confirm Changes",
        changes_formatter: Callable[[dict[str, Any]], list[tuple[str, str]]] | None = None,
        confirm_text: str = "Confirm",
        cancel_text: str = "Cancel",
        confirm_variant: str = "success",
        cancel_variant: str = "default",
        custom_content: list | None = None,
        bindings_enabled: bool = True,
        icon: str = icons.QUESTION_CIRCLE,
    ) -> None:
        """Initialize the GenericConfirmModal.

        :param question: Main question/description text
        :param changes: Dictionary of changes to display
        :param title: Modal title (default: "Confirm Changes")
        :param changes_formatter: Optional custom formatter for changes display
        :param confirm_text: Text for confirm button (default: "Confirm")
        :param cancel_text: Text for cancel button (default: "Cancel")
        :param confirm_variant: Button variant for confirm button (default: "success")
        :param cancel_variant: Button variant for cancel button (default: "default")
        :param custom_content: Optional list of additional widgets to display
        :param bindings_enabled: Whether to enable keyboard bindings (default: True)
        :param icon: Icon to display in the modal title (default: question mark icon)
        """
        super().__init__()
        self.question = question
        self.changes = changes or {}
        self.modal_title = title
        self.changes_formatter = changes_formatter or self._default_changes_formatter
        self.confirm_text = confirm_text
        self.cancel_text = cancel_text
        self.confirm_variant = confirm_variant
        self.cancel_variant = cancel_variant
        self.custom_content = custom_content or []
        self.bindings_enabled = bindings_enabled
        self.icon = icon

    @staticmethod
    def _default_changes_formatter(changes: dict[str, Any]) -> list[tuple[str, str]]:
        formatted_changes = []
        for key, value in changes.items():
            display_key = key.replace("_", " ").title()
            if isinstance(value, str):
                display_value = f"Updated ({len(value)} characters)" if len(value) > 50 else value
            elif isinstance(value, (int, float)):
                display_value = f"{value}:00" if key == "day_start" else str(value)
            elif isinstance(value, bool):
                display_value = icons.CHECK_MARK if value else icons.MULTIPLICATION_X
            elif isinstance(value, list):
                display_value = f"{len(value)} items"
            elif isinstance(value, dict):
                display_value = f"{len(value)} properties"
            else:
                display_value = str(value)
            formatted_changes.append((display_key, display_value))
        return formatted_changes

    def compose(self) -> ComposeResult:
        """Create child widgets for the modal."""
        with Container(classes="input-confirm dialog"):
            confirm_screen = Vertical(classes="input-confirm-body dialog-content")
            confirm_screen.border_title = f"{self.icon} {self.modal_title}"
            with confirm_screen:
                yield Label(self.question, classes="changes-question")
                if self.changes:
                    with Vertical(classes="changes-list"):
                        formatted_changes = self.changes_formatter(self.changes)
                        for label, value in formatted_changes:
                            with Horizontal(classes="changes-row"):
                                yield Label(f"• {label}: ", classes="changes-label")
                                yield Label(value, classes="changes-value")
                for x in self.custom_content:
                    yield Label(x)
                with Horizontal(classes="modal-buttons"):
                    yield Button(self.cancel_text, id="cancel", variant=self.cancel_variant, flat=True)  # type: ignore
                    yield Button(self.confirm_text, id="confirm", variant=self.confirm_variant, flat=True)  # type: ignore

    @on(Button.Pressed, "#cancel")
    def cancel_action(self) -> None:
        """Dismiss the modal with a False result when the cancel button is pressed."""
        self.dismiss(False)

    @on(Button.Pressed, "#confirm")
    def confirm_action(self) -> None:
        """Dismiss the modal with a True result when the confirm button is pressed."""
        self.dismiss(True)

    def action_cancel(self) -> None:
        """Handle cancel binding."""
        if self.bindings_enabled:
            self.dismiss(False)

    def action_confirm(self) -> None:
        """Handle confirm binding."""
        if self.bindings_enabled:
            self.dismiss(True)


# ─── Custom Formatters ─────────────────────────────────────────────────────────
class HabiticaChangesFormatter:
    """Specialized formatter for Habitica changes."""

    @staticmethod
    def format_changes(changes: dict[str, Any]) -> list[tuple[str, str]]:
        """Format Habitica-specific changes for display."""
        formatted = []
        if changes.get("name"):
            formatted.append(("Name", changes["name"]))
        if "day_start" in changes:
            formatted.append(("Day Start", f"{changes['day_start']}:00"))
        if changes.get("bio"):
            formatted.append(("Bio", f"Updated ({len(changes['bio'])} characters)"))
        return formatted


# ─── Usage Examples ────────────────────────────────────────────────────────────
def show_habitica_confirm(changes: dict) -> GenericConfirmModal:
    """Show a confirmation modal for Habitica changes."""
    return GenericConfirmModal(
        question="The following changes will be sent to Habitica:",
        changes=changes,
        changes_formatter=HabiticaChangesFormatter.format_changes,
        title="Confirm Changes",
        icon=icons.QUESTION_MARK,
    )


def show_delete_confirm(item_name: str) -> GenericConfirmModal:
    """Show a confirmation modal for item deletion."""
    return GenericConfirmModal(
        question=f"Are you sure you want to delete '{item_name}'? This action cannot be undone.",
        title="Confirm Deletion",
        confirm_text="Delete",
        cancel_text="Keep",
        confirm_variant="error",
        icon=icons.WARNING,
    )


def show_exit_confirm(unsaved_changes: int) -> GenericConfirmModal:
    """Show a confirmation modal for exiting with unsaved changes."""
    return GenericConfirmModal(
        question=f"You have {unsaved_changes} unsaved changes. Do you want to exit without saving?",
        title="Unsaved Changes",
        confirm_text="Exit Anyway",
        cancel_text="Stay",
        confirm_variant="warning",
        icon=icons.SAVE,
    )


def show_custom_confirm() -> GenericConfirmModal:
    """Show a confirmation modal with custom content."""
    custom_widgets = [
        Static(f"{icons.WARNING} This will affect multiple users", classes="warning-text"),
        Static(f"{icons.BAR_CHART} Estimated processing time: 5 minutes", classes="info-text"),
    ]
    return GenericConfirmModal(question="Do you want to proceed with the bulk operation?", title="Bulk Operation", custom_content=custom_widgets, icon=icons.GEAR)


def custom_formatter(changes: dict[str, Any]) -> list[tuple[str, str]]:
    """Add emojis and special formatting."""
    formatted = []
    for key, value in changes.items():
        if key == "status":
            emoji = icons.CHECK_MARK if value == "active" else icons.MULTIPLICATION_X
            formatted.append((f"{emoji} Status", value.title()))
        elif key == "priority":
            emoji = icons.RED_CIRCLE if value == "high" else icons.YELLOW_CIRCLE if value == "medium" else icons.GREEN_CIRCLE
            formatted.append((f"{emoji} Priority", value.title()))
        else:
            formatted.append((key.replace("_", " ").title(), str(value)))
    return formatted
