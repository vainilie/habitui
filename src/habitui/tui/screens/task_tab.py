from __future__ import annotations

import typing
from typing import Any
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
from habitui.core.models.task_model import AnyTask, TaskTodo, TaskDaily, TaskHabit, TaskCollection


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


# ─── Task Formatter Module ─────────────────────────────────────────────────────
class TaskFormatter:
    """Handles all task display formatting logic."""

    TAG_CONFIGS = {
        TagsTrait.LEGACY: TagConfig(TagsTrait.LEGACY, icons.LEGACY),
        TagsTrait.CHALLENGE: TagConfig(TagsTrait.CHALLENGE, icons.TROPHY),
        TagsTrait.PERCEPTION: TagConfig(TagsTrait.PERCEPTION, icons.DROP, "per"),
        TagsTrait.STRENGTH: TagConfig(TagsTrait.STRENGTH, icons.FIRE_O, "str"),
        TagsTrait.INTELLIGENCE: TagConfig(TagsTrait.INTELLIGENCE, icons.AIR, "int"),
        TagsTrait.CONSTITUTION: TagConfig(TagsTrait.CONSTITUTION, icons.LEAVES, "con"),
        TagsTrait.NO_ATTRIBUTE: TagConfig(TagsTrait.NO_ATTRIBUTE, icons.ANCHOR),
    }

    def __init__(self, vault):
        self.vault = vault

    def _sanitize_id(self, task_id: str) -> str:
        """Convert a UUID to a valid Textual widget ID."""
        return f"task_{task_id.replace('-', '_')}"

    def _extract_task_id(self, widget_id: str) -> str:
        """Extract the original UUID from a sanitized widget ID."""
        if widget_id.startswith("task_"):
            return widget_id[5:].replace("_", "-")
        return widget_id

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
        status_map = {DailyStatus.COMPLETED_TODAY: icons.CHECK, DailyStatus.DUE_TODAY: icons.BLANK, DailyStatus.READY_TO_COMPLETE: icons.HALF_CIRCLE, DailyStatus.INACTIVE: icons.SLEEP, DailyStatus.DUE_YESTERDAY: icons.BACK}
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
        tag_names_clean = [f"[white][/][blue on white]{tag} [/][white][/]" for tag in tag_names]
        return "".join(tag_names_clean)

    def _extract_task_display_data(self, task: AnyTask) -> dict[str, Any]:
        """Extract and format all display data for a task."""
        data = {
            "text": parse_emoji(task.text).replace("#", ""),
            "notes": parse_emoji(task.notes),
            "attribute": self.TAG_CONFIGS.get(TagsTrait(task.attribute[0:3])).icon,
            "status": self._format_status(task.status) if isinstance(task.status, DailyStatus) else task.status,
            "type": task.type,
            "value": round(task.value),
            "priority": round(task.priority),
            "tags": self.format_tags(task.tags),
            "linked": f"[red]{icons.UNLINK}[/]" if task.task_broken else "",
            "ch_linked": f"[red]{icons.MEGAPHONE}[/red]" if task.task_broken else icons.MEGAPHONE,
            "challenge": self._format_challenge_display(task),
            "created": DateTimeHandler(timestamp=task.created_at).format_time_difference(),
        }
        return data

    def format_task_option(self, task: AnyTask, selected_tasks: set[str]) -> ListItem:
        """Format a task for display in the list."""
        task_data = self._extract_task_display_data(task)
        main_grid = Table(expand=False, padding=(0, 1), show_header=False, show_lines=True)
        main_grid.add_column(ratio=1, justify="right")
        main_grid.add_column(ratio=3)
        task_grid = Table.grid(expand=False, padding=(0, 1))
        task_grid.add_column()
        task_grid.add_row(Markdown(task_data["text"]), style="bold")
        task_grid.add_row(task_data["tags"], style="dim")
        task_grid.add_row(f"{task_data['linked']} {task_data['ch_linked']}", style="dim")
        task_grid.add_row(Panel(Markdown(task_data["notes"])))
        task_grid.add_row(task_data["attribute"])
        task_grid.add_row(f"{task_data['priority']} {task_data['value']}", style="dim")
        if isinstance(task, TaskDaily):
            next_due_ts = task.next_due[0] if task.completed else task.next_due[1]
            next_due_str = DateTimeHandler(timestamp=next_due_ts).format_time_difference()
            task_grid.add_row(f"{task.user_damage}, {task.party_damage}")
            task_grid.add_row(f"{task.streak}, {next_due_str}")
        if isinstance(task, TaskTodo):
            next_due_str = DateTimeHandler(timestamp=task.due_date).format_time_difference() if task.due_date else ""
            task_grid.add_row(f"{task.checklist}")
        if isinstance(task, TaskHabit):
            task_grid.add_row(f"{task.counter_up} - {task.counter_down}")
            task_grid.add_row(f"{task.frequency}")
        main_grid.add_row(task_data["status"], task_grid)
        sanitized_id = self._sanitize_id(task.id)
        item = ListItem(Label(main_grid, markup=True), id=sanitized_id, markup=True, classes="task-item")
        if task.id in selected_tasks:
            item.add_class("task-selected")
        return item


# ─── Task Filter Module ────────────────────────────────────────────────────────
class TaskFilter:
    """Handles all task filtering and sorting logic."""

    def __init__(self, vault):
        self.vault = vault

    def get_tag_filter_options(self, tasks: TaskCollection) -> list[tuple[str, str]]:
        """Get available tags for filtering."""
        options = [("All Tags", "all")]
        tag_uuids = set()
        for task in tasks.all_tasks:
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

    def get_challenge_filter_options(self, tasks: TaskCollection) -> list[tuple[str, str]]:
        """Get available challenges for filtering by challenge_id."""
        options = [("All Challenges", "all")]
        challenge_map: dict[str, str] = {}
        for task in tasks.all_tasks:
            cid = getattr(task, "challenge_id", None)
            cname = getattr(task, "challenge_shortname", None)
            if cid and cid not in challenge_map:
                challenge_map[cid] = cname or cid
        for cid, cname in sorted(challenge_map.items(), key=lambda x: x[1].lower()):
            options.append((parse_emoji(cname), cid))
        return options

    def get_tasks_for_mode(self, tasks: TaskCollection, mode: str, filter_settings: dict[str, Any]) -> list[AnyTask]:
        """Get the correct list of task models for the current view mode."""
        mode_to_attr = {"all": "all_tasks", "dailies": "dailys", "todos": "todos", "habits": "habits", "rewards": "rewards"}
        attr_name = mode_to_attr.get(mode, "all_tasks")
        tasks_list = getattr(tasks, attr_name, [])
        filtered_tasks = self._filter_tasks(tasks_list, filter_settings)
        return self._sort_tasks(filtered_tasks, filter_settings.get("sort", "default"))

    def _filter_tasks(self, tasks_list: list[AnyTask], filter_settings: dict[str, Any]) -> list[AnyTask]:
        """Filter tasks based on current filter settings."""
        current_filter = filter_settings.get("filter", "all")
        if current_filter == "challenge":
            tasks_list = [t for t in tasks_list if getattr(t, "challenge", None)]
        elif current_filter == "non_challenge":
            tasks_list = [t for t in tasks_list if not getattr(t, "challenge", None)]
        elif current_filter == "completed":
            tasks_list = [t for t in tasks_list if getattr(t, "completed", False)]
        elif current_filter == "incomplete":
            tasks_list = [t for t in tasks_list if not getattr(t, "completed", False)]
        elif current_filter == "due_today":
            tasks_list = [t for t in tasks_list if getattr(t, "isDue", False) or getattr(t, "due_today", False)]
        elif current_filter == "broken":
            tasks_list = [t for t in tasks_list if getattr(t, "challenge_broken", True) or getattr(t, "task_broken", True)]
        # Multi-select challenge filter
        selected_challenges = filter_settings.get("selected_challenges", set())
        if selected_challenges:
            tasks_list = [t for t in tasks_list if getattr(t, "challenge_id", None) in selected_challenges]
        # Multi-select tag filter with AND/OR logic
        selected_tags = filter_settings.get("selected_tags", set())
        tag_logic = filter_settings.get("tag_logic", "OR")  # "AND" or "OR"
        if selected_tags:
            if tag_logic == "AND":
                # Task must have ALL selected tags
                tasks_list = [t for t in tasks_list if selected_tags.issubset(set(getattr(t, "tags", [])))]
            else:  # OR logic
                # Task must have AT LEAST ONE of the selected tags
                tasks_list = [t for t in tasks_list if selected_tags.intersection(set(getattr(t, "tags", [])))]
        # Multi-select attribute filter
        selected_attributes = filter_settings.get("selected_attributes", set())
        if selected_attributes:
            tasks_list = [t for t in tasks_list if getattr(t, "attribute", "")[:3] in selected_attributes]
        return tasks_list

    def _sort_tasks(self, tasks_list: list[AnyTask], sort_mode: str) -> list[AnyTask]:
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
        if sort_mode in sort_key_map:
            key, reverse = sort_key_map[sort_mode]
            return sorted(tasks_list, key=key, reverse=reverse)
        return tasks_list


# ─── Task Operations Module ────────────────────────────────────────────────────
class TaskOperations:
    """Handles all task API operations and bulk actions."""

    def __init__(self, app, vault):
        self.app = app
        self.vault = vault

    async def score_tasks(self, tasks_to_score: list[AnyTask], direction: str = "auto") -> dict[str, int]:
        """Handle the workflow for scoring one or more tasks."""
        if not tasks_to_score:
            return {"success": 0, "error": 0}
        success, error = 0, 0
        for task in tasks_to_score:
            try:
                score_direction = direction if direction in {"up", "down"} else "up"
                await self.app.habitica_api.score_task_action(task_id=task.id, score_direction=score_direction)
                success += 1
            except Exception as e:
                log.error(f"Error scoring task {task.id}: {e}")
                error += 1
        return {"success": success, "error": error}

    async def delete_tasks(self, tasks_to_delete: list[AnyTask]) -> dict[str, int]:
        """Handle the workflow for deleting one or more tasks."""
        if not tasks_to_delete:
            return {"success": 0, "error": 0}
        success, error = 0, 0
        for task in tasks_to_delete:
            try:
                await self.app.habitica_api.delete_existing_task(task_id=task.id)
                success += 1
            except Exception as e:
                log.error(f"Error deleting task {task.id}: {e}")
                error += 1
        return {"success": success, "error": error}

    async def analyze_and_fix_inconsistencies(self, tasks: TaskCollection) -> dict[str, Any]:
        """Clean all parent/no_attr tags, then reclassify tasks based on child tags."""
        tags = self.vault.tags
        parent_tags = {tags.get_str_parent().id, tags.get_per_parent().id, tags.get_int_parent().id, tags.get_con_parent().id, tags.get_no_attr_parent().id}
        # Mapeo de atributos a tags padre
        attr_to_parent = {"str": tags.get_str_parent(), "per": tags.get_per_parent(), "int": tags.get_int_parent(), "con": tags.get_con_parent(), "non": tags.get_no_attr_parent()}
        issues_found = {"missing_parent_tags": [], "wrong_parent_tags": [], "multiple_parent_tags": [], "orphaned_parent_tags": []}  # Tareas con atributo pero sin tag padre  # Tareas con tag padre incorrecto  # Tareas con múltiples tags padre  # Tareas con tag padre pero sin atributo hijo
        for task in tasks:
            # Detectar qué atributo debería tener basado en tags hijos
            expected_attribute = None
            child_tags_found = []
            for tag_id in task.tags:
                if tag_id not in parent_tags:
                    if tag_data := tags.get_by_id(tag_id):
                        if hasattr(tag_data, "attribute") and tag_data.attribute:
                            child_tags_found.append(tag_data.attribute)
                            expected_attribute = tag_data.attribute  # El último encontrado
            # Detectar tags padre actuales
            current_parent_tags = [tag_id for tag_id in task.tags if tag_id in parent_tags]
            # Si no hay tags hijos con atributo, debería ser "non"
            if not expected_attribute:
                expected_attribute = "non"
            # Verificar inconsistencias
            expected_parent_id = attr_to_parent[expected_attribute].id
            if not current_parent_tags:
                # Falta el tag padre
                issues_found["missing_parent_tags"].append({"task_id": task.id, "expected_attribute": expected_attribute, "action": "add_parent_tag"})
            elif len(current_parent_tags) > 1:
                # Múltiples tags padre
                issues_found["multiple_parent_tags"].append({"task_id": task.id, "current_parents": current_parent_tags, "expected_attribute": expected_attribute, "action": "fix_multiple_parents"})
            elif current_parent_tags[0] != expected_parent_id:
                # Tag padre incorrecto
                issues_found["wrong_parent_tags"].append({"task_id": task.id, "current_parent": current_parent_tags[0], "expected_attribute": expected_attribute, "action": "replace_parent_tag"})
            # Verificar si tiene tag padre pero no tags hijos válidos
            if current_parent_tags and not child_tags_found:
                # Solo marcar como huérfano si el tag padre no es "non"
                current_parent_tag_name = None
                for attr, parent_tag in attr_to_parent.items():
                    if parent_tag.id in current_parent_tags:
                        current_parent_tag_name = attr
                        break
                if current_parent_tag_name and current_parent_tag_name != "non":
                    issues_found["orphaned_parent_tags"].append({"task_id": task.id, "orphaned_parent": current_parent_tags[0], "action": "convert_to_non"})
        return {
            "issues_found": issues_found,
            "total_issues": sum(len(v) for v in issues_found.values()),
            "summary": {"missing_parent": len(issues_found["missing_parent_tags"]), "wrong_parent": len(issues_found["wrong_parent_tags"]), "multiple_parents": len(issues_found["multiple_parent_tags"]), "orphaned_parents": len(issues_found["orphaned_parent_tags"])},
        }

    async def execute_maintenance_fixes(self, issues_data: dict[str, Any]) -> bool:
        """Ejecuta las correcciones de mantenimiento de forma conservadora."""
        try:
            tags = self.vault.tags
            attr_to_parent = {"str": tags.get_str_parent(), "per": tags.get_per_parent(), "int": tags.get_int_parent(), "con": tags.get_con_parent(), "non": tags.get_no_attr_parent()}
            issues = issues_data["issues_found"]
            log.info(f"{icons.GEAR} Iniciando correcciones de mantenimiento...")
            # 1. Agregar tags padre faltantes
            for issue in issues["missing_parent_tags"]:
                task_id = issue["task_id"]
                expected_attr = issue["expected_attribute"]
                parent_tag = attr_to_parent[expected_attr]
                try:
                    await self.app.habitica_api.add_tag_to_task(task_id=task_id, tag_id_to_add=parent_tag.id)
                    # Asignar atributo si no es "non"
                    if expected_attr != "non":
                        await self.app.habitica_api.assign_task_attribute(task_id=task_id, task_attribute=expected_attr)
                    log.debug(f"✓ Agregado tag padre {expected_attr} a tarea {task_id}")
                except Exception as e:
                    log.warning(f"Error agregando tag padre a {task_id}: {e}")
            # 2. Corregir tags padre incorrectos
            for issue in issues["wrong_parent_tags"]:
                task_id = issue["task_id"]
                current_parent = issue["current_parent"]
                expected_attr = issue["expected_attribute"]
                expected_parent = attr_to_parent[expected_attr]
                try:
                    # Remover el tag padre incorrecto
                    await self.app.habitica_api.remove_tag_from_task(task_id=task_id, tag_id_to_remove=current_parent)
                    # Agregar el tag padre correcto
                    await self.app.habitica_api.add_tag_to_task(task_id=task_id, tag_id_to_add=expected_parent.id)
                    # Asignar atributo correcto
                    if expected_attr != "non":
                        await self.app.habitica_api.assign_task_attribute(task_id=task_id, task_attribute=expected_attr)
                    log.debug(f"✓ Corregido tag padre de tarea {task_id}: {expected_attr}")
                except Exception as e:
                    log.warning(f"Error corrigiendo tag padre en {task_id}: {e}")
            # 3. Limpiar múltiples tags padre
            for issue in issues["multiple_parent_tags"]:
                task_id = issue["task_id"]
                current_parents = issue["current_parents"]
                expected_attr = issue["expected_attribute"]
                expected_parent = attr_to_parent[expected_attr]
                try:
                    # Remover todos los tags padre actuales
                    for parent_id in current_parents:
                        await self.app.habitica_api.remove_tag_from_task(task_id=task_id, tag_id_to_remove=parent_id)
                    # Agregar solo el correcto
                    await self.app.habitica_api.add_tag_to_task(task_id=task_id, tag_id_to_add=expected_parent.id)
                    # Asignar atributo
                    if expected_attr != "non":
                        await self.app.habitica_api.assign_task_attribute(task_id=task_id, task_attribute=expected_attr)
                    log.debug(f"✓ Limpiados múltiples tags padre en tarea {task_id}")
                except Exception as e:
                    log.warning(f"Error limpiando múltiples tags en {task_id}: {e}")
            # 4. Convertir tags padre huérfanos a "non"
            for issue in issues["orphaned_parent_tags"]:
                task_id = issue["task_id"]
                orphaned_parent = issue["orphaned_parent"]
                non_parent = attr_to_parent["non"]
                try:
                    # Remover el tag padre huérfano
                    await self.app.habitica_api.remove_tag_from_task(task_id=task_id, tag_id_to_remove=orphaned_parent)
                    # Agregar tag "non"
                    await self.app.habitica_api.add_tag_to_task(task_id=task_id, tag_id_to_add=non_parent.id)
                    log.debug(f"✓ Convertido tag huérfano a 'non' en tarea {task_id}")
                except Exception as e:
                    log.warning(f"Error convirtiendo tag huérfano en {task_id}: {e}")
            total_fixes = sum(len(v) for v in issues.values())
            log.info(f"{icons.CHECK} Mantenimiento completado: {total_fixes} correcciones aplicadas")
            return True
        except Exception as e:
            log.error(f"{icons.ERROR} Error durante mantenimiento: {e}")
            return False


# ─── Main TasksTab - Now Simplified ───────────────────────────────────────────
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
        Binding("u", "unlink_task", "Unlink"),
    ]
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
        # Initialize modular components
        self.formatter = TaskFormatter(self.vault)
        self.filter = TaskFilter(self.vault)
        self.operations = TaskOperations(self.app, self.vault)
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
        self.filter_options = [("All Tasks", "all"), ("Challenge Tasks", "challenge"), ("Non-Challenge", "non_challenge"), ("Completed", "completed"), ("Incomplete", "incomplete"), ("Due Today", "due_today"), ("Broken Tasks", "broken")]
        log.info("TasksTab: initialized with modular components")

    # ─── Helper Methods ─────────────────────────────────────────────────────────────
    def get_task(self, task_id: str) -> AnyTask | None:
        """Get a task by its ID from the main task collection."""
        return self.tasks.get_task_by_id(task_id)

    def get_filter_settings(self) -> dict[str, str]:
        """Get current filter settings as a dict."""
        return {"filter": self.current_filter, "challenge_filter": self.current_challenge_filter, "tag_filter": self.current_tag_filter, "sort": self.current_sort}

    # ─── UI Composition ────────────────────────────────────────────────────────────
    def compose(self) -> ComposeResult:
        """Compose the dynamic UI for the tasks tab."""
        with Horizontal(classes="controls-row"):
            yield Select([(f"{icons.CALENDAR} Dailies", "dailies"), (f"{icons.TASK_LIST} Todos", "todos"), (f"{icons.INFINITY} Habits", "habits"), (f"{icons.GIFT} Rewards", "rewards"), (f"{icons.GOAL} All", "all")], value=self.current_mode, id="mode_selector", classes="control-select")
            yield Select(self.sort_options, value=self.current_sort, id="sort_selector", classes="control-select")
            yield Select(self.filter_options, value=self.current_filter, id="filter_selector", classes="control-select")
            challenge_options = self.filter.get_challenge_filter_options(self.tasks)
            if len(challenge_options) > 1:
                yield Select(challenge_options, value=self.current_challenge_filter, id="challenge_filter_selector", classes="control-select")
            tag_options = self.filter.get_tag_filter_options(self.tasks)
            if len(tag_options) > 1:
                yield Select(tag_options, value=self.current_tag_filter, id="tag_filter_selector", classes="control-select")
        if self.multiselect:
            with Horizontal(classes="multiselect-controls"):
                yield Button("Score Selected", id="score_selected", variant="success")
                if self.current_mode == "habits":
                    yield Button("Score Up", id="score_up_selected", variant="primary")
                    yield Button("Score Down", id="score_down_selected", variant="warning")
                yield Button("Delete Selected", id="delete_selected", variant="error")
                yield Label(f"Selected: {len(self.tasks_selected)}", classes="selection-count")
        current_tasks = self.filter.get_tasks_for_mode(self.tasks, self.current_mode, self.get_filter_settings())
        if not current_tasks:
            yield Label("No tasks found in this category.", classes="center-text empty-state")
            return
        yield ListView(*[self.formatter.format_task_option(task, self.tasks_selected) for task in current_tasks], id="tasks_list", classes="select-line")

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
        task_id = self.formatter._extract_task_id(sanitized_id)
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
            self.mutate_reactive(TasksTab.tasks)
            self.formatter = TaskFormatter(self.vault)
            self.filter = TaskFilter(self.vault)
            self.operations = TaskOperations(self.app, self.vault)
            available_challenges = {getattr(t, "challenge_id", None) for t in self.tasks.all_tasks}
            if self.current_challenge_filter != "all" and self.current_challenge_filter not in available_challenges:
                self.current_challenge_filter = "all"
            available_tags = {tag for t in self.tasks.all_tasks for tag in getattr(t, "tags", [])}
            if self.current_tag_filter != "all" and self.current_tag_filter not in available_tags:
                self.current_tag_filter = "all"
            self.notify(f"{icons.CHECK} Tasks updated successfully!", title="Data Updated")
        except Exception as e:
            log.error(f"TasksTab: Error refreshing data: {e}")
            self.notify(f"{icons.ERROR} Error updating tasks: {e}", title="Error", severity="error")

    # ─── Task Actions & Workflows ──────────────────────────────────────────────────
    async def _score_selected_tasks(self, direction: str = "auto") -> None:
        """Score all selected tasks with given direction."""
        if not self.tasks_selected:
            return
        tasks_to_score = [self.get_task(task_id) for task_id in self.tasks_selected]
        tasks_to_score = [t for t in tasks_to_score if t is not None]
        result = await self.operations.score_tasks(tasks_to_score, direction)
        self.tasks_selected.clear()
        self.refresh_data()
        self.mutate_reactive(TasksTab.tasks)
        if result["error"] == 0:
            self.notify(f"{icons.CHECK} {result['success']} tasks scored!", title="Tasks Scored")
        else:
            self.notify(f"{icons.WARNING} {result['success']} scored, {result['error']} failed.", title="Batch Complete")

    async def _delete_selected_tasks(self) -> None:
        """Delete all selected tasks."""
        if not self.tasks_selected:
            return
        tasks_to_delete = [self.get_task(task_id) for task_id in self.tasks_selected]
        tasks_to_delete = [t for t in tasks_to_delete if t is not None]
        self._delete_tasks_with_confirmation(tasks_to_delete)

    @work
    async def _delete_tasks_with_confirmation(self, tasks_to_delete: list[AnyTask]) -> None:
        """Handle the workflow for deleting one or more tasks with confirmation."""
        if not tasks_to_delete:
            return
        preview = "\n".join(f"• {t.text}" for t in tasks_to_delete[:5])
        if len(tasks_to_delete) > 5:
            preview += f"\n... and {len(tasks_to_delete) - 5} more"
        question = f"Delete {len(tasks_to_delete)} tasks?\n\n{preview}"
        modal = GenericConfirmModal(question=question, confirm_variant="error", icon=icons.ERASE)
        if not await self.app.push_screen(modal, wait_for_dismiss=True):
            return
        result = await self.operations.delete_tasks(tasks_to_delete)
        self.tasks_selected.clear()
        self.refresh_data()
        self.mutate_reactive(TasksTab.tasks)
        if result["error"] == 0:
            self.notify(f"{icons.CHECK} {result['success']} tasks deleted!", title="Tasks Deleted")
        else:
            self.notify(f"{icons.WARNING} {result['success']} deleted, {result['error']} failed.", title="Batch Complete")

    # ─── Action Methods - FIXED ────────────────────────────────────────────────────
    async def _handle_single_task_action(self, action_func, *args) -> None:
        """Helper to handle single task actions."""
        if self.multiselect and self.tasks_selected:
            # Si estamos en modo multiselect, usar la función apropiada
            if action_func == self.operations.score_tasks:
                await self._score_selected_tasks(*args)
            elif action_func == self._delete_tasks_with_confirmation:
                await self._delete_selected_tasks()
            return
        task_list = self.query_one("#tasks_list", ListView)
        if task_list.index is not None and (selected_item := task_list.highlighted_child):
            sanitized_id = str(selected_item.id)
            task_id = self.formatter._extract_task_id(sanitized_id)
            if task := self.get_task(task_id):
                if action_func == self.operations.score_tasks:
                    result = await action_func([task], *args)
                    self.refresh_data()
                    self.mutate_reactive(TasksTab.tasks)
                    if result["error"] == 0:
                        self.notify(f"{icons.CHECK} Task scored!", title="Task Scored")
                    else:
                        self.notify(f"{icons.ERROR} Failed to score task", title="Error", severity="error")
                elif action_func == self._delete_tasks_with_confirmation:
                    await action_func([task])

    @work
    async def action_score_task(self) -> None:
        """Score the currently selected task (smart direction)."""
        await self._handle_single_task_action(self.operations.score_tasks, "auto")

    @work
    async def action_score_up_task(self) -> None:
        """Score up the currently selected task(s)."""
        await self._handle_single_task_action(self.operations.score_tasks, "up")

    @work
    async def action_score_down_task(self) -> None:
        """Score down the currently selected task(s)."""
        await self._handle_single_task_action(self.operations.score_tasks, "down")

    @work
    async def action_delete_task(self) -> None:
        """Delete the currently selected task(s)."""
        await self._handle_single_task_action(self._delete_tasks_with_confirmation)

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
        self._maintenance_workflow()

    # ─── Maintenance Workflow ─────────────────────────────────────────────────────
    @work
    async def _maintenance_workflow(self) -> None:
        """Analyze and fix only the inconsistencies found in task tagging."""
        analysis_data = await self.operations.analyze_and_fix_inconsistencies(self.tasks)
        issues = analysis_data["issues_found"]
        summary_stats = analysis_data["summary"]
        # Crear resumen detallado
        summary = f"""
        ANÁLISIS DE CONSISTENCIA:
        ========================
        Issues encontrados: {analysis_data["total_issues"]}
        Detalle por tipo:
        - Tags padre faltantes: {summary_stats["missing_parent"]}
        - Tags padre incorrectos: {summary_stats["wrong_parent"]}
        - Múltiples tags padre: {summary_stats["multiple_parents"]}
        - Tags padre huérfanos: {summary_stats["orphaned_parents"]}
        """
        log.info(summary)
        # Si no hay issues, informar y salir
        if analysis_data["total_issues"] == 0:
            self.notify(f"{icons.CHECK} No se encontraron inconsistencias", title="Sistema consistente")
            return
        # Crear descripción detallada para el modal
        issue_details = []
        if summary_stats["missing_parent"] > 0:
            issue_details.append(f"• {summary_stats['missing_parent']} tareas sin tag padre")
        if summary_stats["wrong_parent"] > 0:
            issue_details.append(f"• {summary_stats['wrong_parent']} tareas con tag padre incorrecto")
        if summary_stats["multiple_parents"] > 0:
            issue_details.append(f"• {summary_stats['multiple_parents']} tareas con múltiples tags padre")
        if summary_stats["orphaned_parents"] > 0:
            issue_details.append(f"• {summary_stats['orphaned_parents']} tags padre sin hijos válidos")
        details_text = "\n".join(issue_details)
        confirm = GenericConfirmModal(question=f"Se encontraron {analysis_data['total_issues']} inconsistencias:\n\n{details_text}\n\n¿Aplicar correcciones de mantenimiento?", title="Mantenimiento del Sistema", confirm_variant="primary", icon=icons.GEAR)  # Menos agresivo que "warning"
        if await self.app.push_screen(confirm, wait_for_dismiss=True):
            success = await self.operations.execute_maintenance_fixes(analysis_data)
            if success:
                self.notify(f"{icons.CHECK} Mantenimiento completado: {analysis_data['total_issues']} correcciones aplicadas", title="Mantenimiento exitoso")
            else:
                self.notify(f"{icons.ERROR} Error durante el proceso de mantenimiento", title="Error", severity="error")
            self.refresh_data()
        else:
            log.info("Mantenimiento cancelado por el usuario")

    @work
    async def action_unlink_task(self) -> None:
        """Unlink the currently selected task(s) - handles both single and multi-select."""
        if self.multiselect and self.tasks_selected:
            # Modo multiselect - usar las tareas seleccionadas
            tasks_to_unlink = [self.get_task(task_id) for task_id in self.tasks_selected]
            tasks_to_unlink = [t for t in tasks_to_unlink if t is not None]
            self._unlink_task_with_confirmation(tasks_to_unlink)
        else:
            # Modo single select - obtener la tarea highlighted
            task_list = self.query_one("#tasks_list", ListView)
            if task_list.index is not None and (selected_item := task_list.highlighted_child):
                sanitized_id = str(selected_item.id)
                task_id = self.formatter._extract_task_id(sanitized_id)
                if task := self.get_task(task_id):
                    self._unlink_task_with_confirmation([task])

    @work
    async def _unlink_task_with_confirmation(self, tasks_to_unlink: list[AnyTask]) -> None:
        """Handle the workflow for unlinking one or more tasks from challenges with confirmation."""
        if not tasks_to_unlink:
            return
        # Separar por tipo de problema
        challenge_broken_tasks = []
        individual_broken_tasks = []
        non_broken_tasks = []
        for task in tasks_to_unlink:
            if hasattr(task, "challenge_broken") and task.challenge_broken:
                # Si challenge_broken=True, siempre es challenge completo
                challenge_broken_tasks.append(task)
            elif hasattr(task, "task_broken") and task.task_broken and not (hasattr(task, "challenge_broken") and task.challenge_broken):
                # Solo task_broken=True y challenge_broken=False
                individual_broken_tasks.append(task)
            else:
                # task_broken=False y challenge_broken=False --> NO SE PUEDE
                non_broken_tasks.append(task)
        # Si hay tareas que no están broken, mostrar error
        if non_broken_tasks:
            non_broken_preview = "\n".join(f"• {t.text[:40]}" for t in non_broken_tasks[:3])
            if len(non_broken_tasks) > 3:
                non_broken_preview += f"\n... y {len(non_broken_tasks) - 3} más"
            self.notify(f"{icons.ERROR} Estas tareas no están broken y no se pueden desenlazar:\n\n{non_broken_preview}", title="Tareas no broken", severity="error")
            return
        # Si no hay tareas broken válidas, salir
        if not challenge_broken_tasks and not individual_broken_tasks:
            return
        # Manejar challenges broken (por challenge_id)
        if challenge_broken_tasks:
            # Agrupar por challenge_id
            challenges_to_unlink = {}
            for task in challenge_broken_tasks:
                challenge_id = task.challenge_id
                if challenge_id not in challenges_to_unlink:
                    challenges_to_unlink[challenge_id] = []
                challenges_to_unlink[challenge_id].append(task)
            # Procesar cada challenge broken
            for challenge_id, selected_tasks in challenges_to_unlink.items():
                # OBTENER TODAS LAS TAREAS DEL CHALLENGE (no solo las seleccionadas)
                all_challenge_tasks = [t for t in self.tasks if hasattr(t, "challenge_id") and t.challenge_id == challenge_id]
                await self._handle_challenge_broken_unlink(challenge_id, all_challenge_tasks)
        # Manejar tareas individuales broken
        for task in individual_broken_tasks:
            await self._handle_individual_task_broken_unlink(task)
        # Refrescar datos después de todas las operaciones
        self.tasks_selected.clear()
        self.refresh_data()
        self.mutate_reactive(TasksTab.tasks)

    async def _handle_challenge_broken_unlink(self, challenge_id: str, challenge_tasks: list[AnyTask]) -> None:
        """Handle unlinking ALL tasks from a broken challenge."""
        # Crear preview de las tareas del challenge
        preview = "\n".join(f"• {t.text}" for t in challenge_tasks[:5])
        if len(challenge_tasks) > 5:
            preview += f"\n... y {len(challenge_tasks) - 5} más"
        # Obtener nombre del challenge si está disponible
        challenge_name = f"Challenge {challenge_id}"
        if challenge_tasks and hasattr(challenge_tasks[0], "challenge_name"):
            challenge_name = challenge_tasks[0].challenge_shortname or challenge_name
        question = f"""El challenge '{challenge_name}' está BROKEN.
    Tareas del challenge ({len(challenge_tasks)}):
    {preview}
    ¿Qué hacer con TODAS las tareas del challenge?"""
        modal = GenericConfirmModal(question=question, title="Challenge Broken - Desenlazar Todo", confirm_variant="warning", icon=icons.UNLINK, confirm_text="Mantener todas", cancel_text="Eliminar todas")
        user_choice = await self.app.push_screen(modal, wait_for_dismiss=True)
        if user_choice is None:  # Usuario canceló
            return
        keep_option = "keep-all" if user_choice else "remove-all"
        # Ejecutar el unlink del challenge completo
        try:
            success = self.app.habitica_api.unlink_all_tasks_from_challenge(challenge_id=challenge_id, task_handling_option=keep_option)
            if success:
                action_desc = "mantenidas" if keep_option == "keep-all" else "eliminadas"
                self.notify(f"{icons.CHECK} Challenge broken desenlazado: {len(challenge_tasks)} tareas {action_desc}", title="Challenge Desenlazado")
            else:
                self.notify(f"{icons.ERROR} Error al desenlazar challenge broken", title="Error", severity="error")
        except Exception as e:
            log.error(f"Error unlinking broken challenge {challenge_id}: {e}")
            self.notify(f"{icons.ERROR} Error al desenlazar challenge: {e!s}", title="Error", severity="error")

    async def _handle_individual_task_broken_unlink(self, task: AnyTask) -> None:
        """Handle unlinking a single broken task from its active challenge."""
        task_name = task.text[:50] + "..." if len(task.text) > 50 else task.text
        question = f"""La tarea está BROKEN en su challenge:
    "{task_name}"
    ¿Qué hacer con esta tarea al desenlazarla?"""
        modal = GenericConfirmModal(question=question, title="Tarea Broken - Desenlazar Individual", confirm_variant="primary", icon=icons.UNLINK, confirm_text="Mantener tarea", cancel_text="Eliminar tarea")
        user_choice = await self.app.push_screen(modal, wait_for_dismiss=True)
        if user_choice is None:  # Usuario canceló
            return
        keep_option = "keep" if user_choice else "remove"
        # Ejecutar el unlink individual
        try:
            success = self.app.habitica_api.unlink_task_from_challenge(task_id=task.id, task_handling_option=keep_option)
            if success:
                action_desc = "mantenida" if keep_option == "keep" else "eliminada"
                self.notify(f"{icons.CHECK} Tarea broken desenlazada y {action_desc}", title="Tarea Desenlazada")
            else:
                self.notify(f"{icons.ERROR} Error al desenlazar tarea broken", title="Error", severity="error")
        except Exception as e:
            log.error(f"Error unlinking broken task {task.id}: {e}")
            self.notify(f"{icons.ERROR} Error al desenlazar tarea: {e!s}", title="Error", severity="error")
