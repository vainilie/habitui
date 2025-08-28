# ♥♥─── HabiTui Task Processor ─────────────────────────────────────────────────
"""Handle processing and parsing of tasks from API data into HabiTui models."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from collections import defaultdict

from box import Box
from pydantic import ValidationError

from habitui.custom_logger import log

from .base_enums import RewardStatus
from .task_model import TaskTodo, TaskDaily, TaskHabit, TaskReward, TaskChecklist, TaskCollection, ChallengeInTask
from .validators import todo_status, daily_status, habit_status, extract_subtasks, parse_nested_challenge


if TYPE_CHECKING:
    from .user_model import UserCollection


def _parse_habit(task_data: Box) -> TaskHabit:
    """Parse a habit task.

    :param task_data: The Box object containing habit task data.
    :returns: A `TaskHabit` instance.
    """
    task_data["status"] = habit_status(task_data.up, task_data.down, task_data.value)
    return TaskHabit.model_validate(task_data.to_dict())


def _parse_todo(task_data: Box) -> TaskTodo:
    """Parse a todo task.

    :param task_data: The Box object containing todo task data.
    :returns: A `TaskTodo` instance.
    """
    task_data["due_date"] = task_data.date
    task_data["status"] = todo_status(task_data.completed, task_data.checklist_progress, task_data.due_date)
    return TaskTodo.model_validate(task_data.to_dict())


class TaskProcessor:
    """Handle the processing and parsing of tasks from API data."""

    def __init__(self, user_vault: UserCollection) -> None:
        self.challenge_map: dict[str, Any] = {}
        self.user_vault = user_vault
        self.counters: defaultdict[str, int] = defaultdict(int)
        self.collections: dict[str, list[Any]] = {"habits": [], "todos": [], "dailys": [], "rewards": [], "subtasks": [], "challenges_tasks_ids": []}

    def process_tasks(self, raw_content: list[dict[str, Any]]) -> TaskCollection:
        """Process all tasks and returns a TaskCollection instance.

        :param raw_content: Raw API data for tasks.
        :returns: A `TaskCollection` instance populated with parsed and validated models.
        """
        for task in raw_content:
            try:
                self._process_single_task(task)
            except (ValidationError, KeyError, TypeError, AttributeError) as e:
                task_id = task.get("id", "unknown")
                task_type = task.get("type", "unknown")
                log.error("Error processing {} task {}: {}", task_type, task_id, e)
        for ch in self.challenge_map.values():
            self.collections["challenges_tasks_ids"].append(ChallengeInTask.model_validate(ch))
        collection = TaskCollection(todos=self.collections["todos"], dailys=self.collections["dailys"], habits=self.collections["habits"], rewards=self.collections["rewards"], subtasks=self.collections["subtasks"], challenges=self.collections["challenges_tasks_ids"])
        collection._user_vault = self.user_vault  # noqa: SLF001
        return collection

    def _process_single_task(self, task: dict[str, Any]) -> None:
        """Process a single task and adds it to the appropriate collection.

        :param task: The raw API data for a single task.
        """
        task_data = Box(task, default_box=True, default_box_attr=None, camel_killer_box=True)
        self._process_challenge(task_data)
        self._process_subtasks(task_data)
        task_type = task_data.type
        task_data["position"] = self.counters[task_type]
        self.counters[task_type] += 1
        self._parse_and_add_task(task_data, task_type)

    def _process_challenge(self, task_data: Box) -> None:
        """Extract and processes challenge information from task data.

        :param task_data: The Box object containing task data.
        """
        challenge_model, challenge_in_task = parse_nested_challenge(task_data.challenge, task_data.id)
        task_data.update(challenge_in_task)
        if challenge_model:
            challenge_id = challenge_model["id"]
            if challenge_id not in self.challenge_map:
                self.challenge_map[challenge_id] = challenge_model
            else:
                existing = self.challenge_map[challenge_id]
                for field in ["short_name", "broken", "winner"]:
                    if challenge_model.get(field) != existing.get(field):
                        log.warning("Challenge field conflict for '{}': {} vs {}", field, challenge_model.get(field), existing.get(field))
                existing["tasks_ids"] = sorted(set(existing.get("tasks_ids", [])) | set(challenge_model.get("tasks_ids", [])))
                existing["broken_tasks_ids"] = sorted(set(existing.get("broken_tasks_ids", [])) | set(challenge_model.get("broken_tasks_ids", [])))

    def _process_subtasks(self, task_data: Box) -> None:
        """Extract and processes subtasks from task data.

        :param task_data: The Box object containing task data.
        """
        subtasks, subtasks_stats = extract_subtasks(task_data.checklist, task_data.id)
        task_data.update(subtasks_stats)
        for sub in subtasks:
            validated_subtask = TaskChecklist.from_api_dict(sub)
            self.collections["subtasks"].append(validated_subtask)

    def _parse_and_add_task(self, task_data: Box, task_type: str) -> None:
        """Parse a task based on its type and adds it to the appropriate collection.

        :param task_data: The Box object containing task data.
        :param task_type: The type of task (e.g., "reward", "habit").
        """
        parsers = {"reward": self._parse_reward, "habit": _parse_habit, "daily": self._parse_daily, "todo": _parse_todo}
        if parser := parsers.get(task_type):
            parsed_task = parser(task_data)
            self.collections[f"{task_type}s"].append(parsed_task)
        else:
            log.warning("No parser found for task type: {}", task_type)

    def _parse_reward(self, task_data: Box) -> TaskReward:
        """Parse a reward task with an affordability check.

        :param task_data: The Box object containing reward task data.
        :returns: A `TaskReward` instance.
        """
        if self.user_vault and task_data.get("value", 0) <= self.user_vault.raw_stats.gp:
            task_data["status"] = RewardStatus.AFFORDABLE
        return TaskReward.model_validate(task_data.to_dict())

    def _parse_daily(self, task_data: Box) -> TaskDaily:
        """Parse a daily task.

        :param task_data: The Box object containing daily task data.
        :returns: A `TaskDaily` instance.
        """
        task_data["status"] = daily_status(completed=bool(task_data.get("completed", False)), due_today=bool(task_data.get("is_due", False)), due_yesterday=bool(task_data.get("yester_daily", False)), checklist_progress=float(task_data.get("checklist_progress", 0.0)), cron=self.user_vault.user_state.needs_cron)
        return TaskDaily.from_api_dict(data=task_data, user=self.user_vault)
