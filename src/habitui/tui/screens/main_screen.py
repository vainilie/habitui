# ♥♥─── Main Screen ──────────────────────────────────────────────────────────────
from __future__ import annotations

from typing import TYPE_CHECKING

from textual.screen import Screen
from textual.binding import Binding
from textual.widgets import Footer, Header, TabPane, TabbedContent
from textual.containers import Vertical, Horizontal

from habitui.tui.main.rich_log import TextualLogConsole

from .profile_tab import ProfileTab


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

    def __init__(self) -> None:
        super().__init__()
        self.app: HabiTUI
        self.show_sidebar: bool = False
        self.loaded_tabs = set()

    def compose(self) -> ComposeResult:
        """Composes the main layout of the screen."""
        yield Header(show_clock=True)
        with Horizontal(id="content-area"):
            with (
                Vertical(id="main-container"),
                TabbedContent(initial="profile"),
            ):
                with TabPane("Profile", id="profile"):
                    yield ProfileTab()
                with TabPane("Party", id="party"):
                    pass
                with TabPane("Tags", id="tags"):
                    pass
                with TabPane("Inbox", id="inbox"):
                    pass
                with TabPane("Challenges", id="challenges"):
                    pass
                with TabPane("Config", id="config"):
                    pass
                with TabPane("Tasks", id="tasks"):
                    pass
            with Vertical(id="sidebar", disabled=True):
                yield TextualLogConsole(id="log-console")

        yield Footer()

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
