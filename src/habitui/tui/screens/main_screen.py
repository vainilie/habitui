# ♥♥─── Main Screen ──────────────────────────────────────────────────────────────
from __future__ import annotations

from typing import TYPE_CHECKING

from textual import on
from textual.screen import Screen
from textual.binding import Binding
from textual.widgets import Label, Footer, Header, TabPane, TabbedContent
from textual.reactive import reactive
from textual.containers import Vertical, Horizontal

from habitui.tui.main import TextualLogConsole
from habitui.tui.main.api_handler import PendingCalls, SuccessfulCalls

from .tag_tab import TagsTab
from .task_tab import TasksTab
from .inbox_tab import InboxTab
from .party_tab import PartyTab
from .profile_tab import ProfileTab
from .challenge_tab import ChallengesTab


if TYPE_CHECKING:
    from textual.app import ComposeResult

    from habitui.tui.main_app import HabiTUI


# ─── Main Screen Definition ────────────────────────────────────────────────────


class MainScreen(Screen):
    """Main screen of the Habitica TUI application, featuring tabbed content."""

    BINDINGS = [
        Binding("ctrl+l", "toggle_log", "Toggle Log"),
        Binding("?", "show_help", "Help"),
    ]
    pending_op: reactive[int] = reactive(0, recompose=True)
    success_op: reactive[int] = reactive(0, recompose=True)

    def __init__(self) -> None:
        super().__init__()
        self.app: HabiTUI
        self.show_sidebar: bool = False
        self.loaded_tabs = set()

    def compose(self) -> ComposeResult:
        """Composes the main layout of the screen."""
        yield Header(show_clock=True)

        yield Label(
            f"API Calls: {self.success_op}/{self.pending_op}",
            id="pending-op-label",
        )
        with Horizontal(id="content-area"):
            with (
                Vertical(id="main-container"),
                TabbedContent(initial="profile"),
            ):
                with TabPane("Profile", id="profile"):
                    yield ProfileTab()
                with TabPane("Party", id="party"):
                    yield PartyTab()
                with TabPane("Tags", id="tags"):
                    yield TagsTab()
                with TabPane("Inbox", id="inbox"):
                    yield InboxTab()
                with TabPane("Challenges", id="challenges"):
                    yield ChallengesTab()
                with TabPane("Config", id="config"):
                    pass
                with TabPane("Tasks", id="tasks"):
                    yield TasksTab()
            with Vertical(id="sidebar", disabled=True):
                yield TextualLogConsole(id="log-console")

        yield Footer()

    @on(PendingCalls)
    def update_pending_op(self, event: PendingCalls) -> None:
        """Update the pending operations count from the API handler."""
        self.pending_op = event.pending
        self.app.logger.info(f"Received PendingCalls: {event.pending} operations")

    @on(SuccessfulCalls)
    def handle_successful_calls(self, event: SuccessfulCalls) -> None:
        """Handle completion of API batch operations."""
        # Ahora tienes acceso a ambos valores
        success_count = event.success_count
        total = event.total

        # Por ejemplo, podrías resetear pending_op o mostrar un resumen
        self.pending_op = total  # O lo que sea apropiado
        self.success_op = success_count

        self.app.logger.info(
            f"Batch completed: {success_count}/{total} successful operations",
        )

        # Tal vez actualizar algún indicador visual
        if success_count == total:
            self.notify(
                "All operations completed successfully!",
                severity="information",
            )
        else:
            self.notify(
                f"Completed with {total - success_count} failures",
                severity="warning",
            )

    def action_toggle_log(self) -> None:
        """Toggles the visibility of the log sidebar."""
        self.show_sidebar = not self.show_sidebar
        sidebar = self.query_one("#sidebar")
        main_container = self.query_one("#main-container")

        if self.show_sidebar:
            sidebar.add_class("visible")
            main_container.add_class("with-sidebar")
            self.app.logger.info("Log sidebar shown")

        else:
            sidebar.remove_class("visible")
            main_container.remove_class("with-sidebar")
            self.app.logger.info("Log sidebar hidden")

    async def action_refresh_quick(self) -> None:
        """Perform a quick data refresh (F5)."""
