# ♥♥─── Main App ─────────────────────────────────────────────────────────────────
from __future__ import annotations

from time import sleep as time_sleep
from asyncio import Event, create_task, get_running_loop

from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.binding import Binding
from textual.widgets import Static, LoadingIndicator
from textual.containers import Vertical

from art import text2art

from habitui.core.client import HabiticaClient
from habitui.core.services import DataVault
from habitui.custom_logger import get_logger

from .main import LoggingMixin, TextualLogConsole, TextualThemeManager
from .screens import MainScreen


async def sleep(sleep_for: float) -> None:
    """An asyncio sleep."""
    await get_running_loop().run_in_executor(None, time_sleep, sleep_for)


class LoadingScreen(Screen):
    def __init__(self) -> None:
        super().__init__()
        self.app: HabiTUI

    def compose(self) -> ComposeResult:
        with Vertical(id="home-screen"):
            ascii_art = text2art("habiTUI", font="doom")
            yield Static(ascii_art, id="name-banner")
            yield LoadingIndicator(id="main-loading")
            yield TextualLogConsole(classes="console", id="loading-console", max_lines=20)

    def on_mount(self) -> None:
        """Configura el logger y lanza la carga en background."""
        log_console = self.query_one(TextualLogConsole)
        self.app.logging.setup_logging_widget(log_console)
        self.app.logger.info("Starting HabiTUI...")

        # Inicia carga de datos de forma asincrónica (no bloquea UI)
        create_task(self.app.load_data_async())


class HabiTUI(App):
    BINDINGS = [Binding("q", "quit", "Quit", priority=True)]
    CSS_PATH = "habitui.tcss"
    SCREENS = {"main": MainScreen, "loading": LoadingScreen}
    TITLE = "HabiTUI"
    HORIZONTAL_BREAKPOINTS = [
        (0, "-narrow"),
        (40, "-normal"),
        (80, "-wide"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.logger = get_logger()
        self.theme_manager: TextualThemeManager = TextualThemeManager(self)
        self.habitica_api = HabiticaClient()
        self.vault: DataVault | None = None
        self.logging = LoggingMixin()
        self.data_ready = Event()

    async def on_mount(self) -> None:
        self.theme = "rose_pine"
        await self.push_screen("loading")

    async def load_data_async(self) -> None:
        """Carga datos y pre-renderiza MainScreen en background."""
        try:
            self.logger.info("Loading vault data...")

            loop = get_running_loop()

            # Ejecutar en thread pool para no bloquear UI
            def _load():
                self.vault = DataVault()
                # Esto corre en thread separado
                import asyncio

                asyncio.run(
                    self.vault.get_data(
                        force=False,
                        debug=True,
                        mode="smart",
                        with_challenges=True,
                    ),
                )

            await loop.run_in_executor(None, _load)

            self.logger.info("Vault loaded successfully.")

            # Pre-renderizar MainScreen en thread separado
            self.logger.info("Pre-building main screen...")
            await loop.run_in_executor(None, self._prebuild_main_screen)

            self.logger.info("Main screen ready!")
            self._on_data_ready()

        except Exception as e:
            self.logger.exception(f"Error loading data: {e}")
            self.logger.error("Failed to load vault.")
            self._on_data_ready()

    def _prebuild_main_screen(self) -> None:
        """Pre-construye MainScreen en thread separado (solo estructura, sin renderizar)."""
        # Acceder a propiedades pero sin montar widgets
        # Esto prepara todo lo que MainScreen.__init__ necesita
        _ = self.habitica_api.request_stats.total_requests

    def _on_data_ready(self) -> None:
        """Cambiar a main screen cuando data esté lista."""
        try:
            self.logger.info("Data ready! Switching to main screen...")
            self.data_ready.set()
            self.pop_screen()
            self.push_screen("main")
        except Exception as e:
            self.logger.exception(f"Error switching screen: {e}")


if __name__ == "__main__":
    app = HabiTUI()
    app.run()
