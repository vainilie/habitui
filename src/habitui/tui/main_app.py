# ♥♥─── Habitica TUI Main Application ─────────────────────────

from textual.app import App, ComposeResult
from textual.widgets import LoadingIndicator

from habitui.core.services.data_vault import DataVault
from habitui.custom_logger import get_logger

from .components.api_handler import SimpleAPIHandler
from .main_screen import MainScreen
from .textual_theme import TextualThemeManager


# ─── Habitica App ──────────────────────────────────────────────────────────────
class HabiticaApp(App):
    """Main Habitica application with app-level vault and API handling."""

    def __init__(self) -> None:
        super().__init__()

        self.logger = get_logger()
        self.vault = DataVault()
        self.api_handler = SimpleAPIHandler(self.vault)
        self.theme_manager: TextualThemeManager = TextualThemeManager(self)

    def compose(self) -> ComposeResult:
        """Compose the main screen."""
        yield LoadingIndicator()

    def on_mount(self) -> None:
        """Actions to perform when the app is mounted."""
        self.title = "PYXABIT 󰞇"
        self.theme = "Rose Pine"

        self.push_screen(MainScreen())


if __name__ == "__main__":
    app = HabiticaApp()

    # Optional: Set a specific theme at startup
    app.run()
