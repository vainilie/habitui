from __future__ import annotations

from typing import TYPE_CHECKING, Any
from itertools import starmap

from rich.table import Table

from textual import on, work
from textual.app import ComposeResult
from textual.screen import Screen, ModalScreen
from textual.binding import Binding
from textual.message import Message
from textual.widgets import (
    Input,
    Label,
    Button,
    ListItem,
    ListView,
    Markdown,
    OptionList,
)
from textual.reactive import reactive
from textual.containers import Vertical, Container, Horizontal, VerticalScroll
from textual.widgets.option_list import Option

from habitui.ui import icons
from habitui.utils import DateTimeHandler
from habitui.tui.generic import BaseTab
from habitui.custom_logger import log


if TYPE_CHECKING:
    from textual.app import ComposeResult

    from habitui.core.models import UserMessage
    from habitui.tui.main_app import HabiTUI


# ─── Custom Messages ───────────────────────────────────────────────────────────


class InboxNeedsRefresh(Message):
    """Posted when the inbox data needs to be reloaded."""


# ─── UI Components ─────────────────────────────────────────────────────────────


class MessageInputWidget(Container):
    """Reusable widget for message input."""

    def compose(self) -> ComposeResult:
        """Compose the input widget."""
        yield Input(
            placeholder="Write your message...",
            id="message-input",
            classes="message-input",
        )

    def get_message_text(self) -> str:
        """Get the trimmed text from the input."""
        input_widget = self.query_one("#message-input", Input)

        return input_widget.value.strip()

    def clear_input(self) -> None:
        """Clear the input field."""
        input_widget = self.query_one("#message-input", Input)
        input_widget.value = ""


class ConversationHeaderWidget(Container):
    """Widget for conversation headers."""

    def __init__(self, sender_name: str, sender_username: str):
        """Initialize the conversation header.

        :param sender_name: Display name of the sender
        :param sender_username: Username of the sender
        """
        super().__init__()
        self.sender_name = sender_name
        self.sender_username = sender_username

    def compose(self) -> ComposeResult:
        """Compose the header label."""
        yield Label(
            f"{icons.USER} {self.sender_name} (@{self.sender_username})",
            classes="conversation-header",
            id="conversation-header",
        )


class MessageListWidget(VerticalScroll):
    """Widget to display a list of messages."""

    def __init__(self, messages: list[UserMessage]):
        """Initialize the message list.

        :param messages: A list of UserMessage objects
        """
        super().__init__(id="messages-scroll", classes="messages-container")
        self.messages = messages

    def compose(self) -> ComposeResult:
        """Compose the list of messages."""
        sorted_messages = sorted(
            self.messages,
            key=lambda m: m.timestamp,
            reverse=True,
        )
        message_items = [self._create_message_item(msg) for msg in sorted_messages]

        yield ListView(*message_items, id="messages-list")

    def _create_message_item(self, message: UserMessage) -> ListItem:
        """Create a visual list item for a UserMessage.

        :param message: The UserMessage object
        :returns: A configured ListItem widget
        """
        msg_item = ListItem(
            Markdown(message.text),
            classes="my-message" if message.by_me else "other-message",
            id=f"message-{message.id}",
        )
        time_diff = DateTimeHandler(
            timestamp=message.timestamp,
        ).format_time_difference()
        msg_item.border_subtitle = f"{icons.CLOCK_O} {time_diff}"

        return msg_item


# ─── Modal Screens ─────────────────────────────────────────────────────────────


class ConfirmDeleteScreen(Screen):
    """Modal screen to confirm message deletion."""

    def __init__(self, message_id: str):
        """Initialize the confirmation screen.

        :param message_id: The ID of the message to be deleted
        """
        super().__init__()
        self.message_id = message_id

    def compose(self) -> ComposeResult:
        """Compose the confirmation dialog."""
        with Container(classes="input-dialog"):
            confirm_screen = Vertical()
            confirm_screen.border_title = f"{icons.QUESTION} Confirm Deletion"

            with confirm_screen:
                yield Label("Are you sure you want to delete this message?")
                yield Label("This action cannot be undone.", classes="warning-text")

                with Horizontal(classes="modal-buttons"):
                    yield Button("Cancel", id="cancel", variant="default")
                    yield Button("Delete", id="confirm", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "confirm":
            self.dismiss(True)
        else:
            self.dismiss(False)


class MessageDetailScreen(ModalScreen):
    """Screen for viewing a full conversation."""

    BINDINGS = [
        Binding("d", "delete_message", "Delete"),
        Binding("escape", "back_to_conversations", "Back"),
    ]

    def __init__(self, conversation_data: dict[str, Any]):
        """Initialize the detail screen.

        :param conversation_data: Dictionary containing conversation details
        """
        super().__init__()
        self.conversation_data = conversation_data
        self.selected_message_id: str | None = None
        self.app: HabiTUI

    def compose(self) -> ComposeResult:
        """Compose the conversation view."""
        sender_name = self.conversation_data.get("sender_name", "(Unknown)")
        sender_username = self.conversation_data.get("sender_username", "(Unknown)")
        messages = self.conversation_data.get("messages", [])

        yield ConversationHeaderWidget(sender_name, sender_username)
        yield MessageListWidget(messages)
        yield MessageInputWidget()

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle message selection."""
        if (
            event.list_view.id == "messages-list"
            and event.item
            and event.item.id
            and event.item.id.startswith("message-")
        ):
            self.selected_message_id = event.item.id.replace("message-", "")
            log.info(f"Message selected: {self.selected_message_id}")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle new message submission."""
        if event.input.id == "message-input":
            await self._send_message()

    async def _send_message(self) -> None:
        """Send a new private message."""
        message_input = self.query_one(MessageInputWidget)
        content = message_input.get_message_text()

        if not content:
            self.notify(f"{icons.WARNING} Message cannot be empty", severity="warning")

            return

        message_input.clear_input()

        try:
            success = self.app.habitica_api.send_private_message(
                recipient_user_id=self.conversation_data["uuid"],
                message_content=content,
            )

            if success:
                self.notify(f"{icons.CHECK} Message sent!", severity="information")
                self.post_message(InboxNeedsRefresh())
            else:
                self.notify(f"{icons.ERROR} Error sending message", severity="error")

        except Exception as e:
            log.error(f"Error sending message: {e}")
            self.notify(f"{icons.ERROR} Error sending message: {e}", severity="error")

    @work
    async def _confirm_delete_message(self) -> None:
        """Confirm and delete the selected message."""
        if not self.selected_message_id:
            return

        confirm_screen = ConfirmDeleteScreen(self.selected_message_id)
        confirmed = await self.app.push_screen(confirm_screen, wait_for_dismiss=True)

        if confirmed and self.selected_message_id:
            try:
                success = self.app.habitica_api.delete_private_message(
                    self.selected_message_id,
                )

                if success:
                    self.notify(
                        f"{icons.CHECK} Message deleted!",
                        severity="information",
                    )
                    self.post_message(InboxNeedsRefresh())

                else:
                    self.notify(
                        f"{icons.ERROR} Error deleting message",
                        severity="error",
                    )

            except Exception as e:
                log.error(f"Error deleting message: {e}")
                self.notify(
                    f"{icons.ERROR} Error deleting message: {e}",
                    severity="error",
                )

    def action_delete_message(self) -> None:
        """Action to initiate message deletion."""
        if not self.selected_message_id:
            self.notify(f"{icons.WARNING} Select a message first", severity="warning")

            return

        self._confirm_delete_message()

    def action_back_to_conversations(self) -> None:
        """Dismiss the screen and return to the conversation list."""
        self.dismiss()


# ─── Main Tab ──────────────────────────────────────────────────────────────────


class InboxTab(Vertical, BaseTab):
    """Main tab for private message management."""

    BINDINGS = [
        Binding("r", "refresh_data", "Refresh"),
    ]

    conversations: reactive[dict[str, Any]] = reactive(dict, recompose=True)

    def __init__(self) -> None:
        """Initialize the Inbox tab."""
        super().__init__()
        self.app: HabiTUI
        self.conversations = self.vault.user.get_inbox_by_senders()
        log.info("InboxTab: initialized")

    def get_conversation(self, conversation_id: str) -> dict[str, Any] | None:
        """Get a specific conversation by its ID.

        :param conversation_id: The UUID of the conversation
        :returns: The conversation data dictionary or None
        """
        return self.conversations.get(conversation_id)

    def format_conversation_for_list(self, uuid: str, conv_data: dict) -> Option:
        """Format conversation data for display in an OptionList.

        :param uuid: The conversation UUID
        :param conv_data: The conversation data dictionary
        :returns: A configured Option widget
        """
        grid = Table.grid(expand=True, padding=(0, 1))
        grid.add_column(ratio=3)
        grid.add_column(ratio=1, justify="right")

        sender_name = conv_data.get("sender_name", "(Unknown)")
        sender_username = conv_data.get("sender_username", "(Unknown)")
        last_message = conv_data.get("last_by_me", "")

        grid.add_row(f"[b]{sender_name}[/b]", f"[dim]{sender_username}[/dim]")

        last_message_preview = (
            "You: message sent" if conv_data.get("last_by_me") else last_message
        )
        time_formatted = DateTimeHandler(
            timestamp=conv_data.get("last_time"),
        ).format_with_diff()
        grid.add_row(f"[dim]{last_message_preview}[/]", f"[dim]{time_formatted}[/dim]")

        return Option(grid, id=uuid)

    def compose(self) -> ComposeResult:
        """Compose the main inbox UI."""
        yield Label(f"{icons.INBOX} Private Messages", classes="tab-title")

        if not self.conversations:
            yield Label("No conversations yet", classes="center-text empty-state")

            return

        conversation_options = list(
            starmap(self.format_conversation_for_list, self.conversations.items()),
        )

        yield OptionList(
            *conversation_options,
            id="conversations_list",
            classes="select-line",
        )

    async def on_option_list_option_selected(
        self,
        event: OptionList.OptionSelected,
    ) -> None:
        """Handle conversation selection."""
        if event.option_list.id == "conversations_list":
            conversation_data = self.get_conversation(str(event.option.id))

            if conversation_data:
                detail_screen = MessageDetailScreen(conversation_data)
                await self.app.push_screen(detail_screen)
            else:
                self.notify(
                    f"{icons.ERROR} Conversation not found",
                    severity="error",
                )

    @work
    async def refresh_data(self) -> None:
        """Update the inbox data from the vault."""
        log.info("InboxTab: refreshing data")
        try:
            self.conversations = self.vault.user.get_inbox_by_senders()
            self.mutate_reactive(InboxTab.conversations)
            self.notify(
                f"{icons.CHECK} Inbox updated successfully!",
                title="Data Updated",
                severity="information",
            )
        except Exception as e:
            log.error(f"InboxTab: Error refreshing data: {e}")
            self.notify(
                f"{icons.ERROR} Error updating inbox: {e}",
                title="Error",
                severity="error",
            )

    @on(InboxNeedsRefresh)
    def handle_inbox_refresh(self) -> None:
        """Catches the refresh message and triggers a data update."""
        self.refresh_data()

    def action_refresh_data(self) -> None:
        """Action to trigger a data refresh."""
        self.refresh_data()
