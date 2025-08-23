from __future__ import annotations

from typing import TYPE_CHECKING, Any
from itertools import starmap

from rich.table import Table
from rich.markdown import Markdown as rMarkdown

from textual import on, work
from textual.app import ComposeResult
from textual.screen import Screen, ModalScreen
from textual.binding import Binding
from textual.message import Message
from textual.widgets import (
    Label,
    Button,
    Select,
    Static,
    ListItem,
    ListView,
    Markdown,
    OptionList,
)
from textual.reactive import reactive
from textual.containers import Vertical, Container, Horizontal, VerticalScroll
from textual.widgets.option_list import Option

from habitui.ui import icons, parse_emoji
from habitui.utils import DateTimeHandler
from habitui.tui.generic import BaseTab
from habitui.custom_logger import log
from habitui.core.models.challenge_model import ChallengeInfo, ChallengeCollection


if TYPE_CHECKING:
    from textual.app import ComposeResult

    from habitui.tui.main_app import HabiTUI


# ─── Custom Messages ───────────────────────────────────────────────────────────


class ChallengesNeedRefresh(Message):
    pass


# ─── UI Components ─────────────────────────────────────────────────────────────


class ChallengeTasksWidget(VerticalScroll):
    """Widget to display challenge tasks."""

    def __init__(self, tasks: ChallengeCollection) -> None:
        """Initialize the tasks' widget.

        :param tasks: A list of challenge tasks
        """
        super().__init__(id="tasks-scroll", classes="tasks-container")
        self.tasks = tasks

    def compose(self) -> ComposeResult:
        """Compose the list of tasks."""
        if not self.tasks:
            yield Label("No tasks available", classes="center-text empty-state")
            return

        task_items = []
        for task in self.tasks.all_tasks:
            task_item = ListItem(
                Markdown(task.text),
                classes=f"challenge-task task-{task.type}",
                id=f"task-{task.id}",
            )
            task_item.border_subtitle = f"{icons.CLOCK_O} {task.type}"
            task_items.append(task_item)

        yield ListView(*task_items, id="tasks-list")


class ChallengeHeaderWidget(Container):
    """Widget for challenge headers."""

    def __init__(self, challenge_name: str, leader_name: str, member_count: int):
        """Initialize the challenge header.

        :param challenge_name: Name of the challenge
        :param leader_name: Name of the challenge leader
        :param member_count: Number of challenge members
        """
        super().__init__()
        self.challenge_name = challenge_name
        self.leader_name = leader_name
        self.member_count = member_count

    def compose(self) -> ComposeResult:
        """Compose the header label."""
        yield Label(
            f"{icons.GOAL} {self.challenge_name}",
            classes="challenge-title",
            id="challenge-header",
        )
        yield Label(
            f"{icons.USER} {self.leader_name} • {icons.CROWD} {self.member_count} members",
            classes="challenge-info",
            id="challenge-info",
        )


# ─── Modal Screens ─────────────────────────────────────────────────────────────


class JoinChallengeScreen(ModalScreen):
    """Modal screen to confirm joining a challenge."""

    def __init__(self, challenge_name: str):
        """Initialize the join screen.

        :param challenge_name: The name of the challenge to join
        """
        super().__init__()
        self.challenge_name = challenge_name

    def compose(self) -> ComposeResult:
        """Compose the join dialog."""
        with Container(classes="input-dialog"):
            join_screen = Vertical()
            join_screen.border_title = f"{icons.PLUS_CIRCLE} Join Challenge"

            with join_screen:
                yield Label("Join this challenge?")
                yield Label(f'"{self.challenge_name}"', classes="challenge-preview")

                with Horizontal(classes="modal-buttons"):
                    yield Button("Cancel", id="cancel", variant="warning")
                    yield Button("Join Challenge", id="confirm", variant="success")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "confirm":
            self.dismiss(True)
        else:
            self.dismiss(False)


class LeaveChallengeScreen(ModalScreen):
    """Modal screen to confirm leaving a challenge."""

    def __init__(self, challenge_name: str):
        """Initialize the leave screen.

        :param challenge_name: The name of the challenge to leave
        """
        super().__init__()
        self.challenge_name = challenge_name

    def compose(self) -> ComposeResult:
        """Compose the leave dialog."""
        with Container(classes="input-dialog"):
            leave_screen = Vertical()
            leave_screen.border_title = f"{icons.QUESTION} Leave Challenge"

            with leave_screen:
                yield Label("Leave this challenge?")
                yield Label(f'"{self.challenge_name}"', classes="challenge-preview")
                yield Label(
                    "What should happen to your challenge tasks?",
                    classes="question-text",
                )

                with Horizontal(classes="modal-buttons"):
                    yield Button("Cancel", id="cancel", variant="warning")
                    yield Button("Delete Tasks", id="delete-tasks", variant="error")
                    yield Button("Keep Tasks", id="keep-tasks", variant="success")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "delete-tasks":
            self.dismiss("remove-all")
        elif event.button.id == "keep-tasks":
            self.dismiss("keep-all")
        else:
            self.dismiss(False)


class ChallengeDetailScreen(Screen):
    """Screen for viewing challenge details."""

    BINDINGS = [
        Binding("j", "join_challenge", "Join"),
        Binding("k", "leave_challenge", "Leave"),
        Binding("t", "load_tasks", "Tasks"),
        Binding("escape", "back_to_challenges", "Back"),
    ]

    def __init__(self, challenge_data: dict[str, Any]):
        """Initialize the detail screen.

        :param challenge_data: Dictionary containing challenge details
        """
        super().__init__()
        self.challenge_data = challenge_data
        self.tasks_loaded = False
        self.tasks = []
        self.app: HabiTUI

    def compose(self) -> ComposeResult:
        """Compose the challenge detail view."""
        challenge = self.challenge_data

        yield ChallengeHeaderWidget(
            challenge.name,
            challenge.leader_name,
            challenge.member_count,
        )

        with VerticalScroll(classes="challenge-info"):
            if challenge.summary:
                summary_panel = Static(classes="info-panel")
                summary_panel.border_title = f"{icons.FEATHER} Summary"
                with summary_panel:
                    yield Markdown(challenge.summary)

            # Description
            if challenge.description:
                description_panel = Static(classes="info-panel")
                description_panel.border_title = f"{icons.CARD} Description"
                with description_panel:
                    yield Markdown(challenge.description)

        # Tasks section
        if self.tasks_loaded:
            yield ChallengeTasksWidget(self.tasks)
        else:
            yield Button(
                "Load Challenge Tasks",
                id="load-tasks-btn",
                classes="load-button",
            )

    @work
    async def _load_tasks(self) -> None:
        """Load tasks for the current challenge."""
        try:
            challenge_id = self.challenge_data.id
            if not challenge_id:
                return

            # Aquí usarías tu API para cargar las tareas
            tasks_raw = await self.app.vault.client.get_challenge_tasks_data(
                challenge_id,
            )
            tasks = ChallengeCollection.from_challenge_tasks_data(tasks_raw)
            self.tasks = tasks
            self.tasks_loaded = True

            self.notify(f"{icons.CHECK} Tasks loaded!", severity="information")
            await self.recompose()

        except Exception as e:
            log.error(f"Error loading challenge tasks: {e}")
            self.notify(f"{icons.ERROR} Error loading tasks: {e}", severity="error")

    @work
    async def _join_challenge(self) -> None:
        """Join the current challenge."""
        try:
            challenge_id = self.challenge_data.id
            challenge_name = self.challenge_data.name

            # Confirm join
            join_screen = JoinChallengeScreen(challenge_name)
            confirmed = await self.app.push_screen(join_screen, wait_for_dismiss=True)

            if not confirmed:
                return

            success = await self.app.vault.client.join_challenge(challenge_id)

            if success:
                self.notify(f"{icons.CHECK} Challenge joined!", severity="information")

                self.app.screen.post_message(ChallengesNeedRefresh())
            else:
                self.notify(f"{icons.ERROR} Error joining challenge", severity="error")

        except Exception as e:
            log.error(f"Error joining challenge: {e}")
            self.notify(f"{icons.ERROR} Error joining challenge: {e}", severity="error")

    @work
    async def _leave_challenge(self) -> None:
        """Leave the current challenge."""
        try:
            challenge_id = self.challenge_data.id
            challenge_name = self.challenge_data.name

            # Confirm leave with task handling options
            leave_screen = LeaveChallengeScreen(challenge_name)
            result = await self.app.push_screen(leave_screen, wait_for_dismiss=True)

            if not result:
                return

            # API call to leave challenge
            success = await self.app.vault.client.leave_challenge(challenge_id, result)
            log.warning("success")
            if success:
                self.notify(f"{icons.CHECK} Challenge left!", severity="information")
                self.app.screen.post_message(ChallengesNeedRefresh())
            else:
                self.notify(f"{icons.ERROR} Error leaving challenge", severity="error")

        except Exception as e:
            log.error(f"Error leaving challenge: {e}")
            self.notify(f"{icons.ERROR} Error leaving challenge: {e}", severity="error")

    @on(Button.Pressed, "#load-tasks-btn")
    async def handle_load_tasks(self) -> None:
        """Handle loading tasks for current challenge."""
        self._load_tasks()

    def action_join_challenge(self) -> None:
        self._join_challenge()

    def action_leave_challenge(self) -> None:
        self._leave_challenge()

    def action_load_tasks(self) -> None:
        self._load_tasks()

    def action_back_to_challenges(self) -> None:
        """Dismiss the screen and return to the challenges list."""
        self.dismiss()


# ─── Main Tab ──────────────────────────────────────────────────────────────────


class ChallengesTab(Vertical, BaseTab):
    """Tab for managing challenges with tabbed interface and lazy loading."""

    BINDINGS = [
        Binding("m", "challenges_mine", "My Challenges"),
        Binding("o", "challenges_owned", "Owned"),
        Binding("j", "challenges_joined", "Joined"),
        Binding("p", "challenges_public", "Public"),
        Binding("right", "next_page", "Next →"),
        Binding("left", "prev_page", "← Prev"),
        Binding("r", "refresh_data", "Refresh"),
    ]

    challenges: reactive[dict[str, Any]] = reactive(dict, recompose=True)
    current_mode: reactive[str] = reactive("mine", recompose=True)
    current_page: reactive[int] = reactive(0, recompose=True)
    public_challenges_raw: reactive[dict[str, Any]] = reactive(dict, recompose=False)

    def __init__(self) -> None:
        """Initialize the Challenges tab."""
        super().__init__()
        self.app: HabiTUI
        self.challenges = self.vault.challenges.get_all_challenges()
        log.info("ChallengesTab: initialized")

    def get_challenge(self, challenge_id: str) -> dict[str, Any] | None:
        """Get a specific challenge by ID."""
        return self.challenges.get(challenge_id)

    def format_challenge_option(
        self,
        challenge_id: str,
        challenge_data: ChallengeInfo,
    ) -> Option:
        """Format challenge data for display in an OptionList.

        :param challenge_id: The challenge UUID
        :param challenge_data: The challenge data
        :returns: A configured Option widget
        """
        grid = Table(expand=True, padding=(0, 1), show_header=False, show_lines=True)
        grid.add_column(justify="center", ratio=1)
        grid.add_column(justify="full", ratio=15)
        grid.add_column(justify="left", ratio=3)

        # Status icon based on whether user joined the challenge
        status_icon = (
            icons.CHECK if getattr(challenge_data, "joined", False) else icons.BLANK
        )
        # Third row: Summary and time
        time_formatted = DateTimeHandler(
            timestamp=challenge_data.created_at,
        ).format_time_difference()

        grid.add_row(
            f"{status_icon}",
            f"[b]{parse_emoji(challenge_data.name)}[/b]",
            f"{icons.GEM} {challenge_data.prize}",
        )

        # Second row: Prize, leader, and member count
        grid.add_row(
            "",
            f"{icons.LEGACY if challenge_data.legacy else ''}{parse_emoji(challenge_data.group_name if challenge_data.legacy else 'Public')} {icons.SMALL_CIRCLE} {icons.USER} {parse_emoji(challenge_data.leader_name)}",
            f"{icons.CROWD} {challenge_data.member_count}",
        )

        summary_preview = parse_emoji(challenge_data.summary) or "No summary"

        grid.add_row(
            "",
            rMarkdown(f"{summary_preview}"),
            f"{icons.HISTORY} [dim]{time_formatted.replace(' ago', '')}[/dim]",
        )

        return Option(grid, id=challenge_id)

    def _get_challenges_for_mode(self) -> dict[str, Any]:
        """Get challenges based on current mode."""
        if self.current_mode == "public":
            # Los challenges públicos se manejan por separado con paginación
            return self.challenges

        all_challenges = self.vault.challenges.get_all_challenges()

        if self.current_mode == "mine":
            return all_challenges
        if self.current_mode == "owned":
            return self.vault.challenges.get_owned_challenges()
        if self.current_mode == "joined":
            return self.vault.challenges.get_joined_challenges()

        return all_challenges

    @work
    async def _load_public_challenges(self, page: int = 0) -> None:
        """Load public challenges from API with pagination."""
        try:
            challenges_data = await self.vault.client.get_user_challenges_data(
                member_only=False,
                owned_filter=None,
                page=page,
            )

            # Convertir los datos de la API al formato esperado
            page_collection = ChallengeCollection.from_api_data(
                challenges_data=challenges_data,
                user=self.vault.user,  # Asumiendo que tienes user collection
                tasks=self.vault.tasks,  # Asumiendo que tienes task collection
            )

            # Guardar datos raw para joins posteriores
            self.public_challenges_raw = {}
            for ch in challenges_data:
                self.public_challenges_raw[ch["id"]] = ch

            # Actualizar challenges mostrados
            self.challenges = page_collection.get_all_challenges()
            self.current_page = page

            log.info(f"Loaded page {page} of public challenges")

        except Exception as e:
            log.error(f"Error loading public challenges: {e}")
            self.notify(
                f"{icons.ERROR} Failed to load public challenges",
                severity="error",
            )

    def compose(self) -> ComposeResult:
        """Compose the main challenges UI."""
        mode_titles = {
            "mine": f"{icons.GOAL} My Challenges",
            "owned": f"{icons.CROWN} Owned Challenges",
            "joined": f"{icons.CHECK} Joined Challenges",
            "public": f"{icons.GLOBE} Public Challenges",
        }

        title = mode_titles.get(self.current_mode, f"{icons.GOAL} Challenges")
        if self.current_mode == "public" and self.current_page > 0:
            title += f" (Page {self.current_page + 1})"

        yield Label(title, classes="tab-title")

        modes_options = [
            (f"{icons.GOAL} Mine", "mine"),
            (f"{icons.CROWN} Owned", "owned"),
            (f"{icons.CHECK} Joined", "joined"),
            (f"{icons.GLOBE} Public", "public"),
        ]

        my_select: Select[str] = Select(
            modes_options,
            value=self.current_mode,
            compact=True,
            id="mode_selector",
            classes="mode-selector-dropdown",
        )
        yield my_select

        current_challenges = self._get_challenges_for_mode()

        if not current_challenges:
            empty_messages = {
                "mine": "No challenges yet",
                "owned": "You don't own any challenges",
                "joined": "You haven't joined any challenges",
                "public": "No public challenges available",
            }
            yield Label(
                empty_messages.get(self.current_mode, "No challenges available"),
                classes="center-text empty-state",
            )
            return

        challenges_options = list(
            starmap(self.format_challenge_option, current_challenges.items()),
        )

        yield OptionList(
            *challenges_options,
            id="challenges_list",
            classes="select-line",
        )

    @on(Select.Changed)
    def select_changed(self, event: Select.Changed) -> None:
        """Handle mode selection change."""
        if event.select.id == "mode_selector":
            mode = event.value
            if mode == "mine":
                self.action_challenges_mine()
            elif mode == "owned":
                self.action_challenges_owned()
            elif mode == "joined":
                self.action_challenges_joined()
            elif mode == "public":
                self.action_challenges_public()

    async def on_option_list_option_selected(
        self,
        event: OptionList.OptionSelected,
    ) -> None:
        """Handle challenge selection."""
        if event.option_list.id == "challenges_list":
            challenge_id = str(event.option.id)

            # Para challenges públicos, usar los datos raw
            if self.current_mode == "public":
                challenge_data = self.challenges.get(challenge_id)
                if not challenge_data:
                    challenge_data = self.get_challenge(challenge_id)
            else:
                challenge_data = self.get_challenge(challenge_id)

            if challenge_data:
                detail_screen = ChallengeDetailScreen(challenge_data)
                await self.app.push_screen(detail_screen)
            else:
                self.notify(
                    f"{icons.ERROR} Challenge not found",
                    severity="error",
                )

    @work
    async def refresh_data(self) -> None:
        """Update the challenges data from the vault."""
        log.info("ChallengesTab: refreshing data")
        try:
            # Actualizar desde la API
            await self.vault.update_challenges_only("smart", False, True)
            self.challenges = self.vault.challenges.get_all_challenges()
            self.mutate_reactive(ChallengesTab.challenges)

            self.notify(
                f"{icons.CHECK} Challenges updated successfully!",
                title="Data Updated",
                severity="information",
            )
        except Exception as e:
            log.error(f"ChallengesTab: Error refreshing data: {e}")
            self.notify(
                f"{icons.ERROR} Error updating challenges: {e}",
                title="Error",
                severity="error",
            )

    @on(ChallengesNeedRefresh)
    def handle_challenges_refresh(self) -> None:
        """Catches the refresh message and triggers a data update."""
        self.refresh_data()

    def action_challenges_mine(self) -> None:
        """Show all my challenges."""
        self.current_mode = "mine"
        self.current_page = 0
        self.challenges = self._get_challenges_for_mode()

    def action_challenges_owned(self) -> None:
        """Show challenges I own."""
        self.current_mode = "owned"
        self.current_page = 0
        self.challenges = self._get_challenges_for_mode()

    def action_challenges_joined(self) -> None:
        """Show challenges I've joined."""
        self.current_mode = "joined"
        self.current_page = 0
        self.challenges = self._get_challenges_for_mode()

    def action_challenges_public(self) -> None:
        """Show public challenges."""
        self.current_mode = "public"
        self.current_page = 0
        self.call_after_refresh(lambda: self._load_public_challenges(0))

    def action_next_page(self) -> None:
        """Next page (public challenges only)."""
        if self.current_mode == "public":
            self.call_after_refresh(
                lambda: self._load_public_challenges(self.current_page + 1),
            )

    def action_prev_page(self) -> None:
        """Previous page (public challenges only)."""
        if self.current_mode == "public" and self.current_page > 0:
            self.call_after_refresh(
                lambda: self._load_public_challenges(self.current_page - 1),
            )

    def action_refresh_data(self) -> None:
        """Action to trigger a data refresh."""
        if self.current_mode == "public":
            self.call_after_refresh(
                lambda: self._load_public_challenges(self.current_page),
            )
        else:
            self.refresh_data()
