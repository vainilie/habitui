# ♥♥─── Profile Tab ──────────────────────────────────────────────────────────────
from __future__ import annotations

from typing import TYPE_CHECKING
from datetime import datetime

from rich.markdown import Markdown

from textual import work
from textual.binding import Binding
from textual.widgets import Label, Collapsible
from textual.reactive import reactive
from textual.containers import Grid, Horizontal, VerticalScroll

from box import Box

from habitui.ui import icons
from habitui.custom_logger import log
from habitui.tui.generic.base_tab import BaseTab
from habitui.tui.generic.edit_modal import create_profile_edit_modal
from habitui.tui.generic.confirm_modal import GenericConfirmModal, HabiticaChangesFormatter
from habitui.tui.generic.dashboard_panels import (
    Panel,
    create_info_panel as cip,
    create_dashboard_row as cdr,
)


if TYPE_CHECKING:
    from textual.app import ComposeResult

    from habitui.tui.main_app import HabiTUI


class ProfileTab(BaseTab):
    """Displays and manages the user's profile information, stats, and achievements."""

    # ─── Configuration ─────────────────────────────────────────────────────────────
    BINDINGS: list[Binding] = [
        Binding("s", "toggle_sleep_status", "Sleep"),
        Binding("c", "trigger_cron_run", "Cron"),
        Binding("e", "edit_profile_mode", "Edit"),
        Binding("r", "refresh_data", "Refresh"),
    ]

    uc: reactive[Box] = reactive(Box, recompose=True)
    app: HabiTUI

    def __init__(self) -> None:
        super().__init__()
        log.info("ProfileTab: __init__ called")
        self.uc = Box(self.vault.user.get_display_data())  # type: ignore

    # ─── UI Composition ────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        """Compose the layout using the new dashboard components."""
        log.info("ProfileTab: compose() called")

        with VerticalScroll(classes="dashboard-main-container"):
            with Grid(classes="dashboard-panel-row"):
                yield self._create_user_overview_panel()
                yield self._create_character_stats_panel()
            with Grid(classes="dashboard-panel-row"):
                yield self._create_achievements_panel()
                yield self._create_statistics_stats()

            yield self._create_biography_section()

    def _create_user_overview_panel(self) -> Panel:
        """Create the user overview panel using new components."""
        today = datetime.now().strftime("%A %d, %b %Y")  # noqa: DTZ005

        rows = [
            cdr(value=f"Welcome, {self.uc.display_name}!", icon="NORTH_STAR", element_id="user-welcome-message"),
            cdr(value=f"Today is {today}", icon="CALENDAR", element_id="current-date-info"),
            cdr(value=self.uc.sleep, icon="DUNGEON", element_id="sleep-status-row"),
            cdr(value=f"Day start: {self.uc.day_start}:00", icon="CLOCK_O", element_id="day-start-time-row"),
            cdr(icon="CUT", value=f"User Damage: {round(self.vault.ensure_tasks_loaded().get_damage()[1], 1)}", element_id="userdmg-stat-row"),
        ]
        if self.uc.needs_cron is True:
            rows.append(cdr(value="Needs Cron", icon="WARNING", element_id="cron-status-row"))

        if self.uc.has_quest:
            rows.extend((
                cdr(value=self.uc.quest_display_text, icon="DRAGON", element_id="current-quest-row"),
                cdr(value=f"Party Damage: {round(self.vault.ensure_tasks_loaded().get_damage()[0], 1)}", element_id="partydam-stat-row", icon="CUT"),
            ))

        return cip(*rows, title="Overview", title_icon="CAT", element_id="user-overview-panel")

    def _create_character_stats_panel(self) -> Panel:
        """Create the character stats panel."""
        progress_section = Panel(
            cdr(
                label="HP",
                value=self.uc.hp.current,
                progress_total=self.uc.hp.max,
                show_progress_text=False,
                icon="BEAT",
                css_classes="hp",
                element_id="hp-stats-row",
            ),
            cdr(
                label="XP",
                value=self.uc.xp.current,
                progress_total=self.uc.xp.max,
                show_progress_text=False,
                icon="EXP",
                css_classes="xp",
                element_id="xp-stats-row",
            ),
            cdr(
                label="MP",
                value=self.uc.mp.current,
                progress_total=self.uc.mp.max,
                show_progress_text=False,
                icon="MANA",
                css_classes="mp",
                element_id="mp-stats-row",
            ),
            css_classes="dashboard-panel-horizontal",
            element_id="user-health-mana-xp-bars",
        )

        primary_rows = [
            cdr(label="Levl", value=self.uc.level, icon="CHART_LINE", element_id="stat-level-row"),
            cdr(label="Gold", value=self.uc.gold, icon="STACK", element_id="stat-gold-row"),
            cdr(label="Gems", value=self.uc.gems, icon="GEM", element_id="stat-gems-row"),
        ]

        primary_panel = Panel(*primary_rows, css_classes="dashboard-panel-vertical", element_id="user-primary-stats")

        attribute_rows = [
            cdr(label="INT", value=self.uc.intelligence, element_id="intelligence-stat-row"),
            cdr(label="PER", value=self.uc.perception, element_id="perception-stat-row"),
            cdr(label="STR", value=self.uc.strength, element_id="strength-stat-row"),
            cdr(label="CON", value=self.uc.constitution, element_id="constitution-stat-row"),
        ]

        attribute_panel = Panel(*attribute_rows, css_classes="dashboard-panel-vertical", element_id="user-attributes-stats")

        stats_horizontal = Horizontal(primary_panel, attribute_panel, classes="dashboard-panel-horizontal", id="user-primary-and-attributes-stats")

        return Panel(progress_section, stats_horizontal, title="Stats", title_icon="LEVEL", element_id="character-stats-panel")

    def _create_achievements_panel(self) -> Panel:
        """Create the achievements panel."""
        (cdr(label="Joined", value=self.uc.account_created, element_id="account-creation-date-row"),)
        achievement_rows = [
            cdr(label="Check-ins", value=self.uc.login_days, element_id="login-days-row"),
            cdr(label="Perfect Days", value=self.uc.perfect_days, element_id="perfect-days-row"),
            cdr(label="21D Streaks", value=self.uc.streak_count, element_id="streak-count-row"),
            cdr(label="Challenges Won", value=self.uc.challenges_won, element_id="challenges-won-row"),
            cdr(label="Quests Won", value=self.uc.quests_completed, element_id="quests-completed-row"),
            cdr(label="Total Challenges", value=len(self.vault.ensure_challenges_loaded().get_all_challenges()), element_id="all-challenges-row"),
            cdr(label="Participating Challenges", value=len(self.vault.ensure_challenges_loaded().get_joined_challenges()), element_id="joined-challenges-row"),
            cdr(label="Created Challenges", value=len(self.vault.ensure_challenges_loaded().get_owned_challenges()), element_id="created-challenges-row"),
        ]

        return cip(*achievement_rows, title="Achievements", title_icon="STARRY", element_id="user-achievements-panel")

    def _create_statistics_stats(self) -> Panel:
        """Create the statistics panel with tasks and challenges sections."""
        tasks_rows = [
            cdr(icon="TODO", label="Todos", value=len(self.vault.ensure_tasks_loaded().todos), element_id="total-todos-row"),
            cdr(icon="HABIT", label="Habits", value=len(self.vault.ensure_tasks_loaded().habits), element_id="total-habits-row"),
            cdr(icon="REWARD", label="Rewards", value=len(self.vault.ensure_tasks_loaded().rewards), element_id="total-rewards-row"),
            cdr(icon="DAILY", label="Dailies", value=len(self.vault.ensure_tasks_loaded().dailys), element_id="total-dailies-row"),
        ]
        today = datetime.now().strftime("%d, %b %Y")  # noqa: DTZ005

        challenges_rows = [
            cdr(icon="USER", label="User Tasks", value=len(self.vault.ensure_tasks_loaded().get_owned_tasks()), element_id="owntasks-challenges-row"),
            cdr(icon="KEY", label="Challenge Tasks", value=len(self.vault.ensure_tasks_loaded().get_challenge_tasks()), element_id="chtasks-challenges-row"),
            cdr(icon="TASK", label="Total Tasks", value=len(self.vault.ensure_tasks_loaded().all_tasks), element_id="total-tasks-row"),
            cdr(icon="TODAY", label="Due Dailies", value=len(self.vault.ensure_tasks_loaded().get_due_dailies()), element_id="today-dailies-row"),
        ]

        # Crear paneles individuales siguiendo la misma estructura que stats
        tasks_panel = Panel(*tasks_rows, css_classes="dashboard-panel-vertical", element_id="user-tasks-stats")

        challenges_panel = Panel(*challenges_rows, css_classes="dashboard-panel-vertical", element_id="user-challenges-stats")

        # Contenedor horizontal como en character stats
        stats_horizontal = Horizontal(challenges_panel, tasks_panel, classes="dashboard-panel-horizontal", id="user-tasks-and-challenges-stats")

        # Panel principal
        return Panel(stats_horizontal, title="Statistics", title_icon="STARRY", element_id="user-statistics-panel")

    def _create_biography_section(self) -> Collapsible:
        """Create the biography section."""
        biography_section = Collapsible(
            Label(Markdown(self.uc.bio), id="user-biography-content", classes="markdown-box"),
            classes="text-box-collapsible",
            id="user-biography-collapsible",
            title="Description",
        )

        biography_section.border_title = f"{icons.FEATHER} About"
        biography_section.border_subtitle = f"{icons.AT} {self.uc.username}"

        return biography_section

    # ─── Data Handling ─────────────────────────────────────────────────────────────

    @work
    async def refresh_data(self) -> None:
        """Refresh user data using BaseTab API access."""
        try:
            await self.vault.update_user_only("smart", False, True, False)
            self.uc = Box(self.vault.user.get_display_data())  # type: ignore
            self.mutate_reactive(ProfileTab.uc)
            self.notify(f"{icons.CHECK} Profile data refreshed successfully!", title="Data Refreshed", severity="information")
        except Exception as e:
            log.error(f"{icons.ERROR} Error refreshing data: {e}")
            self.notify(f"{icons.ERROR} Failed to refresh data: {e}", title="Error", severity="error")

    # ─── Actions ───────────────────────────────────────────────────────────────────
    async def action_refresh_data(self) -> None:
        self.refresh_data()

    async def action_trigger_cron_run(self) -> None:
        """Triggers user cron using BaseTab client access."""
        try:
            log.info(f"{icons.RELOAD} Attempting to trigger cron...")
            await self.client.trigger_user_cron_run()
            self.refresh_data()
            self.notify(f"{icons.RELOAD} Cron triggered!", title="Cron Triggered", severity="information")
            log.info(f"{icons.CHECK} Cron triggered successfully.")
        except Exception as e:
            log.error(f"{icons.ERROR} Error triggering cron: {e}")
            self.notify(f"{icons.ERROR} Failed to trigger cron: {e!s}", title="Error", severity="error")

    async def action_toggle_sleep_status(self) -> None:
        """Toggles user sleep status using BaseTab client access."""
        try:
            log.info(f"{icons.BED} Attempting to toggle sleep status...")

            is_sleeping = self.vault.user.is_sleeping() if self.vault.user else False
            sleep_status_message = "awake" if is_sleeping is True else "resting"
            await self.vault.client.toggle_user_sleep_status()
            self.refresh_data()

            self.notify(f"{icons.BED} Sleep status changed - you are now {sleep_status_message}!", title="Sleep Toggled", severity="information")
            log.info(f"{icons.CHECK} Sleep status toggled.")
        except Exception as e:
            log.error(f"{icons.ERROR} Error toggling sleep: {e}")
            self.notify(f"{icons.ERROR} Failed to toggle sleep status: {e!s}", title="Error", severity="error")

    def action_edit_profile_mode(self) -> None:
        """Enters profile editing mode."""
        self._edit_profile_workflow()

    @work
    async def _edit_profile_workflow(self) -> None:
        edit_screen = create_profile_edit_modal(name=self.uc.display_name, bio=self.uc.bio, day_start=self.uc.day_start)
        changes = await self.app.push_screen(edit_screen, wait_for_dismiss=True)
        if changes:
            confirm_screen = GenericConfirmModal(
                question="The following changes will be sent to Habitica:",
                changes=changes,
                changes_formatter=HabiticaChangesFormatter.format_changes,
                title="Confirm Changes",
                icon=icons.QUESTION_CIRCLE,
            )
            confirmed = await self.app.push_screen(confirm_screen, wait_for_dismiss=True)
            if confirmed:
                await self._save_profile_changes_via_api(changes)

    async def _save_profile_changes_via_api(self, changes: dict) -> None:
        try:
            log.info(f"{icons.RELOAD} Saving profile changes via API...")
            payload = self._build_profile_payload(changes)

            if payload:
                await self.app.habitica_api.update_user_settings_or_data(update_payload=payload)

                self.refresh_data()
                self.notify(f"{icons.CHECK} Profile updated successfully!", title="Profile Update", severity="information")
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
        field_mappings = {"name": "profile.name", "bio": "profile.blurb", "day_start": "preferences.dayStart"}

        for change_key, api_key in field_mappings.items():
            if change_key in changes:
                payload[api_key] = changes[change_key]

        return payload
