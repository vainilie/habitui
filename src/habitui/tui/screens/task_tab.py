from __future__ import annotations

from typing import TYPE_CHECKING

from rich.table import Table

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import (
    Label,
    Button,
    Select,
    OptionList,
)
from textual.reactive import reactive
from textual.containers import Vertical, Horizontal
from textual.widgets.option_list import Option

from habitui.ui import icons
from habitui.utils import DateTimeHandler
from habitui.tui.generic import BaseTab, GenericConfirmModal
from habitui.custom_logger import log
from habitui.core.models.task_model import (
    AnyTask,
    TaskHabit,
    TaskCollection,
)


if TYPE_CHECKING:
    from textual.app import ComposeResult

    from habitui.tui.main_app import HabiTUI


class TasksTab(Vertical, BaseTab):
    """A tabbed interface for displaying and interacting with user tasks."""

    BINDINGS = [
        Binding("D", "delete_task", "Delete"),
        Binding("C", "score_task", "Score"),
        Binding("+", "score_up_task", "Score up"),
        Binding("-", "score_down_task", "Score down"),
        Binding("A", "add_task", "Add"),
        Binding("r", "refresh_data", "Refresh"),
        Binding("m", "toggle_multiselect", "Multiselection"),
        Binding("escape", "clear_selection", "Clear"),
        Binding("d", "tasks_dailies", "Dailies"),
        Binding("t", "tasks_todos", "Todos"),
        Binding("h", "tasks_habits", "Habits"),
        Binding("w", "tasks_rewards", "Rewards"),
        Binding("a", "tasks_all", "All"),
    ]

    tasks: reactive[TaskCollection] = reactive(None, recompose=True)
    current_mode: reactive[str] = reactive("dailies", recompose=True)
    current_sort: reactive[str] = reactive("default", recompose=True)
    current_filter: reactive[str] = reactive("all", recompose=True)
    current_challenge_filter: reactive[str] = reactive("all", recompose=True)
    multiselect: reactive[bool] = reactive(False, recompose=True)
    tasks_selected: reactive[set[str]] = reactive(
        set,
        init=False,
    )  # Store IDs instead of objects

    def __init__(self) -> None:
        """Initialize the TasksTab."""
        super().__init__()
        self.app: HabiTUI
        self.tasks = self.vault.ensure_tasks_loaded()

        # Sort options
        self.sort_options = [
            ("Default", "default"),
            ("Name A-Z", "name_asc"),
            ("Name Z-A", "name_desc"),
            ("Priority High-Low", "priority_desc"),
            ("Priority Low-High", "priority_asc"),
            ("Value High-Low", "value_desc"),
            ("Value Low-High", "value_asc"),
            ("Created New-Old", "created_desc"),
            ("Created Old-New", "created_asc"),
        ]

        # Filter options
        self.filter_options = [
            ("All Tasks", "all"),
            ("Challenge Tasks", "challenge"),
            ("Non-Challenge", "non_challenge"),
            ("Completed", "completed"),
            ("Incomplete", "incomplete"),
            ("Due Today", "due_today"),
        ]

        # Challenge filter options - will be populated dynamically
        self.challenge_filter_options = [("All Challenges", "all")]

        log.info("TasksTab: initialized")

    def get_task(self, task_id: str) -> AnyTask | None:
        """Get a task by its ID from the main task collection."""
        return self.tasks.get_task_by_id(task_id)

    def format_task_option(self, task: AnyTask) -> Option:
        """Format a single task model into a rich, selectable Option."""
        grid = Table.grid(expand=True, padding=(0, 1))
        grid.add_column(ratio=3)
        grid.add_column(ratio=1, justify="right")

        task_name = getattr(task, "text", "Unnamed Task")

        # Check if task is selected for visual styling
        is_selected = self.multiselect and task.id in self.tasks_selected

        # Status icon based on task state
        status_icon = icons.BLANK_CIRCLE_O
        if getattr(task, "completed", False):
            status_icon = icons.CHECK
        elif getattr(task, "isDue", False) or getattr(task, "due_today", False):
            status_icon = icons.EXCLAMATION

        # Apply selection styling if selected
        if is_selected:
            color = self.app.theme_variables.get("accent", "primary")
            display_name = f"[b {color}]{icons.CHECK} {task_name}[/b {color}]"
        else:
            display_name = f"{status_icon} [b]{task_name}[/b]"

        # Add challenge indicator if applicable
        challenge_shortname = getattr(task, "challenge_shortname", None)
        if challenge_shortname:
            display_name += f" {icons.TROPHY}[dim]({challenge_shortname})[/dim]"

        grid.add_row(display_name, f"[dim]{task.type}[/dim]")
        grid.add_row(
            f"{icons.STAR} Priority: {task.priority:.1f} • Value: {task.value:.2f}",
            "",
        )

        notes = getattr(task, "notes", "") or ""
        notes_preview = (notes[:50] + "...") if len(notes) > 50 else notes or "No notes"

        grid.add_row(
            f"[dim]{notes_preview}[/]",
            f"[dim]{DateTimeHandler(timestamp=task.created_at).format_time_difference()}[/dim]",
        )

        return Option(grid, id=task.id)

    def _get_challenge_filter_options(self) -> list[tuple[str, str]]:
        """Get available challenge short_names for filtering."""
        options = [("All Challenges", "all")]

        # Collect all unique challenge short_names
        challenge_names = set()
        for task in self.tasks.all_tasks:
            challenge_shortname = getattr(task, "challenge_shortname", None)
            if challenge_shortname:
                challenge_names.add(challenge_shortname)

        # Add each challenge as a filter option
        for name in sorted(challenge_names):
            options.append((f"Challenge: {name}", name))

        return options

    def _get_tasks_for_mode(self) -> list[AnyTask]:
        """Get the correct list of task models for the current view mode."""
        if self.current_mode == "all":
            tasks_list = self.tasks.all_tasks
        else:
            mode_to_attr = {
                "dailies": "dailys",
                "todos": "todos",
                "habits": "habits",
                "rewards": "rewards",
            }
            attr_name = mode_to_attr.get(self.current_mode, "")
            tasks_list = getattr(self.tasks, attr_name, [])

        # Apply filters
        filtered_tasks = self._filter_tasks(tasks_list)

        # Apply sorting
        return self._sort_tasks(filtered_tasks)

    def _filter_tasks(self, tasks_list: list[AnyTask]) -> list[AnyTask]:
        """Filter tasks based on current filter settings."""
        # Apply general filters
        if self.current_filter == "challenge":
            tasks_list = [t for t in tasks_list if getattr(t, "challenge", None)]
        elif self.current_filter == "non_challenge":
            tasks_list = [t for t in tasks_list if not getattr(t, "challenge", None)]
        elif self.current_filter == "completed":
            tasks_list = [t for t in tasks_list if getattr(t, "completed", False)]
        elif self.current_filter == "incomplete":
            tasks_list = [t for t in tasks_list if not getattr(t, "completed", False)]
        elif self.current_filter == "due_today":
            tasks_list = [
                t
                for t in tasks_list
                if getattr(t, "isDue", False) or getattr(t, "due_today", False)
            ]
        # "all" filter doesn't modify the list

        # Apply challenge-specific filter
        if self.current_challenge_filter != "all":
            tasks_list = [
                t
                for t in tasks_list
                if getattr(t, "challenge_shortname", None)
                == self.current_challenge_filter
            ]

        return tasks_list

    def _sort_tasks(self, tasks_list: list[AnyTask]) -> list[AnyTask]:
        """Sort a list of task models based on the current sort mode."""
        if self.current_sort == "default":
            return tasks_list
        if self.current_sort == "name_asc":
            return sorted(tasks_list, key=lambda t: t.text.lower())
        if self.current_sort == "name_desc":
            return sorted(tasks_list, key=lambda t: t.text.lower(), reverse=True)
        if self.current_sort == "priority_desc":
            return sorted(tasks_list, key=lambda t: t.priority, reverse=True)
        if self.current_sort == "priority_asc":
            return sorted(tasks_list, key=lambda t: t.priority)
        if self.current_sort == "value_desc":
            return sorted(tasks_list, key=lambda t: t.value, reverse=True)
        if self.current_sort == "value_asc":
            return sorted(tasks_list, key=lambda t: t.value)
        if self.current_sort == "created_desc":
            return sorted(tasks_list, key=lambda t: t.created_at, reverse=True)
        if self.current_sort == "created_asc":
            return sorted(tasks_list, key=lambda t: t.created_at)

        return tasks_list

    def compose(self) -> ComposeResult:
        """Compose the dynamic UI for the tasks tab."""
        mode_titles = {
            "dailies": f"{icons.CALENDAR} Dailies",
            "todos": f"{icons.TASK_LIST} Todos",
            "habits": f"{icons.INFINITY} Habits",
            "rewards": f"{icons.GIFT} Rewards",
            "all": f"{icons.GOAL} All Tasks",
        }
        title = mode_titles.get(self.current_mode, f"{icons.GOAL} Tasks")

        yield Label(f"{title}", classes="tab-title")

        # Control row with dropdowns
        with Horizontal(classes="controls-row"):
            yield Select(
                [
                    (f"{icons.CALENDAR} Dailies", "dailies"),
                    (f"{icons.TASK_LIST} Todos", "todos"),
                    (f"{icons.INFINITY} Habits", "habits"),
                    (f"{icons.GIFT} Rewards", "rewards"),
                    (f"{icons.GOAL} All", "all"),
                ],
                value=self.current_mode,
                id="mode_selector",
                classes="control-select",
            )

            yield Select(
                self.sort_options,
                value=self.current_sort,
                id="sort_selector",
                classes="control-select",
            )

            yield Select(
                self.filter_options,
                value=self.current_filter,
                id="filter_selector",
                classes="control-select",
            )

            # Challenge filter - only show if there are challenges
            challenge_options = self._get_challenge_filter_options()
            if len(challenge_options) > 1:  # More than just "All Challenges"
                yield Select(
                    challenge_options,
                    value=self.current_challenge_filter,
                    id="challenge_filter_selector",
                    classes="control-select",
                )

        # Multiselect controls
        if self.multiselect:
            with Horizontal(classes="multiselect-controls"):
                yield Button("Score Selected", id="score_selected", variant="success")
                if self.current_mode == "habits":
                    yield Button("Score Up", id="score_up_selected", variant="primary")
                    yield Button(
                        "Score Down",
                        id="score_down_selected",
                        variant="warning",
                    )
                yield Button("Delete Selected", id="delete_selected", variant="error")
                yield Label(
                    f"Selected: {len(self.tasks_selected)}",
                    classes="selection-count",
                )

        current_tasks = self._get_tasks_for_mode()

        if not current_tasks:
            yield Label(
                "No tasks found in this category.",
                classes="center-text empty-state",
            )
            return

        yield OptionList(
            *[self.format_task_option(task) for task in current_tasks],
            id="tasks_list",
            classes="select-line",
        )

    # ─── Event Handlers ────────────────────────────────────────────────────────────
    @on(Select.Changed, "#mode_selector")
    def handle_mode_change(self, event: Select.Changed) -> None:
        """Switch the task view when the dropdown is changed."""
        if isinstance(event.value, str):
            self.current_mode = event.value

    @on(Select.Changed, "#sort_selector")
    def handle_sort_change(self, event: Select.Changed) -> None:
        """Change sort order when dropdown is changed."""
        if isinstance(event.value, str):
            self.current_sort = event.value

    @on(Select.Changed, "#filter_selector")
    def handle_filter_change(self, event: Select.Changed) -> None:
        """Change filter when dropdown is changed."""
        if isinstance(event.value, str):
            self.current_filter = event.value

    @on(Select.Changed, "#challenge_filter_selector")
    def handle_challenge_filter_change(self, event: Select.Changed) -> None:
        """Change challenge filter when dropdown is changed."""
        if isinstance(event.value, str):
            self.current_challenge_filter = event.value

    @on(Button.Pressed, "#score_selected")
    async def handle_score_selected(self, event: Button.Pressed) -> None:
        """Score all selected tasks."""
        await self._score_selected_tasks("auto")

    @on(Button.Pressed, "#score_up_selected")
    async def handle_score_up_selected(self, event: Button.Pressed) -> None:
        """Score up all selected tasks."""
        await self._score_selected_tasks("up")

    @on(Button.Pressed, "#score_down_selected")
    async def handle_score_down_selected(self, event: Button.Pressed) -> None:
        """Score down all selected tasks."""
        await self._score_selected_tasks("down")

    @on(Button.Pressed, "#delete_selected")
    async def handle_delete_selected(self, event: Button.Pressed) -> None:
        """Delete all selected tasks."""
        await self._delete_selected_tasks()

    @on(OptionList.OptionSelected, "#tasks_list")
    async def handle_task_selection(self, event: OptionList.OptionSelected) -> None:
        """Handle user selecting a task from the list."""
        task_id = str(event.option.id)
        task = self.get_task(task_id)
        if not task:
            log.error(f"Task not found with ID: {task_id}")
            return

        if self.multiselect:
            # Toggle selection without recomposing
            if task_id in self.tasks_selected:
                self.tasks_selected.remove(task_id)
            else:
                self.tasks_selected.add(task_id)

            # Trigger recompose to update the visual styling
            self.mutate_reactive(TasksTab.current_mode)

            self.notify(f"Selected: {len(self.tasks_selected)} tasks")
            log.info(f"Total selected tasks: {len(self.tasks_selected)}")
        else:
            self.notify(f"{icons.INFO} Selected: {task.text}")

    @work
    async def refresh_data(self) -> None:
        """Asynchronously refresh task data from the vault."""
        log.info("TasksTab: refreshing data")

        try:
            await self.vault.update_tasks_only(force=True)
            self.tasks = self.vault.ensure_tasks_loaded()
            # Clear selections after refresh since task objects may have changed
            self.tasks_selected.clear()
            # Reset challenge filter if the selected challenge no longer exists
            if self.current_challenge_filter != "all":
                available_challenges = {
                    getattr(task, "challenge_shortname", None)
                    for task in self.tasks.all_tasks
                    if getattr(task, "challenge_shortname", None)
                }
                if self.current_challenge_filter not in available_challenges:
                    self.current_challenge_filter = "all"

            self.notify(
                f"{icons.CHECK} Tasks updated successfully!",
                title="Data Updated",
            )
        except Exception as e:
            log.error(f"TasksTab: Error refreshing data: {e}")
            self.notify(
                f"{icons.ERROR} Error updating tasks: {e}",
                title="Error",
                severity="error",
            )

    # ─── Task Actions & Workflows ──────────────────────────────────────────────────
    async def _score_selected_tasks(self, direction: str = "auto") -> None:
        """Score all selected tasks with given direction."""
        if not self.tasks_selected:
            return

        tasks_to_score = [self.get_task(task_id) for task_id in self.tasks_selected]
        tasks_to_score = [t for t in tasks_to_score if t is not None]

        await self.score_tasks(tasks_to_score, direction)

    async def _delete_selected_tasks(self) -> None:
        """Delete all selected tasks."""
        if not self.tasks_selected:
            return

        tasks_to_delete = [self.get_task(task_id) for task_id in self.tasks_selected]
        tasks_to_delete = [t for t in tasks_to_delete if t is not None]

        await self.delete_tasks(tasks_to_delete)

    async def score_tasks(
        self,
        tasks_to_score: list[AnyTask],
        direction: str = "auto",
    ) -> None:
        """Handle the workflow for scoring one or more tasks."""
        if not tasks_to_score:
            return

        success, error = 0, 0
        for task in tasks_to_score:
            try:
                # For habits, use the specified direction; for others, use "up" or "auto"
                if isinstance(task, TaskHabit):
                    score_direction = direction if direction in ["up", "down"] else "up"
                else:
                    score_direction = "up"  # Non-habits are typically scored "up"

                self.app.habitica_api.score_task_action(
                    task_id=task.id,
                    score_direction=score_direction,
                )
                success += 1
            except Exception as e:
                log.error(f"Error scoring task {task.id}: {e}")
                error += 1

        self.tasks_selected.clear()
        self.refresh_data()

        if error == 0:
            self.notify(f"{icons.CHECK} {success} tasks scored!", title="Tasks Scored")
        else:
            self.notify(
                f"{icons.WARNING} {success} scored, {error} failed.",
                title="Batch Complete",
            )

    async def delete_tasks(self, tasks_to_delete: list[AnyTask]) -> None:
        """Handle the workflow for deleting one or more tasks."""
        if not tasks_to_delete:
            return

        # Show confirmation
        preview = "\n".join(f"• {t.text}" for t in tasks_to_delete[:5])
        if len(tasks_to_delete) > 5:
            preview += f"\n... and {len(tasks_to_delete) - 5} more"

        q = f"Delete {len(tasks_to_delete)} tasks?\n\n{preview}"
        modal = GenericConfirmModal(
            question=q,
            confirm_variant="error",
            icon=icons.ERASE,
        )

        if not await self.app.push_screen(modal, wait_for_dismiss=True):
            return

        success, error = 0, 0
        for task in tasks_to_delete:
            try:
                self.app.habitica_api.delete_existing_task(task_id=task.id)
                success += 1
            except Exception as e:
                log.error(f"Error deleting task {task.id}: {e}")
                error += 1

        self.tasks_selected.clear()
        self.refresh_data()

        if error == 0:
            self.notify(
                f"{icons.CHECK} {success} tasks deleted!",
                title="Tasks Deleted",
            )
        else:
            self.notify(
                f"{icons.WARNING} {success} deleted, {error} failed.",
                title="Batch Complete",
            )

    @work
    async def action_score_task(self) -> None:
        """Score the currently selected task (smart direction)."""
        await self._action_score_task("auto")

    @work
    async def action_score_up_task(self) -> None:
        """Score up the currently selected task(s)."""
        await self._action_score_task("up")

    @work
    async def action_score_down_task(self) -> None:
        """Score down the currently selected task(s)."""
        await self._action_score_task("down")

    async def _action_score_task(self, direction: str) -> None:
        """Score task(s) with the given direction."""
        if self.multiselect and self.tasks_selected:
            await self._score_selected_tasks(direction)
            return

        task_list = self.query_one("#tasks_list", OptionList)
        if task_list.highlighted is not None:
            option = task_list.get_option_at_index(task_list.highlighted)
            if option and option.id:
                task = self.get_task(str(option.id))
                if task:
                    await self.score_tasks([task], direction)

    @work
    async def action_delete_task(self) -> None:
        """Delete the currently selected task(s)."""
        if self.multiselect and self.tasks_selected:
            await self._delete_selected_tasks()
            return

        # Single task selection
        task_list = self.query_one("#tasks_list", OptionList)
        if task_list.highlighted is not None:
            option = task_list.get_option_at_index(task_list.highlighted)
            if option and option.id:
                task = self.get_task(str(option.id))
                if task:
                    await self.delete_tasks([task])

    # ─── Mode & View Actions ───────────────────────────────────────────────────────
    def action_tasks_dailies(self) -> None:
        self.current_mode = "dailies"

    def action_tasks_todos(self) -> None:
        self.current_mode = "todos"

    def action_tasks_habits(self) -> None:
        self.current_mode = "habits"

    def action_tasks_rewards(self) -> None:
        self.current_mode = "rewards"

    def action_tasks_all(self) -> None:
        self.current_mode = "all"

    # Multiselect actions
    def action_toggle_multiselect(self) -> None:
        """Toggle multiselect mode."""
        self.multiselect = not self.multiselect
        self.notify(f"Multiselect {'enabled' if self.multiselect else 'disabled'}")
        if not self.multiselect:
            self.tasks_selected.clear()

    def action_clear_selection(self) -> None:
        if self.tasks_selected:
            self.tasks_selected.clear()
            # Trigger recompose to update visual styling
            self.mutate_reactive(TasksTab.current_mode)
            self.notify("Selection cleared")
            log.info("Task selections cleared")
        elif self.multiselect:
            self.action_toggle_multiselect()

    def action_refresh_data(self) -> None:
        self.refresh_data()
