# ♥♥─── Main App ─────────────────────────────────────────────────────────────────
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.binding import Binding
from textual.widgets import Static, LoadingIndicator
from textual.containers import Vertical

from art import text2art

from habitui.custom_logger import get_logger
from habitui.core.services.data_vault import DataVault

from .main.theming import TextualThemeManager
from .main.rich_log import LoggingMixin, TextualLogConsole
from .screens.main_screen import MainScreen


class LoadingScreen(Screen):
    def __init__(self) -> None:
        super().__init__()
        self.app: HabiTUI

    def compose(self) -> ComposeResult:
        vertical = Vertical(id="home-screen")
        with vertical:
            ascii_art = text2art("habiTUI", font="doom")
            yield Static(ascii_art, id="name-banner")  # type: ignore
            yield LoadingIndicator(id="main-loading")
            yield TextualLogConsole(
                classes="console",
                id="loading-console",
                max_lines=20,
            )

    def on_mount(self) -> None:
        initial_log_console = self.query_one(TextualLogConsole)
        self.app.setup_logging_widget(initial_log_console)
        self.app.logger.info("Starting HabiTUI...")


class HabiTUI(LoggingMixin, App):
    BINDINGS = [Binding("q", "quit", "Quit", priority=True)]
    CSS_PATH = "habitui.tcss"
    SCREENS = {"loading": LoadingScreen, "main": MainScreen}

    def __init__(self) -> None:
        super().__init__()
        self.logger = get_logger()
        self.theme_manager: TextualThemeManager = TextualThemeManager(self)
        self.vault: DataVault | None = None

    async def on_mount(self) -> None:
        self.title = "HabiTUI"
        self.theme = "rose_pine"
        self.push_screen("loading")

    async def on_ready(self) -> None:
        try:
            self.logger.info("Starting vault load...")
            self.vault = DataVault()
            await self.vault.get_data(force=False, debug=True, mode="smart")
            self.logger.info("Vault loaded successfully.")
            self.logger.info("Transitioning to MainScreen...")
            self.pop_screen()
            self.push_screen("main")

        except Exception as e:
            msg = f"Error during data loading: {e}"
            self.logger.exception(msg)
            self.logger.exception("Failed to load vault. Staying on loading screen.")


if __name__ == "__main__":
    app = HabiTUI()
    app.run()
