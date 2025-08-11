# ♥♥─── HabiTUI Application Core ─────────────────────────────────────────


from __future__ import annotations

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Static, LoadingIndicator
from textual.containers import Vertical

from art import text2art

from habitui.custom_logger import get_logger
from habitui.core.services.data_vault import DataVault

from .main_screen import MainScreen
from .textual_log import LoggingMixin, TextualLogConsole
from .textual_theme import TextualThemeManager


class HabiTUI(LoggingMixin, App):
	"""
	Main application class for HabiTUI. Manages application lifecycle, data loading, and screen transitions.
	"""

	BINDINGS = [
		Binding("q", "quit", "Quit"),
	]
	CSS_PATH = "habitui.css"

	def __init__(self) -> None:
		"""Initializes the HabiTUI application."""
		super().__init__()
		self.logger = get_logger()
		self.theme_manager: TextualThemeManager = TextualThemeManager(self)
		self.vault: DataVault | None = None
		self._loading_complete: bool = False

	def compose(self) -> ComposeResult:
		"""
		Composes the initial layout of the application. Displays an ASCII art banner, a loading indicator, and a log console.
		"""
		vertical = Vertical(id="home_screen")

		with vertical:
			ascii_art = text2art("habiTUI", font="ogre")
			yield Static(ascii_art, id="ascii-banner")  # type: ignore
			yield LoadingIndicator(id="main-loading")
			yield TextualLogConsole(id="log-console")

	async def on_mount(self) -> None:
		"""Actions to perform when the app is mounted. Sets up logging, banner styling, and initiates asynchronous data loading."""

		self.setup_banner_styling()

		# Explicitly set up logging for the initial console
		initial_log_console = self.query_one("#log-console", TextualLogConsole)
		self.setup_logging_widget(initial_log_console)

		self.logger.info("Starting HabiTUI...")
		self.title = "HabiTUI"
		self.theme = "rose_pine"

		self.load_vault_and_main_screen()

	# ─── Setup Methods ─────────────────────────────────────────────────────────────

	def setup_banner_styling(self) -> None:
		"""
		Applies styles to the ASCII art banner.
		"""
		try:
			banner = self.query_one("#ascii-banner", Static)
			banner.styles.color = "rgb(235,188,186)"
			banner.styles.text_align = "center"

		except Exception as e:
			self.logger.warning(f"Could not style the banner: {e}")

	# ─── Data Loading and Screen Transition ────────────────────────────────────────

	@work(exclusive=True)
	async def load_vault_and_main_screen(self) -> None:
		"""
		Loads the DataVault and transitions to the MainScreen.
		This operation runs in a background worker thread.
		"""
		try:
			self.logger.info("Starting vault load...")
			self.vault = DataVault()
			await self.vault.get_data(force=False, debug=True, mode="smart")
			self.logger.info("Vault loaded successfully.")
			self.logger.info("Transitioning to MainScreen...")
			self._loading_complete = True
			self.push_screen(MainScreen())

		except Exception as e:
			self.logger.error(f"Error during data loading: {e}")


if __name__ == "__main__":
	app = HabiTUI()
	app.run()
