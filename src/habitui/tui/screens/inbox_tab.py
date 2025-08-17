"""
Refactorización del sistema de mensajes privados con mejor arquitectura
Separación de responsabilidades y código más limpio y mantenible
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from itertools import starmap

from rich.table import Table

from textual import work
from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.binding import Binding
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

    from habitui.tui.main_app import HabiTUI


# ========== MODELOS DE DATOS ==========
# Los modelos UserMessage ya existen en habitui, no necesitamos duplicarlos


# ========== COMPONENTES UI ==========
class MessageInputWidget(Container):
    """Widget reutilizable para input de mensajes."""

    def compose(self) -> ComposeResult:
        yield Input(
            placeholder="Escribe tu mensaje...",
            id="message-input",
            classes="message-input",
        )

    def get_message_text(self) -> str:
        """Obtiene el texto del input."""
        input_widget = self.query_one("#message-input", Input)
        return input_widget.value.strip()

    def clear_input(self) -> None:
        """Limpia el input."""
        input_widget = self.query_one("#message-input", Input)
        input_widget.value = ""


class ConversationHeaderWidget(Container):
    """Widget para el header de conversaciones."""

    def __init__(self, sender_name: str, sender_username: str):
        super().__init__()
        self.sender_name = sender_name
        self.sender_username = sender_username

    def compose(self) -> ComposeResult:
        yield Label(
            f"{icons.USER} {self.sender_name} (@{self.sender_username})",
            classes="conversation-header",
            id="conversation-header",
        )


class MessageListWidget(VerticalScroll):
    """Widget para mostrar lista de mensajes."""

    def __init__(self, messages: list[Message]):
        super().__init__(id="messages-scroll", classes="messages-container")
        self.messages = messages

    def compose(self) -> ComposeResult:
        message_items = []
        # Ordenar por timestamp (más recientes primero)
        sorted_messages = sorted(self.messages, key=lambda m: m.timestamp, reverse=True)

        for message in sorted_messages:
            msg_item = self._create_message_item(message)
            message_items.append(msg_item)

        yield ListView(*message_items, id="messages-list")

    def _create_message_item(self, message) -> ListItem:
        """Crea un item visual para un mensaje UserMessage."""
        msg_item = ListItem(
            Markdown(message.text),
            classes="my-message" if message.by_me else "other-message",
            id=f"message-{message.id}",
        )

        # Agregar timestamp
        time_diff = DateTimeHandler(
            timestamp=message.timestamp,
        ).format_time_difference()
        msg_item.border_subtitle = f"{icons.CLOCK_O} {time_diff}"

        return msg_item


# ========== PANTALLAS MODALES ==========
class ConfirmDeleteScreen(ModalScreen):
    """Modal para confirmar eliminación de mensaje."""

    def __init__(self, message_id: str):
        super().__init__()
        self.message_id = message_id

    def compose(self) -> ComposeResult:
        with Container(classes="input-dialog"):
            confirm_screen = Vertical()
            confirm_screen.border_title = f"{icons.QUESTION} Confirmar Eliminación"

            with confirm_screen:
                yield Label("¿Estás segura de que quieres eliminar este mensaje?")
                yield Label("Esta acción no se puede deshacer.", classes="warning-text")

                with Horizontal(classes="modal-buttons"):
                    yield Button("Cancelar", id="cancel", variant="default")
                    yield Button("Eliminar", id="confirm", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm":
            self.dismiss(True)
        else:
            self.dismiss(False)


class MessageDetailScreen(ModalScreen):
    """Pantalla para ver una conversación completa."""

    BINDINGS = [
        Binding("d", "delete_message", "Eliminar"),
        Binding("escape", "back_to_conversations", "Volver"),
    ]

    def __init__(self, conversation_data: dict):
        super().__init__()
        self.conversation_data = conversation_data
        self.selected_message_id: str | None = None
        self.app: HabiTUI

    def compose(self) -> ComposeResult:
        # Header
        sender_name = self.conversation_data.get("sender_name", "(Unknown)")
        sender_username = self.conversation_data.get("sender_username", "(Unknown)")
        yield ConversationHeaderWidget(sender_name, sender_username)

        # Lista de mensajes
        messages = self.conversation_data.get("messages", [])
        yield MessageListWidget(messages)

        # Input para nuevo mensaje
        yield MessageInputWidget()

    async def on_list_view_selected(self, event) -> None:
        """Maneja selección de mensaje."""
        if (
            event.list_view.id == "messages-list"
            and event.item.id
            and event.item.id.startswith("message-")
        ):
            self.selected_message_id = event.item.id.replace("message-", "")
            log.info(f"Mensaje seleccionado: {self.selected_message_id}")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Maneja envío de mensaje."""
        if event.input.id == "message-input":
            await self._send_message()

    async def _send_message(self) -> None:
        """Envía un nuevo mensaje."""
        message_input = self.query_one(MessageInputWidget)
        content = message_input.get_message_text()

        if not content:
            self.notify(
                f"{icons.WARNING} El mensaje no puede estar vacío",
                severity="warning",
            )
            return

        message_input.clear_input()

        try:
            success = self.app.habitica_api.send_private_message(
                recipient_user_id=self.conversation_data["uuid"],
                message_content=content,
            )

            if success:
                self.notify(f"{icons.CHECK} Mensaje enviado!", severity="information")
                # Aquí recargarías los datos
            else:
                self.notify(f"{icons.ERROR} Error al enviar mensaje", severity="error")
        except Exception as e:
            log.error(f"Error enviando mensaje: {e}")
            self.notify(f"{icons.ERROR} Error al enviar mensaje: {e}", severity="error")

    def action_delete_message(self) -> None:
        """Acción para eliminar mensaje."""
        if not self.selected_message_id:
            self.notify(
                f"{icons.WARNING} Selecciona un mensaje primero",
                severity="warning",
            )
            return

        self._confirm_delete_message()

    @work
    async def _confirm_delete_message(self) -> None:
        """Confirma y elimina mensaje."""
        confirm_screen = ConfirmDeleteScreen(self.selected_message_id)
        confirmed = await self.app.push_screen(confirm_screen, wait_for_dismiss=True)

        if confirmed and self.selected_message_id:
            try:
                success = self.app.habitica_api.delete_private_message(
                    self.selected_message_id,
                )

                if success:
                    self.notify(
                        f"{icons.CHECK} Mensaje eliminado!",
                        severity="information",
                    )
                    # Aquí recargarías los datos
                else:
                    self.notify(
                        f"{icons.ERROR} Error al eliminar mensaje",
                        severity="error",
                    )
            except Exception as e:
                log.error(f"Error eliminando mensaje: {e}")
                self.notify(
                    f"{icons.ERROR} Error al eliminar mensaje: {e}",
                    severity="error",
                )

    def action_back_to_conversations(self) -> None:
        """Vuelve a la lista de conversaciones."""
        self.dismiss()


# ========== TAB PRINCIPAL ==========
class InboxTab(Vertical, BaseTab):
    """Tab principal para gestión de mensajes privados."""

    BINDINGS = [
        Binding("r", "refresh_data", "Actualizar"),
    ]

    conversations: reactive[dict[str, Any]] = reactive(dict, recompose=True)

    def __init__(self):
        super().__init__()
        self.app: HabiTUI
        log.info("InboxTab: inicializado")
        self.conversations = self.vault.user.get_inbox_by_senders()

    def get_conversation(self, conversation_id: str) -> Any | None:
        """Obtiene una conversación específica."""
        return self.conversations.get(conversation_id)

    def format_conversation_for_list(self, uuid: str, conv_data: dict) -> Option:
        """Formatea una conversación para mostrar en lista."""
        grid = Table.grid(expand=True, padding=(0, 1))
        grid.add_column(ratio=3)
        grid.add_column(ratio=1, justify="right")

        sender_name = conv_data.get("sender_name", "(Unknown)")
        sender_username = conv_data.get("sender_username", "(Unknown)")
        last_message = conv_data.get("last_by_me", "")

        # Primera fila: nombre y username
        grid.add_row(f"[b]{sender_name}[/b]", f"[dim]{sender_username}[/dim]")

        # Segunda fila: último mensaje y tiempo
        last_message_preview = (
            "Tú: mensaje enviado" if conv_data.get("last_by_me") else last_message
        )
        time_formatted = DateTimeHandler(
            timestamp=conv_data.get("last_time"),
        ).format_with_diff()
        grid.add_row(f"[dim]{last_message_preview}[/]", f"[dim]{time_formatted}[/dim]")

        return Option(grid, id=uuid)

    def compose(self) -> ComposeResult:
        """Compone la UI principal."""
        yield Label(f"{icons.INBOX} Mensajes Privados", classes="tab-title")

        if not self.conversations:
            yield Label("No hay conversaciones aún", classes="center-text empty-state")
            return

        # Lista de conversaciones
        conversation_options = list(
            starmap(
                self.format_conversation_for_list,
                self.conversations.items(),
            ),
        )

        yield OptionList(
            *conversation_options,
            id="conversations_list",
            classes="select-line",
        )

    async def on_option_list_option_selected(self, event) -> None:
        """Maneja selección de conversación."""
        if event.option_list.id == "conversations_list":
            conversation_data = self.get_conversation(event.option.id)

            if conversation_data:
                detail_screen = MessageDetailScreen(conversation_data)
                await self.app.push_screen(detail_screen)
            else:
                self.notify(
                    f"{icons.ERROR} Conversación no encontrada",
                    severity="error",
                )

    async def refresh_data(self) -> None:
        """Actualiza los datos del inbox."""
        log.info("InboxTab: actualizando datos")
        try:
            # Cargar conversaciones
            self.conversations = self.vault.user.get_inbox_by_senders()
            self.mutate_reactive(InboxTab.conversations)

            self.notify(
                f"{icons.CHECK} Inbox actualizado correctamente!",
                title="Datos Actualizados",
                severity="information",
            )
        except Exception as e:
            log.error(f"InboxTab: Error actualizando datos: {e}")
            self.notify(
                f"{icons.ERROR} Error al actualizar inbox: {e}",
                title="Error",
                severity="error",
            )

    def action_refresh_data(self) -> None:
        """Acción para actualizar datos."""
        self.run_worker(self.refresh_data())
