# ♥♥─── Main Screen ──────────────────────────────────────────────────────────────
from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from textual.screen import Screen
from textual.binding import Binding
from textual.widgets import Footer, Header, TabPane, TabbedContent
from textual.containers import Vertical, Horizontal

from habitui.ui import icons
from habitui.core.services.data_vault import DataVault

from .profile_tab import ProfileTab
from .textual_log import TextualLogConsole


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

	CSS_PATH = "habitui.css"

	def __init__(self) -> None:
		"""Initializes the MainScreen."""
		super().__init__()
		self.app: HabiTUI
		self.show_sidebar: bool = False
		self.loaded_tabs = set()

	@property
	def vault(self) -> DataVault:
		return cast("DataVault", self.app.vault)

	@property
	def logger(self) -> Any:
		"""Direct access to app-level logger."""
		return self.app.logger

	def compose(self) -> ComposeResult:
		"""Composes the main layout of the screen."""
		yield Header(show_clock=True)
		with Horizontal(id="content-area"):
			with Vertical(id="main-container"), TabbedContent(initial="profile") as tabs:
				with TabPane("Profile", id="profile"):
					pass
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
			with Vertical(id="sidebar"):
				yield TextualLogConsole(id="log-console")

		yield Footer()

	async def on_mount(self) -> None:
		"""Performs initial setup when the screen is mounted."""
		self.load_initial_tab()

	def load_initial_tab(self) -> None:
		"""Load the content for the initial tab."""
		tabs = self.query_one(TabbedContent)
		initial_tab_id = tabs.active
		if initial_tab_id:
			self.load_tab_content(initial_tab_id)

	def load_tab_content(self, tab_id: str) -> None:
		"""Load content for a specific tab if not already loaded."""
		if tab_id in self.loaded_tabs:
			return

		content_map = {
			"profile": ProfileTab,
			#  "party": PartyTab,
			#  "tags": TagsTab,
			#  "inbox": InboxTab,
			#  "challenges": ChallengesTab,
			#  "config": ConfigTab,
			#  "tasks": TasksTab,
		}
		if tab_id in content_map:
			tab = self.query_one(f"#{tab_id}", TabPane).focus()
			tab.mount(content_map[tab_id]())
			self.loaded_tabs.add(tab_id)

	async def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
		"""Handle tab activation to load content lazily."""
		self.load_tab_content(event.pane.id)  # type: ignore

	def action_toggle_log(self) -> None:
		"""Toggles the visibility of the log sidebar."""
		self.show_sidebar = not self.show_sidebar
		sidebar = self.query_one("#sidebar")
		main_container = self.query_one("#main-container")

		if self.show_sidebar:
			sidebar.add_class("visible")
			main_container.add_class("with-sidebar")
			self.logger.info(f"{icons.INFO} Log sidebar shown")

		else:
			sidebar.remove_class("visible")
			main_container.remove_class("with-sidebar")
			self.logger.info(f"{icons.INFO} Log sidebar hidden")

	async def action_refresh_quick(self) -> None:
		"""Performs a quick data refresh (F5)."""
		await self.vault.refresh_quick(force=False)
