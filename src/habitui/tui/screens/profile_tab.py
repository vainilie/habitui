# ♥♥─── Profile Tab ──────────────────────────────────────────────────────────────
from __future__ import annotations

from typing import TYPE_CHECKING
from datetime import datetime

from rich.markdown import Markdown

from textual import work
from textual.binding import Binding
from textual.widgets import Label, Collapsible
from textual.reactive import reactive
from textual.containers import Horizontal, VerticalScroll

from box import Box

from habitui.ui import icons
from habitui.custom_logger import log
from habitui.tui.generic.base_tab import BaseTab
from habitui.tui.generic.edit_modal import create_profile_edit_modal
from habitui.tui.generic.confirm_modal import (
    GenericConfirmModal,
    HabiticaChangesFormatter,
)
from habitui.tui.generic.dashboard_panels import (
    Panel,
    create_info_panel,
    create_dashboard_row,
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

    user_collection: reactive[Box] = reactive(Box, recompose=True)

    def __init__(self) -> None:
        super().__init__()
        self.app: HabiTUI
        log.info("ProfileTab: __init__ called")
        self.user_collection = Box(self.vault.user.get_display_data())  # type: ignore

    # ─── UI Composition ────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        """Compose the layout using the new dashboard components."""
        log.info("ProfileTab: compose() called")

        with VerticalScroll(classes="dashboard-main-container"):
            with Horizontal(classes="dashboard-panel-row"):
                yield self._create_user_overview_panel()
                yield self._create_character_stats_panel()
            with Horizontal(classes="dashboard-panel-row"):
                yield self._create_achievements_panel()

            yield self._create_biography_section()

    def _create_user_overview_panel(self) -> Panel:
        """Create the user overview panel using new components."""
        today = datetime.now().strftime("%A %d, %b %Y")  # noqa: DTZ005

        rows = [
            create_dashboard_row(
                value=f"Welcome, {self.user_collection.display_name}!",
                icon="NORTH_STAR",
                element_id="user-welcome-message",
            ),
            create_dashboard_row(
                value=f"Today is {today}",
                icon="CALENDAR",
                element_id="current-date-info",
            ),
            create_dashboard_row(
                value=self.user_collection.sleep,
                icon="DUNGEON",
                element_id="sleep-status-row",
            ),
            create_dashboard_row(
                value=f"Day start: {self.user_collection.day_start}:00",
                icon="CLOCK_O",
                element_id="day-start-time-row",
            ),
        ]

        if self.user_collection.has_quest:
            rows.append(
                create_dashboard_row(
                    value=self.user_collection.quest_display_text,
                    icon="DRAGON",
                    element_id="current-quest-row",
                ),
            )

        if self.user_collection.needs_cron is True:
            rows.append(
                create_dashboard_row(
                    value="Needs Cron",
                    icon="WARNING",
                    element_id="cron-status-row",
                ),
            )

        return create_info_panel(
            *rows,
            title="Overview",
            title_icon="CAT",
            element_id="user-overview-panel",
        )

    def _create_character_stats_panel(self) -> Panel:
        """Create the character stats panel."""
        progress_section = Panel(
            create_dashboard_row(
                label="HP",
                value=self.user_collection.hp.current,
                progress_total=self.user_collection.hp.max,
                show_progress_text=False,
                icon="BEAT",
                css_classes="hp",
                element_id="hp-stats-row",
            ),
            create_dashboard_row(
                label="XP",
                value=self.user_collection.xp.current,
                progress_total=self.user_collection.xp.max,
                show_progress_text=False,
                icon="EXP",
                css_classes="xp",
                element_id="xp-stats-row",
            ),
            create_dashboard_row(
                label="MP",
                value=self.user_collection.mp.current,
                progress_total=self.user_collection.mp.max,
                show_progress_text=False,
                icon="MANA",
                css_classes="mp",
                element_id="mp-stats-row",
            ),
            css_classes="dashboard-panel-horizontal",
            element_id="user-health-mana-xp-bars",
        )

        primary_rows = [
            create_dashboard_row(
                label="Levl",
                value=self.user_collection.level,
                icon="CHART_LINE",
                element_id="stat-level-row",
            ),
            create_dashboard_row(
                label="Gold",
                value=self.user_collection.gold,
                icon="STACK",
                element_id="stat-gold-row",
            ),
            create_dashboard_row(
                label="Gems",
                value=self.user_collection.gems,
                icon="GEM",
                element_id="stat-gems-row",
            ),
        ]

        primary_panel = Panel(
            *primary_rows,
            css_classes="dashboard-panel-vertical",
            element_id="user-primary-stats",
        )

        attribute_rows = [
            create_dashboard_row(
                label="INT",
                value=self.user_collection.intelligence,
                element_id="intelligence-stat-row",
            ),
            create_dashboard_row(
                label="PER",
                value=self.user_collection.perception,
                element_id="perception-stat-row",
            ),
            create_dashboard_row(
                label="STR",
                value=self.user_collection.strength,
                element_id="strength-stat-row",
            ),
            create_dashboard_row(
                label="CON",
                value=self.user_collection.constitution,
                element_id="constitution-stat-row",
            ),
        ]

        attribute_panel = Panel(
            *attribute_rows,
            css_classes="dashboard-panel-vertical",
            element_id="user-attributes-stats",
        )

        stats_horizontal = Horizontal(
            primary_panel,
            attribute_panel,
            classes="dashboard-panel-horizontal",
            id="user-primary-and-attributes-stats",
        )

        return Panel(
            progress_section,
            stats_horizontal,
            title="Stats",
            title_icon="LEVEL",
            element_id="character-stats-panel",
        )

    def _create_achievements_panel(self) -> Panel:
        """Create the achievements panel."""
        (
            create_dashboard_row(
                label="Joined",
                value=self.user_collection.account_created,
                element_id="account-creation-date-row",
            ),
        )  # type: ignore
        achievement_rows = [
            create_dashboard_row(
                label="Check-ins",
                value=self.user_collection.login_days,
                element_id="login-days-row",
            ),
            create_dashboard_row(
                label="Perfect Days",
                value=self.user_collection.perfect_days,
                element_id="perfect-days-row",
            ),
            create_dashboard_row(
                label="21D Streaks",
                value=self.user_collection.streak_count,
                element_id="streak-count-row",
            ),
            create_dashboard_row(
                label="Challenges Won",
                value=self.user_collection.challenges_won,
                element_id="challenges-won-row",
            ),
            create_dashboard_row(
                label="Quests Won",
                value=self.user_collection.quests_completed,
                element_id="quests-completed-row",
            ),
        ]

        return create_info_panel(
            *achievement_rows,
            title="Achievements",
            title_icon="STARRY",
            element_id="user-achievements-panel",
        )

    def _create_biography_section(self) -> Collapsible:
        """Create the biography section."""
        biography_section = Collapsible(
            Label(
                Markdown(self.user_collection.bio),
                id="user-biography-content",
                classes="markdown-box",
            ),
            classes="text-box-collapsible",
            id="user-biography-collapsible",
            title="Description",
        )

        biography_section.border_title = f"{icons.FEATHER} About"
        biography_section.border_subtitle = (
            f"{icons.AT} {self.user_collection.username}"
        )

        return biography_section

    # ─── Data Handling ─────────────────────────────────────────────────────────────

    @work
    async def refresh_data(self) -> None:
        """Refresh user data using BaseTab API access."""
        try:
            await self.vault.update_user_only("smart", False, True, False)
            self.user_collection = Box(self.vault.user.get_display_data())  # type: ignore

            self.mutate_reactive(ProfileTab.user_collection)
            self.notify(
                f"{icons.CHECK} Profile data refreshed successfully!",
                title="Data Refreshed",
                severity="information",
            )
        except Exception as e:
            log.error(f"{icons.ERROR} Error refreshing data: {e}")
            self.notify(
                f"{icons.ERROR} Failed to refresh data: {e}",
                title="Error",
                severity="error",
            )

    # ─── Actions ───────────────────────────────────────────────────────────────────

    async def action_trigger_cron_run(self) -> None:
        """Triggers user cron using BaseTab client access."""
        try:
            log.info(f"{icons.RELOAD} Attempting to trigger cron...")
            await self.client.trigger_user_cron_run()
            self.refresh_data()
            self.notify(
                f"{icons.RELOAD} Cron triggered!",
                title="Cron Triggered",
                severity="information",
            )
            log.info(f"{icons.CHECK} Cron triggered successfully.")
        except Exception as e:
            log.error(f"{icons.ERROR} Error triggering cron: {e}")
            self.notify(
                f"{icons.ERROR} Failed to trigger cron: {e!s}",
                title="Error",
                severity="error",
            )

    async def action_toggle_sleep_status(self) -> None:
        """Toggles user sleep status using BaseTab client access."""
        try:
            log.info(f"{icons.BED} Attempting to toggle sleep status...")
            await self.vault.client.toggle_user_sleep_status()

            is_sleeping = self.vault.user.is_sleeping() if self.vault.user else False
            sleep_status_message = "resting" if is_sleeping else "awake"
            self.refresh_data()

            self.notify(
                f"{icons.BED} Sleep status changed - you are now {sleep_status_message}!",
                title="Sleep Toggled",
                severity="information",
            )
            log.info(f"{icons.CHECK} Sleep status toggled.")
        except Exception as e:
            log.error(f"{icons.ERROR} Error toggling sleep: {e}")
            self.notify(
                f"{icons.ERROR} Failed to toggle sleep status: {e!s}",
                title="Error",
                severity="error",
            )

    def action_edit_profile_mode(self) -> None:
        """Enters profile editing mode."""
        self._edit_profile_workflow()

    @work
    async def _edit_profile_workflow(self) -> None:
        edit_screen = create_profile_edit_modal(
            name=self.user_collection.display_name,
            bio=self.user_collection.bio,
            day_start=self.user_collection.day_start,
        )
        changes = await self.app.push_screen(edit_screen, wait_for_dismiss=True)
        if changes:
            confirm_screen = GenericConfirmModal(
                question="The following changes will be sent to Habitica:",
                changes=changes,
                changes_formatter=HabiticaChangesFormatter.format_changes,
                title="Confirm Changes",
                icon=icons.QUESTION_CIRCLE,
            )
            confirmed = await self.app.push_screen(
                confirm_screen,
                wait_for_dismiss=True,
            )
            if confirmed:
                await self._save_profile_changes_via_api(changes)

    async def _save_profile_changes_via_api(self, changes: dict) -> None:
        try:
            log.info(f"{icons.RELOAD} Saving profile changes via API...")
            payload = self._build_profile_payload(changes)

            if payload:
                operations = [{"type": "update_user_settings", "data": payload}]
                await self.execute_operation(
                    operations,
                    "Update user profile",
                    sync_after="user",
                )

                self.refresh_data()
                self.notify(
                    f"{icons.CHECK} Profile updated successfully!",
                    title="Profile Update",
                    severity="information",
                )
                log.info(f"{icons.CHECK} Profile changes saved.")
            else:
                self.notify(
                    f"{icons.INFO} No changes to save.",
                    title="Profile Update",
                    severity="information",
                )
                log.info("No profile changes to save.")
        except Exception as e:
            log.error(f"{icons.ERROR} Error saving profile changes: {e}")
            self.notify(
                f"{icons.ERROR} Failed to save profile changes: {e!s}",
                title="Error",
                severity="error",
            )

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
