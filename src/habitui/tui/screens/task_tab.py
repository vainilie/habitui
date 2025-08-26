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
    Static,
    ListItem,
    ListView,
)
from textual.reactive import reactive
from textual.containers import Vertical, Horizontal

from habitui.ui import icons, parse_emoji
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
        Binding("y", "tag_tasks_workflow", "TagTask"),
    ]

    tasks: reactive[TaskCollection] = reactive(None, recompose=True)
    current_mode: reactive[str] = reactive("dailies", recompose=True)
    current_sort: reactive[str] = reactive("default", recompose=True)
    current_filter: reactive[str] = reactive("all", recompose=True)
    current_challenge_filter: reactive[str] = reactive("all", recompose=True)
    current_tag_filter: reactive[str] = reactive("all", recompose=True)
    multiselect: reactive[bool] = reactive(False, recompose=True)
    tasks_selected: reactive[set[str]] = reactive(
        set,
        init=False,
    )

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

        # Tag filter options - will be populated dynamically
        self.tag_filter_options = [("All Tags", "all")]

        log.info("TasksTab: initialized")

    def _sanitize_id(self, task_id: str) -> str:
        """Convert a UUID to a valid Textual widget ID."""
        # Replace hyphens with underscores and ensure it starts with a letter
        return f"task_{task_id.replace('-', '_')}"

    def _extract_task_id(self, widget_id: str) -> str:
        """Extract the original UUID from a sanitized widget ID."""
        # Remove the 'task_' prefix and convert underscores back to hyphens
        if widget_id.startswith("task_"):
            return widget_id[5:].replace("_", "-")
        return widget_id

    def get_task(self, task_id: str) -> AnyTask | None:
        """Get a task by its ID from the main task collection."""
        return self.tasks.get_task_by_id(task_id)

    def format_task_option(self, task: AnyTask) -> ListItem:
        """Format a single task model into a rich, selectable ListItem."""
        grid = Table(expand=True, padding=(0, 1), show_header=False, show_lines=True)
        grid.add_column(ratio=1, justify="right")
        grid.add_column(ratio=3)
        grid.add_column(ratio=1, justify="right")

        task_name = getattr(task, "text", "Unnamed Task")

        # Status icon based on task state
        status_icon = icons.BLANK_CIRCLE_O
        if getattr(task, "completed", False):
            status_icon = icons.CHECK
        elif getattr(task, "isDue", False) or getattr(task, "due_today", False):
            status_icon = icons.EXCLAMATION

        display_name = f"[b]{parse_emoji(task_name)}[/b]"

        # Add challenge indicator if applicable
        challenge_shortname = getattr(task, "challenge_shortname", None)
        display_challenge = f"{icons.USER}[dim] Personal[/dim]"
        if challenge_shortname:
            display_challenge = (
                f"{icons.TROPHY}[dim] {parse_emoji(challenge_shortname)}[/dim]"
            )

        # Add tags indicator if applicable
        display_tags = ""
        tags = getattr(task, "tags", None)
        if tags and isinstance(tags, list):
            # Get tag collection to resolve UUIDs to names
            tag_collection = self.vault.ensure_tags_loaded()

            tag_names = []
            for tag_uuid in tags:  # Show first 2 tags
                tag_complex = tag_collection.get_by_id(tag_uuid)
                if tag_complex:
                    tag_name = getattr(tag_complex, "name", tag_uuid)
                    tag_names.append(parse_emoji(tag_name))

            if tag_names:
                tag_str = ", ".join(tag_names)
                display_tags = f"[dim]{tag_str}[/dim]"

        grid.add_row(status_icon, display_name, f"[dim]{task.type}[/dim]")
        grid.add_row("", display_challenge, "[dim][/dim]")
        grid.add_row(
            "",
            display_tags,
            f"P: {task.priority} • V: {round(task.value)}",
        )

        notes = getattr(task, "notes", "") or ""
        notes_preview = (
            (notes[:200] + "...") if len(notes) > 200 else notes or "No notes"
        )

        grid.add_row(
            "",
            f"[dim]{parse_emoji(notes_preview)}[/]",
            f"[dim]{DateTimeHandler(timestamp=task.created_at).format_time_difference()}[/dim]",
        )

        # Use sanitized ID for the widget but store original task ID for data operations
        sanitized_id = self._sanitize_id(task.id)
        item = ListItem(Static(grid), id=sanitized_id)

        # Add selected class if task is selected (using original task.id for comparison)
        if task.id in self.tasks_selected:
            item.add_class("task-selected")

        return item

    def _get_tag_filter_options(self) -> list[tuple[str, str]]:
        """Get available tags for filtering."""
        options = [("All Tags", "all")]

        # Collect all unique tag UUIDs from all tasks
        tag_uuids = set()
        for task in self.tasks.all_tasks:
            tags = getattr(task, "tags", None)
            if tags:
                # tags should be a list of UUIDs
                if isinstance(tags, list):
                    tag_uuids.update(tags)

        # Get tag collection and resolve UUIDs to names
        tag_collection = self.vault.ensure_tags_loaded()

        # Add each tag as a filter option
        for tag_uuid in sorted(tag_uuids):
            if tag_uuid:  # Skip empty UUIDs
                tag_complex = tag_collection.get_by_id(tag_uuid)
                if tag_complex:
                    tag_name = getattr(tag_complex, "name", tag_uuid)
                    options.append((parse_emoji(tag_name), tag_uuid))

        return options

    def _get_challenge_filter_options(self) -> list[tuple[str, str]]:
        """Get available challenges for filtering (by challenge_id)."""
        options = [("All Challenges", "all")]

        # 1. Coleccionar challenge_id -> shortname
        challenge_map: dict[str, str] = {}
        for task in self.tasks.all_tasks:
            cid = getattr(task, "challenge_id", None)
            cname = getattr(task, "challenge_shortname", None)
            if cid and cid not in challenge_map:
                challenge_map[cid] = cname or cid

        for cid, cname in sorted(challenge_map.items(), key=lambda x: x[1].lower()):
            options.append((parse_emoji(cname), cid))

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
                if getattr(t, "challenge_id", None) == self.current_challenge_filter
            ]

        # Apply tag-specific filter
        if self.current_tag_filter != "all":

            def task_has_tag(task: AnyTask, target_tag_uuid: str) -> bool:
                tags = getattr(task, "tags", None)
                if not tags or not isinstance(tags, list):
                    return False
                return target_tag_uuid in tags

            tasks_list = [
                t for t in tasks_list if task_has_tag(t, self.current_tag_filter)
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

            # Tag filter - only show if there are tags
            tag_options = self._get_tag_filter_options()
            if len(tag_options) > 1:  # More than just "All Tags"
                yield Select(
                    tag_options,
                    value=self.current_tag_filter,
                    id="tag_filter_selector",
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

        yield ListView(
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

    @on(Select.Changed, "#tag_filter_selector")
    def handle_tag_filter_change(self, event: Select.Changed) -> None:
        """Change tag filter when dropdown is changed."""
        if isinstance(event.value, str):
            self.current_tag_filter = event.value

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

    @on(ListView.Selected, "#tasks_list")
    async def handle_task_selection(self, event: ListView.Selected) -> None:
        """Handle user selecting a task from the list."""
        # Extract original task ID from sanitized widget ID
        sanitized_id = str(event.item.id)
        task_id = self._extract_task_id(sanitized_id)
        task = self.get_task(task_id)
        if not task:
            log.error(f"Task not found with ID: {task_id}")
            return

        if self.multiselect:
            # Toggle selection and CSS class (using original task.id)
            if task_id in self.tasks_selected:
                self.tasks_selected.remove(task_id)
                event.item.remove_class("task-selected")
            else:
                self.tasks_selected.add(task_id)
                event.item.add_class("task-selected")

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
                    getattr(task, "challenge_id", None)
                    for task in self.tasks.all_tasks
                    if getattr(task, "challenge_id", None)
                }
                if self.current_challenge_filter not in available_challenges:
                    self.current_challenge_filter = "all"

            # Reset tag filter if the selected tag no longer exists
            if self.current_tag_filter != "all":
                available_tag_uuids = set()
                for task in self.tasks.all_tasks:
                    tags = getattr(task, "tags", None)
                    if tags and isinstance(tags, list):
                        available_tag_uuids.update(tags)
                if self.current_tag_filter not in available_tag_uuids:
                    self.current_tag_filter = "all"

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

        self.delete_tasks(tasks_to_delete)

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

    @work
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

        # Single task selection
        task_list = self.query_one("#tasks_list", ListView)
        if task_list.index is not None:
            try:
                selected_item = task_list.highlighted_child
                if selected_item and selected_item.id:
                    # Extract original task ID from sanitized widget ID
                    sanitized_id = str(selected_item.id)
                    task_id = self._extract_task_id(sanitized_id)
                    task = self.get_task(task_id)
                    if task:
                        await self.score_tasks([task], direction)
            except (IndexError, AttributeError):
                pass

    @work
    async def action_delete_task(self) -> None:
        """Delete the currently selected task(s)."""
        if self.multiselect and self.tasks_selected:
            await self._delete_selected_tasks()
            return

        # Single task selection
        task_list = self.query_one("#tasks_list", ListView)
        if task_list.index is not None:
            try:
                selected_item = task_list.highlighted_child
                if selected_item and selected_item.id:
                    # Extract original task ID from sanitized widget ID
                    sanitized_id = str(selected_item.id)
                    task_id = self._extract_task_id(sanitized_id)
                    task = self.get_task(task_id)
                    if task:
                        self.delete_tasks([task])
            except (IndexError, AttributeError):
                pass

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
            self.notify("Selection cleared")
            log.info("Task selections cleared")
        elif self.multiselect:
            self.action_toggle_multiselect()

    def action_refresh_data(self) -> None:
        self.refresh_data()

    def action_tag_tasks_workflow(self) -> None:
        """Initiate the tag creation workflow."""
        self._cleanup_and_retag_workflow()

    @work
    async def _cleanup_and_retag_workflow(self) -> None:
        """
        Limpia todas las parent tags y no_attr, luego reclasifica basado en tags hijas
        """
        str_tag = self.vault.tags.get_str_parent()
        per_tag = self.vault.tags.get_per_parent()
        int_tag = self.vault.tags.get_int_parent()
        con_tag = self.vault.tags.get_con_parent()
        no_attr_tag = self.vault.tags.get_no_attr_parent()

        # Listas para el proceso de limpieza
        tasks_to_cleanup = []

        # Listas para re-clasificación
        add_str_tag = []
        add_con_tag = []
        add_int_tag = []
        add_per_tag = []
        add_no_attr = []

        # PASO 1: Identificar tareas que necesitan limpieza
        parent_tag_ids = {
            str_tag.id,
            per_tag.id,
            int_tag.id,
            con_tag.id,
            no_attr_tag.id,
        }

        for task in self.tasks:
            has_parent_tags = any(tag_id in parent_tag_ids for tag_id in task.tags)
            if has_parent_tags:
                tasks_to_cleanup.append(task.id)

        log.info(f"Found {len(tasks_to_cleanup)} tasks that need cleanup")

        # PASO 2: Analizar clasificación basada en tags hijas
        for task in self.tasks:
            task_attribute = None
            child_tags_found = []

            # Buscar tags hijas para determinar el atributo
            for tag_id in task.tags:
                if tag_id not in parent_tag_ids:  # Ignorar parent tags
                    tag_data = self.vault.tags.get_by_id(tag_id)
                    if hasattr(tag_data, "attribute") and tag_data.attribute:
                        child_tags_found.append((
                            tag_id,
                            tag_data.attribute,
                            tag_data.name,
                        ))
                        if not task_attribute:  # Usar el primer atributo encontrado
                            task_attribute = tag_data.attribute

            # Clasificar según el atributo encontrado
            if task_attribute == "str":
                add_str_tag.append(task.id)
            elif task_attribute == "int":
                add_int_tag.append(task.id)
            elif task_attribute == "con":
                add_con_tag.append(task.id)
            elif task_attribute == "per":
                add_per_tag.append(task.id)
            else:
                add_no_attr.append(task.id)

            # Log para debug
            if child_tags_found:
                log.info(
                    f"Task {task.id}: Found child tags: {child_tags_found} -> Attribute: {task_attribute}"
                )
            else:
                log.info(
                    f"Task {task.id}: No child tags with attributes found -> no_attr"
                )

        # Mostrar resumen antes de confirmar
        total_cleanup = len(tasks_to_cleanup)
        total_retag = (
            len(add_str_tag)
            + len(add_con_tag)
            + len(add_per_tag)
            + len(add_int_tag)
            + len(add_no_attr)
        )

        summary = f"""
    CLEANUP & RETAG SUMMARY:
    ========================
    Tasks to cleanup: {total_cleanup}
    Tasks to re-tag:
    - STR: {len(add_str_tag)}
    - INT: {len(add_int_tag)}
    - CON: {len(add_con_tag)}
    - PER: {len(add_per_tag)}
    - NO_ATTR: {len(add_no_attr)}

    Total operations: {total_cleanup + total_retag}
    """

        log.info(summary)

        confirm = GenericConfirmModal(
            question=f"CLEANUP {total_cleanup} tasks and RE-TAG {total_retag} tasks?",
            title="Cleanup & Retag All Tasks",
            confirm_text="Yes, do it!",
            cancel_text="Cancel",
            confirm_variant="warning",
            icon=icons.QUESTION,
        )

        confirmed = await self.app.push_screen(confirm, wait_for_dismiss=True)

        if confirmed:
            # Ejecutar limpieza y re-etiquetado
            await self._execute_cleanup_and_retag(
                tasks_to_cleanup,
                {
                    "str": add_str_tag,
                    "int": add_int_tag,
                    "con": add_con_tag,
                    "per": add_per_tag,
                    "non": add_no_attr,
                },
            )

    async def _execute_cleanup_and_retag(
        self, cleanup_tasks: list, retag_data: dict
    ) -> None:
        """
        Ejecuta la limpieza y re-etiquetado
        """
        try:
            str_tag = self.vault.tags.get_str_parent()
            per_tag = self.vault.tags.get_per_parent()
            int_tag = self.vault.tags.get_int_parent()
            con_tag = self.vault.tags.get_con_parent()
            no_attr_tag = self.vault.tags.get_no_attr_parent()

            parent_tags = [str_tag, per_tag, int_tag, con_tag, no_attr_tag]

            log.info(f"{icons.RELOAD} Starting cleanup process...")

            # PASO 1: LIMPIEZA - Remover todas las parent tags
            for task_id in cleanup_tasks:
                for parent_tag in parent_tags:
                    try:
                        self.app.habitica_api.remove_tag_from_task(
                            task_id=task_id,
                            tag_id_to_remove=parent_tag.id,
                        )
                    except Exception as e:
                        log.warning(
                            f"Could not remove tag {parent_tag.id} from task {task_id}: {e}"
                        )

            log.info(f"{icons.CHECK} Cleanup completed. Starting re-tagging...")

            # PASO 2: RE-ETIQUETADO
            # STR tasks
            for task_id in retag_data["str"]:
                self.app.habitica_api.add_tag_to_task(
                    task_id=task_id,
                    tag_id_to_add=str_tag.id,
                )
                self.app.habitica_api.assign_task_attribute(
                    task_id=task_id,
                    task_attribute="str",
                )

            # INT tasks
            for task_id in retag_data["int"]:
                self.app.habitica_api.add_tag_to_task(
                    task_id=task_id,
                    tag_id_to_add=int_tag.id,
                )
                self.app.habitica_api.assign_task_attribute(
                    task_id=task_id,
                    task_attribute="int",
                )

            # CON tasks
            for task_id in retag_data["con"]:
                self.app.habitica_api.add_tag_to_task(
                    task_id=task_id,
                    tag_id_to_add=con_tag.id,
                )
                self.app.habitica_api.assign_task_attribute(
                    task_id=task_id,
                    task_attribute="con",
                )

            # PER tasks
            for task_id in retag_data["per"]:
                self.app.habitica_api.add_tag_to_task(
                    task_id=task_id,
                    tag_id_to_add=per_tag.id,
                )
                self.app.habitica_api.assign_task_attribute(
                    task_id=task_id,
                    task_attribute="per",
                )

            # NO_ATTR tasks
            for task_id in retag_data["non"]:
                self.app.habitica_api.add_tag_to_task(
                    task_id=task_id,
                    tag_id_to_add=no_attr_tag.id,
                )
                # No asignar atributo para estas tareas

            log.info(f"{icons.CHECK} Re-tagging completed successfully!")
            self.notify(
                f"{icons.CHECK} Cleanup and re-tagging completed!",
                title="Success",
                severity="information",
            )

        except Exception as e:
            log.error(f"{icons.ERROR} Error during cleanup and retag: {e}")
            self.notify(
                f"{icons.ERROR} Failed during cleanup/retag: {e!s}",
                title="Error",
                severity="error",
            )
