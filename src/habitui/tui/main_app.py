# ♥♥─── Main App ─────────────────────────────────────────────────────────────────
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.binding import Binding
from textual.widgets import Static, LoadingIndicator
from textual.containers import Vertical

from art import text2art

from habitui.core.services import DataVault
from habitui.custom_logger import get_logger

from .main import LoggingMixin, QueuedAPIHandler, TextualLogConsole, TextualThemeManager
from .screens import MainScreen


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
        self.app.logging.setup_logging_widget(initial_log_console)
        self.app.logger.info("Starting HabiTUI...")


class HabiTUI(App):
    BINDINGS = [Binding("q", "quit", "Quit", priority=True)]
    CSS_PATH = "habitui.tcss"
    SCREENS = {"loading": LoadingScreen, "main": MainScreen}

    def __init__(self) -> None:
        super().__init__()
        self.logger = get_logger()
        self.theme_manager: TextualThemeManager = TextualThemeManager(self)
        self.habitica_api: QueuedAPIHandler = QueuedAPIHandler(self)
        self.vault: DataVault | None = None
        self.logging = LoggingMixin()

    async def on_mount(self) -> None:
        self.title = "HabiTUI"
        self.theme = "rose_pine"
        self.push_screen("loading")

    async def on_ready(self) -> None:
        try:
            self.logger.info("=== ON_READY START ===")
            self.logger.info(f"Screens already exist: {hasattr(self, '_screen_stack')}")
            if hasattr(self, "_screen_stack"):
                self.logger.info(
                    f"Screen stack: {[str(s) for s in self._screen_stack]}"
                )

            self.logger.info("Starting vault load...")
            self.vault = DataVault()
            self.logger.info("=== VAULT CREATED ===")

            await self.vault.get_data(force=False, debug=True, mode="smart")
            self.logger.info(
                f"=== VAULT LOADED - Tags loaded: {self.vault.tags is not None} ===",
            )

            self.logger.info("Vault loaded successfully.")
            self.logger.info("Transitioning to MainScreen...")

            self.logger.info("=== ABOUT TO POP/PUSH ===")
            self.pop_screen()
            self.push_screen("main")
            self.logger.info("=== FINISHED ON_READY ===")
        except Exception as e:
            self.logger.info(f"ERROR in on_ready: {e}")
            msg = f"Error during data loading: {e}"
            self.logger.exception(msg)
            self.logger.exception("Failed to load vault. Staying on loading screen.")


if __name__ == "__main__":
    app = HabiTUI()
    app.run()
