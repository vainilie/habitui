from __future__ import annotations

import typing
from typing import Any
import inspect
from dataclasses import dataclass

from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown

from textual import on, work
from textual.binding import Binding
from textual.widgets import Label, Button, Select, ListItem, ListView
from textual.reactive import reactive
from textual.containers import Vertical, Horizontal

from habitui.ui import icons, parse_emoji
from habitui.utils import DateTimeHandler
from habitui.tui.generic import BaseTab, GenericConfirmModal
from habitui.custom_logger import log
from habitui.core.models.tag_model import TagComplex
from habitui.core.models.base_enums import TagsTrait, DailyStatus
from habitui.core.models.task_model import (
    AnyTask,
    TaskTodo,
    TaskDaily,
    TaskHabit,
    TaskCollection,
)


if typing.TYPE_CHECKING:
    from textual.app import ComposeResult

    from habitui.tui.main_app import HabiTUI


# ─── Data Classes ──────────────────────────────────────────────────────────────
@dataclass
class TagConfig:
    """Configuration for tag display and attributes."""

    trait: TagsTrait
    icon: str
    attribute: str | None = None


# ─── Main Widget ───────────────────────────────────────────────────────────────
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

    TAG_CONFIGS = {
        TagsTrait.LEGACY: TagConfig(TagsTrait.LEGACY, icons.LEGACY),
        TagsTrait.CHALLENGE: TagConfig(TagsTrait.CHALLENGE, icons.TROPHY),
        TagsTrait.PERCEPTION: TagConfig(TagsTrait.PERCEPTION, icons.DROP, "per"),
        TagsTrait.STRENGTH: TagConfig(TagsTrait.STRENGTH, icons.FIRE_O, "str"),
        TagsTrait.INTELLIGENCE: TagConfig(TagsTrait.INTELLIGENCE, icons.AIR, "int"),
        TagsTrait.CONSTITUTION: TagConfig(TagsTrait.CONSTITUTION, icons.LEAVES, "con"),
        TagsTrait.NO_ATTRIBUTE: TagConfig(TagsTrait.NO_ATTRIBUTE, icons.ANCHOR),
    }

    tasks: reactive[TaskCollection] = reactive(None, recompose=True)
    current_mode: reactive[str] = reactive("dailies", recompose=True)
    current_sort: reactive[str] = reactive("default", recompose=True)
    current_filter: reactive[str] = reactive("all", recompose=True)
    current_challenge_filter: reactive[str] = reactive("all", recompose=True)
    current_tag_filter: reactive[str] = reactive("all", recompose=True)
    multiselect: reactive[bool] = reactive(False, recompose=True)
    tasks_selected: reactive[set[str]] = reactive(set, init=False)

    def __init__(self) -> None:
        """Initialize the TasksTab."""
        super().__init__()
        self.app: HabiTUI
        self.tasks = self.vault.ensure_tasks_loaded()

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

        self.filter_options = [
            ("All Tasks", "all"),
            ("Challenge Tasks", "challenge"),
            ("Non-Challenge", "non_challenge"),
            ("Completed", "completed"),
            ("Incomplete", "incomplete"),
            ("Due Today", "due_today"),
        ]

        self.challenge_filter_options = [("All Challenges", "all")]
        self.tag_filter_options = [("All Tags", "all")]

        log.info("TasksTab: initialized")

    # ─── Internal Helpers ──────────────────────────────────────────────────────────
    def _sanitize_id(self, task_id: str) -> str:
        """Convert a UUID to a valid Textual widget ID."""
        return f"task_{task_id.replace('-', '_')}"

    def _extract_task_id(self, widget_id: str) -> str:
        """Extract the original UUID from a sanitized widget ID."""
        if widget_id.startswith("task_"):
            return widget_id[5:].replace("_", "-")

        return widget_id

    def get_task(self, task_id: str) -> AnyTask | None:
        """Get a task by its ID from the main task collection."""
        return self.tasks.get_task_by_id(task_id)

    def _get_tag_display_name(self, tag_item: TagComplex) -> str | None:
        """Get display name for a tag based on its type and trait."""
        if tag_item.is_parent():
            config = self.TAG_CONFIGS.get(tag_item.trait)
            return config.icon if config else None

        if tag_item.is_subtag():
            return parse_emoji(tag_item.display_name)

        if tag_item.is_base():
            return parse_emoji(tag_item.name)

        return None

    def _format_status(self, status: DailyStatus) -> str | DailyStatus:
        """Format the status of a daily task with an icon."""
        status_map = {
            DailyStatus.COMPLETED_TODAY: icons.CHECK,
            DailyStatus.DUE_TODAY: icons.BLANK,
            DailyStatus.READY_TO_COMPLETE: icons.HALF_CIRCLE,
            DailyStatus.INACTIVE: icons.SLEEP,
            DailyStatus.DUE_YESTERDAY: icons.BACK,
        }

        return status_map.get(status, status)

    def _format_challenge_display(self, task: AnyTask) -> str:
        """Format challenge display for a task."""
        challenge_display = icons.MEDAL if task.challenge else ""

        if task.challenge_shortname:
            challenge_display += parse_emoji(task.challenge_shortname)

        return challenge_display

    def format_tags(self, tag_list: list[str]) -> str:
        """Format tags using configuration mapping."""
        tags = self.vault.ensure_tags_loaded()
        tag_names = []

        for tag_uuid in tag_list:
            tag_item = tags.get_by_id(tag_uuid)
            if not tag_item:
                continue

            tag_name = self._get_tag_display_name(tag_item)
            if tag_name:
                tag_names.append(tag_name)

        if icons.LEGACY in tag_names and icons.TROPHY in tag_names:
            tag_names.remove(icons.TROPHY)

        tag_names.sort()

        tag_names_clean = [
            f"[white][/][blue on white]{tag} [/][white][/]" for tag in tag_names
        ]

        return "".join(tag_names_clean)

    def _extract_task_display_data(self, task: AnyTask) -> dict[str, Any]:
        """Extract and format all display data for a task."""
        data = {
            "text": parse_emoji(task.text).replace("#", ""),
            "notes": parse_emoji(task.notes),
            "attribute": self.TAG_CONFIGS.get(TagsTrait(task.attribute[0:3])).icon,
            "status": self._format_status(task.status)
            if isinstance(task.status, DailyStatus)
            else task.status,
            "type": task.type,
            "value": round(task.value),
            "priority": round(task.priority),
            "tags": self.format_tags(task.tags),
            "linked": f"[red]{icons.UNLINK}[/]" if task.task_broken else "",
            "ch_linked": f"[red]{icons.MEGAPHONE}[/red]"
            if task.task_broken
            else icons.MEGAPHONE,
            "challenge": self._format_challenge_display(task),
            "created": DateTimeHandler(
                timestamp=task.created_at,
            ).format_time_difference(),
        }

        return data

    def format_task_option(self, task: AnyTask) -> ListItem:
        """Format a task for display in the list."""
        task_data = self._extract_task_display_data(task)

        main_grid = Table(
            expand=False,
            padding=(0, 1),
            show_header=False,
            show_lines=True,
        )
        main_grid.add_column(ratio=1, justify="right")
        main_grid.add_column(ratio=3)

        task_grid = Table.grid(expand=False, padding=(0, 1))
        task_grid.add_column()
        task_grid.add_row(Markdown(task_data["text"]), style="bold")
        task_grid.add_row(task_data["tags"], style="dim")
        task_grid.add_row(
            f"{task_data['linked']} {task_data['ch_linked']}",
            style="dim",
        )
        task_grid.add_row(Panel(Markdown(task_data["notes"])))
        task_grid.add_row(task_data["attribute"])
        task_grid.add_row(f"{task_data['priority']} {task_data['value']}", style="dim")

        if isinstance(task, TaskDaily):
            next_due_ts = task.next_due[0] if task.completed else task.next_due[1]
            next_due_str = DateTimeHandler(
                timestamp=next_due_ts,
            ).format_time_difference()
            task_grid.add_row(f"{task.user_damage}, {task.party_damage}")
            task_grid.add_row(f"{task.streak}, {next_due_str}")

        if isinstance(task, TaskTodo):
            next_due_str = (
                DateTimeHandler(timestamp=task.due_date).format_time_difference()
                if task.due_date
                else ""
            )
            task_grid.add_row(f"{task.checklist}")

        if isinstance(task, TaskHabit):
            task_grid.add_row(f"{task.counter_up} - {task.counter_down}")
            task_grid.add_row(f"{task.frequency}")

        main_grid.add_row(task_data["status"], task_grid)
        sanitized_id = self._sanitize_id(task.id)

        item = ListItem(
            Label(main_grid, markup=True),
            id=sanitized_id,
            markup=True,
            classes="task-item",
        )

        if task.id in self.tasks_selected:
            item.add_class("task-selected")

        return item

    # ─── Data Filtering and Sorting ────────────────────────────────────────────────
    def _get_tag_filter_options(self) -> list[tuple[str, str]]:
        """Get available tags for filtering."""
        options = [("All Tags", "all")]
        tag_uuids = set()

        for task in self.tasks.all_tasks:
            tags = getattr(task, "tags", None)
            if isinstance(tags, list):
                tag_uuids.update(tags)

        tag_collection = self.vault.ensure_tags_loaded()

        for tag_uuid in sorted(tag_uuids):
            if tag_uuid:
                tag_complex = tag_collection.get_by_id(tag_uuid)
                if tag_complex:
                    tag_name = getattr(tag_complex, "name", tag_uuid)
                    options.append((parse_emoji(tag_name), tag_uuid))

        return options

    def _get_challenge_filter_options(self) -> list[tuple[str, str]]:
        """Get available challenges for filtering by challenge_id."""
        options = [("All Challenges", "all")]
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
        mode_to_attr = {
            "all": "all_tasks",
            "dailies": "dailys",
            "todos": "todos",
            "habits": "habits",
            "rewards": "rewards",
        }
        attr_name = mode_to_attr.get(self.current_mode, "all_tasks")
        tasks_list = getattr(self.tasks, attr_name, [])

        filtered_tasks = self._filter_tasks(tasks_list)

        return self._sort_tasks(filtered_tasks)

    def _filter_tasks(self, tasks_list: list[AnyTask]) -> list[AnyTask]:
        """Filter tasks based on current filter settings."""
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

        if self.current_challenge_filter != "all":
            tasks_list = [
                t
                for t in tasks_list
                if getattr(t, "challenge_id", None) == self.current_challenge_filter
            ]

        if self.current_tag_filter != "all":
            tasks_list = [
                t
                for t in tasks_list
                if self.current_tag_filter in getattr(t, "tags", [])
            ]

        return tasks_list

    def _sort_tasks(self, tasks_list: list[AnyTask]) -> list[AnyTask]:
        """Sort a list of task models based on the current sort mode."""
        sort_key_map = {
            "name_asc": (lambda t: t.text.lower(), False),
            "name_desc": (lambda t: t.text.lower(), True),
            "priority_desc": (lambda t: t.priority, True),
            "priority_asc": (lambda t: t.priority, False),
            "value_desc": (lambda t: t.value, True),
            "value_asc": (lambda t: t.value, False),
            "created_desc": (lambda t: t.created_at, True),
            "created_asc": (lambda t: t.created_at, False),
        }

        if self.current_sort in sort_key_map:
            key, reverse = sort_key_map[self.current_sort]
            return sorted(tasks_list, key=key, reverse=reverse)

        return tasks_list

    # ─── UI Composition ────────────────────────────────────────────────────────────
    def compose(self) -> ComposeResult:
        """Compose the dynamic UI for the tasks tab."""
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

            challenge_options = self._get_challenge_filter_options()
            if len(challenge_options) > 1:
                yield Select(
                    challenge_options,
                    value=self.current_challenge_filter,
                    id="challenge_filter_selector",
                    classes="control-select",
                )

            tag_options = self._get_tag_filter_options()
            if len(tag_options) > 1:
                yield Select(
                    tag_options,
                    value=self.current_tag_filter,
                    id="tag_filter_selector",
                    classes="control-select",
                )

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
    async def handle_score_selected(self) -> None:
        """Score all selected tasks."""
        await self._score_selected_tasks("auto")

    @on(Button.Pressed, "#score_up_selected")
    async def handle_score_up_selected(self) -> None:
        """Score up all selected tasks."""
        await self._score_selected_tasks("up")

    @on(Button.Pressed, "#score_down_selected")
    async def handle_score_down_selected(self) -> None:
        """Score down all selected tasks."""
        await self._score_selected_tasks("down")

    @on(Button.Pressed, "#delete_selected")
    async def handle_delete_selected(self) -> None:
        """Delete all selected tasks."""
        await self._delete_selected_tasks()

    @on(ListView.Selected, "#tasks_list")
    async def handle_task_selection(self, event: ListView.Selected) -> None:
        """Handle user selecting a task from the list."""
        sanitized_id = str(event.item.id)
        task_id = self._extract_task_id(sanitized_id)
        task = self.get_task(task_id)

        if not task:
            log.error(f"Task not found with ID: {task_id}")

            return

        if self.multiselect:
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
            self.tasks_selected.clear()

            available_challenges = {
                getattr(t, "challenge_id", None) for t in self.tasks.all_tasks
            }
            if (
                self.current_challenge_filter != "all"
                and self.current_challenge_filter not in available_challenges
            ):
                self.current_challenge_filter = "all"

            available_tags = {
                tag for t in self.tasks.all_tasks for tag in getattr(t, "tags", [])
            }
            if (
                self.current_tag_filter != "all"
                and self.current_tag_filter not in available_tags
            ):
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
                score_direction = direction if direction in {"up", "down"} else "up"
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

        preview = "\n".join(f"• {t.text}" for t in tasks_to_delete[:5])

        if len(tasks_to_delete) > 5:
            preview += f"\n... and {len(tasks_to_delete) - 5} more"

        question = f"Delete {len(tasks_to_delete)} tasks?\n\n{preview}"
        modal = GenericConfirmModal(
            question=question,
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

    async def _action_score_task(self, *args, **kwargs) -> None:
        """Score task(s) with the given direction."""
        # --- CÓDIGO DE DIAGNÓSTICO TEMPORAL ---
        direction = kwargs.get("direction")
        if not direction and args:
            direction = args[0]

        # Si 'direction' sigue sin existir, hemos encontrado la llamada incorrecta.
        if not direction:
            log.error(
                "!!! _action_score_task FUE LLAMADA INCORRECTAMENTE !!!",
            )
            log.error(f"Argumentos recibidos (args): {args}")
            log.error(f"Argumentos recibidos (kwargs): {kwargs}")

            # Imprime la pila de llamadas para ver el origen
            log.warning("Rastreando al llamador:")
            for frame in inspect.stack():
                # Muestra el archivo, la línea y la función que originó la llamada
                log.warning(
                    f" -> Origen: {frame.filename}:{frame.lineno} en la función `{frame.function}`",
                )
            return  # Detenemos la ejecución aquí para evitar más errores
        # --- FIN DEL CÓDIGO DE DIAGNÓSTICO ---

        # El resto de tu lógica original va aquí...
        if self.multiselect and self.tasks_selected:
            await self._score_selected_tasks(direction=direction)

            return

        task_list = self.query_one("#tasks_list", ListView)

        if task_list.index is not None and (
            selected_item := task_list.highlighted_child
        ):
            sanitized_id = str(selected_item.id)
            task_id = self._extract_task_id(sanitized_id)
            if task := self.get_task(task_id):
                await self.score_tasks([task], direction)

    @work
    async def action_score_task(self) -> None:
        """Score the currently selected task (smart direction)."""
        await self._action_score_task(direction="auto")

    @work
    async def action_score_up_task(self) -> None:
        """Score up the currently selected task(s)."""
        await self._action_score_task(direction="up")

    @work
    async def action_score_down_task(self) -> None:
        """Score down the currently selected task(s)."""
        await self._action_score_task(direction="down")

    @work
    async def action_delete_task(self) -> None:
        """Delete the currently selected task(s)."""
        if self.multiselect and self.tasks_selected:
            await self._delete_selected_tasks()

            return

        task_list = self.query_one("#tasks_list", ListView)

        if task_list.index is not None and (
            selected_item := task_list.highlighted_child
        ):
            sanitized_id = str(selected_item.id)
            task_id = self._extract_task_id(sanitized_id)
            if task := self.get_task(task_id):
                self.delete_tasks([task])

    # ─── Mode & View Actions ───────────────────────────────────────────────────────
    def action_tasks_dailies(self) -> None:
        """Switch view to Dailies."""
        self.current_mode = "dailies"

    def action_tasks_todos(self) -> None:
        """Switch view to Todos."""
        self.current_mode = "todos"

    def action_tasks_habits(self) -> None:
        """Switch view to Habits."""
        self.current_mode = "habits"

    def action_tasks_rewards(self) -> None:
        """Switch view to Rewards."""
        self.current_mode = "rewards"

    def action_tasks_all(self) -> None:
        """Switch view to All Tasks."""
        self.current_mode = "all"

    def action_toggle_multiselect(self) -> None:
        """Toggle multiselect mode."""
        self.multiselect = not self.multiselect
        self.notify(f"Multiselect {'enabled' if self.multiselect else 'disabled'}")

        if not self.multiselect:
            self.tasks_selected.clear()

    def action_clear_selection(self) -> None:
        """Clear task selection or disable multiselect."""
        if self.tasks_selected:
            self.tasks_selected.clear()
            self.notify("Selection cleared")
            log.info("Task selections cleared")
        elif self.multiselect:
            self.action_toggle_multiselect()

    def action_refresh_data(self) -> None:
        """Trigger a manual data refresh."""
        self.refresh_data()

    def action_tag_tasks_workflow(self) -> None:
        """Initiate the tag cleanup and re-assignment workflow."""
        self._cleanup_and_retag_workflow()

    # ─── Bulk Tagging Workflow ─────────────────────────────────────────────────────
    @work
    async def _cleanup_and_retag_workflow(self) -> None:
        """Clean all parent/no_attr tags, then reclassify tasks based on child tags."""
        tags = self.vault.tags
        parent_tags = {
            tags.get_str_parent().id,
            tags.get_per_parent().id,
            tags.get_int_parent().id,
            tags.get_con_parent().id,
            tags.get_no_attr_parent().id,
        }

        tasks_to_cleanup = {
            task.id
            for task in self.tasks
            if any(tag in parent_tags for tag in task.tags)
        }
        retag_map = {"str": [], "int": [], "con": [], "per": [], "non": []}

        for task in self.tasks:
            task_attribute = None
            for tag_id in task.tags:
                if tag_id not in parent_tags:
                    if tag_data := tags.get_by_id(tag_id):
                        if hasattr(tag_data, "attribute") and tag_data.attribute:
                            task_attribute = tag_data.attribute
                            break  # Use the first attribute found

            if task_attribute in retag_map:
                retag_map[task_attribute].append(task.id)
            else:
                retag_map["non"].append(task.id)

        summary = f"""
        CLEANUP & RETAG SUMMARY:
        ========================
        Tasks to cleanup: {len(tasks_to_cleanup)}
        Tasks to re-tag:
        - STR: {len(retag_map["str"])}
        - INT: {len(retag_map["int"])}
        - CON: {len(retag_map["con"])}
        - PER: {len(retag_map["per"])}
        - NO_ATTR: {len(retag_map["non"])}
        """
        log.info(summary)

        total_retag = sum(len(v) for v in retag_map.values())
        confirm = GenericConfirmModal(
            question=f"CLEANUP {len(tasks_to_cleanup)} tasks and RE-TAG {total_retag} tasks?",
            title="Cleanup & Retag All Tasks",
            confirm_variant="warning",
            icon=icons.QUESTION,
        )

        if await self.app.push_screen(confirm, wait_for_dismiss=True):
            await self._execute_cleanup_and_retag(list(tasks_to_cleanup), retag_map)

    async def _execute_cleanup_and_retag(
        self,
        cleanup_tasks: list[str],
        retag_data: dict[str, list[str]],
    ) -> None:
        """Execute the cleanup and re-tagging API calls."""
        try:
            tags = self.vault.tags
            parent_tag_map = {
                "str": tags.get_str_parent(),
                "per": tags.get_per_parent(),
                "int": tags.get_int_parent(),
                "con": tags.get_con_parent(),
                "non": tags.get_no_attr_parent(),
            }

            log.info(f"{icons.RELOAD} Starting cleanup process...")
            for task_id in cleanup_tasks:
                for parent_tag in parent_tag_map.values():
                    try:
                        self.app.habitica_api.remove_tag_from_task(
                            task_id=task_id,
                            tag_id_to_remove=parent_tag.id,
                        )
                    except Exception as e:
                        log.warning(
                            f"Could not remove tag {parent_tag.id} from task {task_id}: {e}",
                        )

            log.info(
                f"{icons.CHECK} Cleanup completed. Starting re-tagging...",
            )
            for attr, task_ids in retag_data.items():
                parent_tag = parent_tag_map[attr]
                for task_id in task_ids:
                    self.app.habitica_api.add_tag_to_task(
                        task_id=task_id,
                        tag_id_to_add=parent_tag.id,
                    )
                    if attr != "non":
                        self.app.habitica_api.assign_task_attribute(
                            task_id=task_id,
                            task_attribute=attr,
                        )

            log.info(f"{icons.CHECK} Re-tagging completed successfully!")
            self.notify(
                f"{icons.CHECK} Cleanup and re-tagging completed!",
                title="Success",
            )
        except Exception as e:
            log.error(f"{icons.ERROR} Error during cleanup and retag: {e}")
            self.notify(
                f"{icons.ERROR} Failed during cleanup/retag: {e!s}",
                title="Error",
                severity="error",
            )
