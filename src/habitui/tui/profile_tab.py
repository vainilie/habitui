from __future__ import annotations

from typing import TYPE_CHECKING
from datetime import datetime

from rich.markdown import Markdown

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Label, Collapsible
from textual.reactive import reactive
from textual.containers import Horizontal

from habitui.ui import icons
from habitui.core.models import UserCollection
from habitui.custom_logger import log

from .panel import Panel, FlexibleContainer, create_info_panel, create_dashboard_row

# from pyxabit.textual_screens.components.profile_edit import ProfileEditScreen, ProfileConfirmScreen
from .base_tab import BaseTab


if TYPE_CHECKING:
	from habitui.tui.main_app import HabiTUI


class ProfileTab(FlexibleContainer, BaseTab):
	"""Displays and manages the user's profile information, stats, and achievements."""

	BINDINGS = [
		Binding("s", "toggle_sleep_status", "Sleep"),
		Binding("c", "trigger_cron_run", "Cron"),
		Binding("e", "edit_profile_mode", "Edit"),
		Binding("r", "refresh_data", "Refresh"),
	]

	user_collection: reactive[UserCollection | None] = reactive(None, recompose=True)

	def __init__(self) -> None:
		"""Initializes the ProfileTab."""
		super().__init__(container_type="scrollable", css_classes="dashboard-main-container")
		self.app: HabiTUI
		log.info("ProfileTab: __init__ called")

	def compose(self) -> ComposeResult:
		"""Compose the layout using the new dashboard components."""
		log.info("ProfileTab: compose() called")

		if self.user_collection is None:
			yield Label("Loading Profile Data...", id="profile-loading-message")
		else:
			# Primera fila de paneles
			with Horizontal(classes="dashboard-panel-row"):
				yield self._create_user_overview_panel()
				yield self._create_character_stats_panel()

			# Segunda fila
			with Horizontal(classes="dashboard-panel-row"):
				yield self._create_achievements_panel()

			# Biografía
			self._create_biography_section()

	def _create_user_overview_panel(self) -> Panel:
		"""Create the user overview panel using new components."""
		user = self.user_collection
		today = datetime.now().strftime("%A %d, %b %Y")

		# Usar métodos helper del UserCollection
		display_name = user.get_display_name() if user else "Loading..."
		class_info = user.get_class_info() if user else {"name": "no class", "icon": ""}
		sleep_status = user.get_sleep_status() if user else "Unknown"
		quest_info = user.get_quest_info() if user else {"has_quest": False, "display_text": ""}
		day_start = user.get_day_start_time() if user else "0:00"

		# Crear filas usando los helpers
		rows = [
			create_dashboard_row(
				label=f"Welcome, {class_info['icon']} {display_name}",
				icon="NORTH_STAR",
				element_id="user-welcome-message",
			),
			create_dashboard_row(label=f"Today is {today}", icon="CALENDAR", element_id="current-date-info"),
			create_dashboard_row(label=sleep_status, icon="DUNGEON", element_id="sleep-status-row"),
			create_dashboard_row(label=f"Day starts at: {day_start}", icon="CLOCK_O", element_id="day-start-time-row"),
		]

		# Agregar fila de cron si es necesario
		if user and user.needs_cron():
			rows.insert(-1, create_dashboard_row(label="Needs Cron", icon="WARNING", element_id="cron-status-row"))

		quest_info = user.get_quest_info() if user else {"has_quest": False}
		if quest_info["has_quest"]:
			rows.insert(
				-1,
				create_dashboard_row(label=quest_info["display_text"], icon="DRAGON", element_id="current-quest-row"),  # type: ignore
			)

		return create_info_panel(*rows, title="Overview", title_icon="CAT", element_id="user-overview-panel")

	def _create_character_stats_panel(self) -> Panel:
		"""Create the character stats panel."""
		user = self.user_collection

		# Usar método helper de UserCollection
		stats = user.get_basic_stats() if user else self._get_default_stats()
		attributes = user.get_attributes() if user else self._get_default_attributes()

		# Sección de barras de progreso (HP/XP/MP) con clase específica
		progress_section = Panel(
			create_dashboard_row(
				label="HP",
				value=stats["hp"]["current"],
				progress_total=stats["hp"]["max"],
				show_progress_text=True,
				icon="BEAT",
				css_classes="hp",
				element_id="hp-stats-row",
			),
			create_dashboard_row(
				label="XP",
				value=stats["xp"]["current"],
				progress_total=stats["xp"]["max"],
				show_progress_text=True,
				icon="EXP",
				css_classes="xp",
				element_id="xp-stats-row",
			),
			create_dashboard_row(
				label="MP",
				value=stats["mp"]["current"],
				progress_total=stats["mp"]["max"],
				show_progress_text=True,
				icon="MANA",
				css_classes="mp",
				element_id="mp-stats-row",
			),
			css_classes="dashboard-panel-horizontal",
			element_id="user-health-mana-xp-bars",
		)

		# Stats primarias con clases originales
		primary_rows = [
			create_dashboard_row(label="Level", value=stats["level"], icon="CHART_LINE", element_id="stat-level-row"),
			create_dashboard_row(label="Gold", value=stats["gold"], icon="STACK", element_id="stat-gold-row"),
			create_dashboard_row(label="Gems", value=stats["gems"], icon="GEM", element_id="stat-gems-row"),
		]

		primary_panel = Panel(*primary_rows, css_classes="dashboard-panel-vertical", element_id="user-primary-stats")

		# Atributos
		attribute_rows = [
			create_dashboard_row(label="INT", value=attributes["intelligence"], element_id="intelligence-stat-row"),
			create_dashboard_row(label="PER", value=attributes["perception"], element_id="perception-stat-row"),
			create_dashboard_row(label="STR", value=attributes["strength"], element_id="strength-stat-row"),
			create_dashboard_row(label="CON", value=attributes["constitution"], element_id="constitution-stat-row"),
		]

		attribute_panel = Panel(
			*attribute_rows, css_classes="dashboard-panel-vertical", element_id="user-attributes-stats"
		)

		# Horizontal para primary + attributes con clase original
		stats_horizontal = Horizontal(
			primary_panel, attribute_panel, classes="dashboard-panel-horizontal", id="user-primary-and-attributes-stats"
		)

		# Panel principal
		return Panel(
			progress_section, stats_horizontal, title="Stats", title_icon="LEVEL", element_id="character-stats-panel"
		)

	def _create_achievements_panel(self) -> Panel:
		"""Create the achievements panel."""
		user = self.user_collection
		achievements = user.get_achievements() if user else self._get_default_achievements()

		achievement_rows = [
			create_dashboard_row(
				label="Joined", value=achievements["account_created"], element_id="account-creation-date-row"
			),
			create_dashboard_row(label="Check-ins", value=achievements["login_days"], element_id="login-days-row"),
			create_dashboard_row(
				label="Perfect Days", value=achievements["perfect_days"], element_id="perfect-days-row"
			),
			create_dashboard_row(
				label="21D Streaks", value=achievements["streak_count"], element_id="streak-count-row"
			),
			create_dashboard_row(
				label="Challenges Won", value=achievements["challenges_won"], element_id="challenges-won-row"
			),
			create_dashboard_row(
				label="Quests Won", value=achievements["quests_completed"], element_id="quests-completed-row"
			),
		]

		return create_info_panel(
			*achievement_rows, title="Achievements", title_icon="STARRY", element_id="user-achievements-panel"
		)

	def _create_biography_section(self):
		"""Create the biography section."""
		user = self.user_collection
		profile = user.get_profile_summary() if user else {"username": "Loading...", "bio": "No data"}

		# Usando el componente nativo de Textual para mantener funcionalidad
		biography_section = Collapsible(
			classes="text-box-collapsible",
			id="user-biography-collapsible",
			title="Description",
		)
		biography_section.border_title = f"{icons.FEATHER} About"
		biography_section.border_subtitle = f"{icons.AT} {profile['username']}"

		with biography_section:
			yield Label(Markdown(profile["bio"]), id="user-biography-content", classes="markdown-box")

		biography_section

	# === Helpers para datos por defecto ===

	def _get_default_stats(self) -> dict:
		"""Default stats when user is not loaded."""
		return {
			"hp": {"current": 0, "max": 50},
			"xp": {"current": 0, "max": 100},
			"mp": {"current": 0, "max": 30},
			"level": 1,
			"gold": 0,
			"gems": 0,
		}

	def _get_default_attributes(self) -> dict:
		"""Default attributes when user is not loaded."""
		return {"intelligence": 0, "perception": 0, "strength": 0, "constitution": 0}

	def _get_default_achievements(self) -> dict:
		"""Default achievements when user is not loaded."""
		return {
			"account_created": "N/A",
			"login_days": 0,
			"perfect_days": 0,
			"streak_count": 0,
			"challenges_won": 0,
			"quests_completed": 0,
		}

	# === Event handlers y acciones (usando BaseTab helpers) ===

	def on_mount(self) -> None:
		"""Called when the widget is added to the DOM."""
		log.info("ProfileTab: on_mount called")
		self.call_after_refresh(self._fetch_and_update_data)

	@work
	async def _fetch_and_update_data(self) -> None:
		"""Fetch fresh data using BaseTab vault access."""
		try:
			if self.vault:
				user = self.vault.ensure_user_loaded()
				self.user_collection = user
				log.info("ProfileTab: User collection loaded successfully")
		except Exception as e:
			log.error(f"Error updating user collection: {e}")

	async def refresh_data(self) -> None:
		"""Refreshes user data using BaseTab API access."""
		log.info("ProfileTab: refresh_data called")
		try:
			await self.vault.update_user_only("smart", False, True)
			self._fetch_and_update_data()
			self.mutate_reactive(ProfileTab.user_collection)

			self.notify(
				f"{icons.CHECK} Profile data refreshed successfully!",
				title="Data Refreshed",
				severity="information",
			)
		except Exception as e:
			log.error(f"{icons.ERROR} Error refreshing data: {e}")
			self.notify(f"{icons.ERROR} Failed to refresh data: {e}", title="Error", severity="error")

	async def action_trigger_cron_run(self) -> None:
		"""Triggers user cron using BaseTab client access."""
		try:
			log.info(f"{icons.RELOAD} Attempting to trigger cron...")
			await self.client.trigger_user_cron_run()
			await self.refresh_data()
			self.notify(f"{icons.RELOAD} Cron triggered!", title="Cron Triggered", severity="information")
			log.info(f"{icons.CHECK} Cron triggered successfully.")
		except Exception as e:
			log.error(f"{icons.ERROR} Error triggering cron: {e}")
			self.notify(f"{icons.ERROR} Failed to trigger cron: {e!s}", title="Error", severity="error")

	async def action_toggle_sleep_status(self) -> None:
		"""Toggles user sleep status using BaseTab client access."""
		try:
			log.info(f"{icons.BED} Attempting to toggle sleep status...")
			await self.vault.client.toggle_user_sleep_status()
			await self.refresh_data()

			is_sleeping = self.user_collection.is_sleeping() if self.user_collection else False
			sleep_status_message = "resting" if is_sleeping else "awake"

			self.notify(
				f"{icons.BED} Sleep status changed - you are now {sleep_status_message}!",
				title="Sleep Toggled",
				severity="information",
			)
			log.info(f"{icons.CHECK} Sleep status toggled.")
		except Exception as e:
			log.error(f"{icons.ERROR} Error toggling sleep: {e}")
			self.notify(f"{icons.ERROR} Failed to toggle sleep status: {e!s}", title="Error", severity="error")

	def action_edit_profile_mode(self) -> None:
		"""Enters profile editing mode."""
		self._edit_profile_workflow()

	@work
	async def _edit_profile_workflow(self) -> None:
		"""Handles the profile editing workflow."""
		if not self.user_collection:
			self.notify(f"{icons.WARNING} User data not loaded", title="Error", severity="warning")
			return

		user = self.user_collection
		edit_screen = ProfileEditScreen(
			name=user.profile.name or "",
			bio=user.profile.blurb or "",
			day_start=user.preferences.day_start,
		)

		changes = await self.app.push_screen(edit_screen, wait_for_dismiss=True)
		if changes:
			confirm_screen = ProfileConfirmScreen(changes)
			confirmed = await self.app.push_screen(confirm_screen, wait_for_dismiss=True)
			if confirmed:
				await self._save_profile_changes_via_api(changes)

	async def _save_profile_changes_via_api(self, changes: dict) -> None:
		"""Saves the profile changes using BaseTab execute_operation."""
		try:
			log.info(f"{icons.RELOAD} Saving profile changes via API...")
			payload = self._build_profile_payload(changes)

			if payload:
				# Usar BaseTab.execute_operation para consistencia
				operations = [{"type": "update_user_settings", "data": payload}]
				await self.execute_operation(operations, "Update user profile", sync_after="user")

				await self.refresh_data()
				self.notify(
					f"{icons.CHECK} Profile updated successfully!",
					title="Profile Update",
					severity="information",
				)
				log.info(f"{icons.CHECK} Profile changes saved.")
			else:
				self.notify(f"{icons.INFO} No changes to save.", title="Profile Update", severity="information")
				log.info("No profile changes to save.")
		except Exception as e:
			log.error(f"{icons.ERROR} Error saving profile changes: {e}")
			self.notify(f"{icons.ERROR} Failed to save profile changes: {e!s}", title="Error", severity="error")

	def _build_profile_payload(self, changes: dict) -> dict:
		"""Build the API payload from changes."""
		payload = {}
		field_mappings = {
			"name": "profile.name",
			"bio": "profile.blurb",
			"day_start": "preferences.dayStart",
		}

		for change_key, api_key in field_mappings.items():
			if change_key in changes:
				payload[api_key] = changes[change_key]

		return payload
