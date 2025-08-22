from __future__ import annotations

from typing import TYPE_CHECKING
from itertools import starmap

from rich.table import Table

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import (
    Label,
    Select,
    OptionList,
)
from textual.reactive import reactive
from textual.containers import Vertical
from textual.widgets.option_list import Option

from habitui.ui import icons
from habitui.utils import DateTimeHandler
from habitui.tui.generic import BaseTab
from habitui.custom_logger import log
from habitui.core.models.task_model import (
    AnyTask,
    TaskTodo,
    TaskDaily,
    TaskHabit,
    TaskReward,
    TaskCollection,
)


if TYPE_CHECKING:
    from textual.app import ComposeResult

    from habitui.tui.main_app import HabiTUI


class TasksTab(Vertical, BaseTab):
    BINDINGS = [
        Binding("d", "tasks_dailies", "Dailies"),
        Binding("t", "tasks_todos", "Todos"),
        Binding("h", "tasks_habits", "Habits"),
        Binding("w", "tasks_rewards", "Rewards"),
        Binding("a", "tasks", "All"),
        Binding("r", "refresh_data", "Refresh"),
    ]

    tasks: reactive[TaskCollection] = reactive(None, recompose=True)
    current_mode: reactive[str] = reactive("dailies", recompose=True)
    current_page: reactive[int] = reactive(0, recompose=True)

    def __init__(self) -> None:
        super().__init__()
        self.app: HabiTUI
        self.tasks = self.vault.ensure_tasks_loaded()
        log.info("TasksTab: initialized")

    def get_task(self, task_id: str):
        return self.tasks.get_task_by_id(task_id)

    def format_task_option(
        self,
        task_id: str,
        task_data: AnyTask,
    ) -> Option:
        grid = Table.grid(expand=True, padding=(0, 1))
        grid.add_column(ratio=3)
        grid.add_column(ratio=1, justify="right")

        # Different icons based on task type and completion status
        if hasattr(task_data, "completed") and task_data.completed:
            status_icon = icons.CHECK
        elif hasattr(task_data, "isDue") and getattr(task_data, "isDue", False):
            status_icon = icons.EXCLAMATION
        else:
            status_icon = icons.BLANK

        # Task name and type indicator
        task_type = type(task_data).__name__.replace("Task", "").upper()
        grid.add_row(
            f'{status_icon} [b]{task_data.text or task_data.name}[/b]',
            f"[dim]{task_type}[/dim]",
        )

        # Task details (difficulty, value, etc.)
        difficulty = getattr(task_data, "priority", getattr(task_data, "difficulty", 1))
        value = getattr(task_data, "value", 0)

        grid.add_row(
            f"{icons.STAR} Difficulty: {difficulty} • Value: {value}",
            "",
        )

        # Task notes or description
        notes = getattr(task_data, "notes", "") or ""
        notes_preview = notes[:50] if notes else "No notes"
        if len(notes_preview) == 50:
            notes_preview += "..."

        # Format date based on task type
        date_info = ""
        if hasattr(task_data, "date") and task_data.date:
            date_info = DateTimeHandler(
                timestamp=task_data.date,
            ).format_time_difference()
        elif hasattr(task_data, "createdAt") and task_data.createdAt:
            date_info = DateTimeHandler(
                timestamp=task_data.createdAt,
            ).format_time_difference()

        grid.add_row(
            f"[dim]{notes_preview}[/]",
            f"[dim]{date_info}[/dim]",
        )

        return Option(grid, id=task_id)

    def _get_tasks_for_mode(
        self,
    ) -> (
        list[TaskTodo | TaskDaily | TaskHabit | TaskReward]
        | list[TaskDaily]
        | list[TaskHabit]
        | list[TaskTodo]
        | list[TaskReward]
        | TaskCollection
    ):
        if self.current_mode == "all":
            return self.tasks.all_tasks
        if self.current_mode == "dailies":
            return self.tasks.dailys
        if self.current_mode == "habits":
            return self.tasks.habits
        if self.current_mode == "todos":
            return self.tasks.todos
        if self.current_mode == "rewards":
            return self.tasks.rewards
        return self.tasks


    def compose(self) -> ComposeResult:
        mode_titles = {
            "dailies": f"{icons.CALENDAR} Dailies",
            "todos": f"{icons.TASK_LIST} Todos",
            "habits": f"{icons.INFINITY} Habits",
            "rewards": f"{icons.GIFT} Rewards",
            "all": f"{icons.GOAL} All Tasks",
        }

        title = mode_titles.get(self.current_mode, f"{icons.GOAL} Tasks")

        yield Label(title, classes="tab-title")

        modes_options = [
            (f"{icons.CALENDAR} Dailies", "dailies"),
            (f"{icons.TASK_LIST} Todos", "todos"),
            (f"{icons.INFINITY} Habits", "habits"),
            (f"{icons.GIFT} Rewards", "rewards"),
            (f"{icons.GOAL} All", "all"),
        ]

        my_select: Select[str] = Select(
            modes_options,
            value=self.current_mode,
            compact=True,
            id="mode_selector",
            classes="mode-selector-dropdown",
        )
        yield my_select

        current_tasks = self._get_tasks_for_mode()

        if not current_tasks:
            empty_messages = {
                "dailies": "No daily tasks yet",
                "todos": "No todo tasks yet",
                "habits": "No habits yet",
                "rewards": "No rewards available",
                "all": "No tasks available",
            }
            yield Label(
                empty_messages.get(self.current_mode, "No tasks available"),
                classes="center-text empty-state",
            )
            return

        if isinstance(current_tasks, TaskCollection):
            tasks_items = current_tasks.all_tasks.items()
        elif isinstance(current_tasks, dict):
            tasks_items = current_tasks.items()
        else:
            # Handle list case
            tasks_items = [(str(i), task) for i, task in enumerate(current_tasks)]

        tasks_options = list(
            starmap(self.format_task_option, tasks_items),
        )

        yield OptionList(
            *tasks_options,
            id="tasks_list",
            classes="select-line",
        )

    @on(Select.Changed)
    def select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "mode_selector":
            mode = event.value
            if mode == "dailies":
                self.action_tasks_dailies()
            elif mode == "todos":
                self.action_tasks_todos()
            elif mode == "habits":
                self.action_tasks_habits()
            elif mode == "rewards":
                self.action_tasks_rewards()
            elif mode == "all":
                self.action_tasks_all()

    async def on_option_list_option_selected(
        self,
        event: OptionList.OptionSelected,
    ) -> None:
        if event.option_list.id == "tasks_list":
            task_id = str(event.option.id)
            task_data = self.get_task(task_id)

            if task_data:
                # Here you would push a TaskDetailScreen instead of ChallengeDetailScreen
                # detail_screen = TaskDetailScreen(task_data)
                # await self.app.push_screen(detail_screen)
                self.notify(
                    f"{icons.INFO} Task selected: {task_data.text or task_data.name}",
                )
            else:
                self.notify(
                    f"{icons.ERROR} Task not found",
                    severity="error",
                )

    @work
    async def refresh_data(self) -> None:
        log.info("TasksTab: refreshing data")
        try:
            await self.vault.update_tasks_only(force= True)
            self.tasks = self.vault.ensure_tasks_loaded()
            self.mutate_reactive(TasksTab.tasks)

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

    # Removed the handle_challenges_refresh method as it referenced challenges
    # You might need to create a TasksNeedsRefresh event instead

    def action_tasks_dailies(self) -> None:
        self.current_mode = "dailies"
        self.current_page = 0

    def action_tasks_todos(self) -> None:
        self.current_mode = "todos"
        self.current_page = 0

    def action_tasks_habits(self) -> None:
        self.current_mode = "habits"
        self.current_page = 0

    def action_tasks_rewards(self) -> None:
        self.current_mode = "rewards"
        self.current_page = 0

    def action_tasks_all(self) -> None:
        self.current_mode = "all"
        self.current_page = 0

    def action_refresh_data(self) -> None:
        self.refresh_data()

