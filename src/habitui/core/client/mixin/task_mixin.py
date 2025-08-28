# ♥♥─── Task API Methods Mixin ────────────────────────────────────────────────────
from __future__ import annotations

from typing import Any, Literal, cast
from collections.abc import Callable

from habitui.core.models import TaskType, Attribute, ScoreDirection
from habitui.custom_logger import log
from habitui.core.client.api_models import HabiticaResponse, TaskOperationError, T_ClientPydanticModel, SuccessfulResponseData, _validate_not_empty_param, _operation_successful_check


def _normalize_attribute_parameter(attribute: Attribute | str) -> Callable[[], str] | str:
    """Normalize an Attribute enum or string to its string value for API calls.

    :param attribute: The attribute to normalize.
    :return: Normalized string value ('str', 'int', 'con', or 'per').
    :raises TaskOperationError: If the input is invalid.
    """
    if isinstance(attribute, Attribute):
        return attribute.value
    if isinstance(attribute, str) and attribute.lower() in {"str", "int", "con", "per"}:
        return attribute.lower()
    msg = "Invalid attribute. Must be 'str', 'int', 'con', 'per', or an Attribute enum member."
    raise TaskOperationError(msg)


def _normalize_score_direction(direction: ScoreDirection | str) -> Callable[[], str] | str:
    """Normalize a ScoreDirection enum or string to its string value for API calls.

    :param direction: The score direction to normalize.
    :return: Normalized string value ('up' or 'down').
    :raises TaskOperationError: If the input is invalid.
    """
    if isinstance(direction, ScoreDirection):
        return direction.value
    if isinstance(direction, str) and direction.lower() in {"up", "down"}:
        return direction.lower()
    msg = "Score direction must be 'up', 'down', or a ScoreDirection enum member."
    raise TaskOperationError(msg)


def _normalize_task_type_filter(task_type_filter: TaskType | Literal["habits", "dailys", "todos", "rewards"] | None) -> dict[str, str] | None:
    """Normalize task type filter to API parameters.

    :param task_type_filter: The task type filter to normalize.
    :return: Dictionary with 'type' parameter for API call, or None if no filter.
    """
    if not task_type_filter:
        return None

    type_value_str = task_type_filter.value if isinstance(task_type_filter, TaskType) else task_type_filter
    type_mapping = {"habit": "habits", "daily": "dailys", "todo": "todos", "reward": "rewards"}
    api_type_param = type_mapping.get(type_value_str.lower(), type_value_str.lower())
    return {"type": api_type_param}


class TaskMixin:
    """A mixin class that provides methods for managing user tasks via Habitica API."""

    async def get(self, api_endpoint: str, params: dict[str, Any] | None = None, *, parse_to_model: type[T_ClientPydanticModel] | None = None, return_full_response_object: bool = False, **kwargs: Any) -> SuccessfulResponseData | T_ClientPydanticModel | HabiticaResponse | None: ...
    async def post(self, api_endpoint: str, data: Any | None = None, params: dict[str, Any] | None = None, *, parse_to_model: type[T_ClientPydanticModel] | None = None, return_full_response_object: bool = False, **kwargs: Any) -> SuccessfulResponseData | T_ClientPydanticModel | HabiticaResponse | None: ...
    async def put(self, api_endpoint: str, data: Any | None = None, params: dict[str, Any] | None = None, *, parse_to_model: type[T_ClientPydanticModel] | None = None, return_full_response_object: bool = False, **kwargs: Any) -> SuccessfulResponseData | T_ClientPydanticModel | HabiticaResponse | None: ...
    async def delete(self, api_endpoint: str, params: dict[str, Any] | None = None, *, parse_to_model: type[T_ClientPydanticModel] | None = None, return_full_response_object: bool = False, **kwargs: Any) -> SuccessfulResponseData | T_ClientPydanticModel | HabiticaResponse | None: ...
    async def get_user_tasks_raw_response(self, *, task_type_filter: TaskType | Literal["habits", "dailys", "todos", "rewards"] | None = None) -> HabiticaResponse:
        """Fetch user tasks, optionally filtered by type, returning the raw HabiticaResponse.

        :param task_type_filter: Optional filter by task type.
        :return: The full HabiticaResponse object containing user tasks.
        """
        params = _normalize_task_type_filter(task_type_filter)
        return cast("HabiticaResponse", await self.get("tasks/user", params=params, return_full_response_object=True))

    async def get_user_tasks_data(self, *, task_type_filter: TaskType | Literal["habits", "dailys", "todos", "rewards"] | None = None) -> list[dict[str, Any]]:
        """Fetch user tasks, optionally filtered by type, returning the 'data' field.

        :param task_type_filter: Optional filter by task type.
        :return: The 'data' field of the API response containing user tasks.
        """
        params = _normalize_task_type_filter(task_type_filter)
        result = await self.get("tasks/user", params=params)
        return cast("list[dict[str, Any]]", result)

    async def create_new_task(self, task_payload) -> list[dict[str, Any]] | dict[str, Any] | None:  # noqa: ANN001
        """Create a new task (Habit, Daily, Todo, or Reward).

        :param task_payload: The task data, can be a `TaskCreatePayload` model instance or a dictionary.
        :return: The 'data' field of the API response (often the created task object).
        :raises TaskOperationError: If essential fields are missing or invalid.
        """
        if isinstance(task_payload, dict):
            if not task_payload.get("text") or not task_payload.get("type"):
                msg = "Task creation data requires 'text' and 'type'."
                raise TaskOperationError(msg)
            if task_payload["type"] not in {t.value for t in TaskType}:
                msg = f"Invalid task type: {task_payload['type']}."
                raise TaskOperationError(msg)
        result = await self.post("tasks/user", data=task_payload)
        if isinstance(result, list):
            return cast("list[dict[str, Any]]", result)
        if isinstance(result, dict):
            return cast("dict[str, Any]", result)
        return None

    async def update_existing_task(self, task_id: str, update_payload: dict[str, Any]) -> dict[str, Any]:
        """Update an existing task by its ID.

        :param task_id: The ID of the task to update.
        :param update_payload: A dictionary containing the fields to update.
        :return: The 'data' field of the API response (often the updated task object).
        :raises TaskOperationError: If task ID is empty or update payload is empty.
        """
        _validate_not_empty_param(task_id, "Task ID")
        if not update_payload:
            msg = "Update payload cannot be empty."
            raise TaskOperationError(msg)
        result = await self.put(f"tasks/{task_id}", data=update_payload)
        return cast("dict[str, Any]", result)

    async def delete_existing_task(self, task_id: str) -> bool:
        """Delete a task by its ID.

        :param task_id: The ID of the task to delete.
        :return: True if the deletion was successful, False otherwise.
        :raises TaskOperationError: If task ID is empty.
        """
        _validate_not_empty_param(task_id, "Task ID")
        result = await self.delete(f"tasks/{task_id}")
        return _operation_successful_check(result)

    async def score_task_action(self, task_id: str, score_direction: ScoreDirection | Literal["up", "down"] = ScoreDirection.UP) -> dict[str, Any]:
        """Score a task (e.g., completes a To-Do, clicks + or - on a Habit).

        :param task_id: The ID of the task to score.
        :param score_direction: The direction of the score ('up' or 'down').
        :return: The 'data' field of the API response (user stats delta, drops, etc.).
        :raises TaskOperationError: If task ID is empty or score direction is invalid.
        """
        _validate_not_empty_param(task_id, "Task ID")
        direction_value_str = _normalize_score_direction(score_direction)
        result = await self.post(f"tasks/{task_id}/score/{direction_value_str}")
        return cast("dict[str, Any]", result)

    async def assign_task_attribute(self, task_id: str, task_attribute: Attribute | Literal["str", "int", "con", "per"]) -> dict[str, Any]:
        """Assign a primary attribute (STR, INT, CON, PER) to a task.

        :param task_id: The ID of the task.
        :param task_attribute: The attribute to assign.
        :return: The 'data' field of the API response (updated task).
        :raises TaskOperationError: If task ID is empty or attribute is invalid.
        """
        _validate_not_empty_param(task_id, "Task ID")
        attribute_value_str = _normalize_attribute_parameter(task_attribute)
        result = await self.update_existing_task(task_id, {"attribute": attribute_value_str})
        return cast("dict[str, Any]", result)

    async def move_task_to_new_position(self, task_id: str, new_target_position: int) -> list[str]:
        """Move a task to a specific position 0 or 1) within its list type.

        :param task_id: The ID of the task to move.
        :param new_target_position: 0 or 1.
        :return: The 'data' field of the API response (new order of task IDs, etc.).
        :raises TaskOperationError: If task ID is empty or target position is invalid.
        """
        _validate_not_empty_param(task_id, "Task ID")
        result = await self.post(f"tasks/{task_id}/move/to/{new_target_position}")
        return cast("list[str]", result)

    async def clear_all_completed_todos(self) -> bool:
        """Clear all To-Do tasks that have been marked as completed.

        :return: True if the operation was successful, False otherwise.
        """
        result = await self.post("tasks/clearCompletedTodos")
        return _operation_successful_check(result)

    async def add_tag_to_task(self, task_id: str, tag_id_to_add: str) -> dict[str, Any]:
        """Add an existing tag to a specific task.

        :param task_id: The ID of the task.
        :param tag_id_to_add: The ID of the tag to add.
        :return: The 'data' field of the API response (updated task object).
        :raises TaskOperationError: If task ID or tag ID is empty.
        """
        validated_tag_id = tag_id_to_add
        log.info(f"Executing add_tag_to_task: taskId={task_id}, tagId={validated_tag_id}")
        result = await self.post(f"tasks/{task_id}/tags/{validated_tag_id}")
        return cast("dict[str, Any]", result)

    async def remove_tag_from_task(self, task_id: str, tag_id_to_remove: str) -> dict[str, Any]:
        """Remove a tag from a specific task.

        :param task_id: The ID of the task.
        :param tag_id_to_remove: The ID of the tag to remove.
        :return: The 'data' field of the API response (updated task object).
        :raises TaskOperationError: If task ID or tag ID is empty.
        """
        validated_tag_id = tag_id_to_remove
        result = await self.delete(f"tasks/{task_id}/tags/{validated_tag_id}")
        return cast("dict[str, Any]", result)

    async def add_checklist_item_to_task(self, task_id: str, item_text: str) -> dict[str, Any]:
        """Add a new checklist item to a specified task.

        :param task_id: The ID of the task.
        :param item_text: The text content of the checklist item.
        :return: The 'data' field of the API response (updated task).
        :raises TaskOperationError: If task ID or item text is empty.
        """
        _validate_not_empty_param(task_id, "Task ID")
        _validate_not_empty_param(item_text, "Checklist item text")
        result = await self.post(f"tasks/{task_id}/checklist", data={"text": item_text})
        return cast("dict[str, Any]", result)

    async def update_checklist_item_on_task(self, task_id: str, checklist_item_id: str, new_text: str) -> dict[str, Any]:
        """Update the text of an existing checklist item on a task.

        :param task_id: The ID of the task.
        :param checklist_item_id: The ID of the checklist item to update.
        :param new_text: The new text content for the checklist item.
        :return: The 'data' field of the API response (updated task).
        :raises TaskOperationError: If any ID or text is empty.
        """
        _validate_not_empty_param(task_id, "Task ID")
        _validate_not_empty_param(checklist_item_id, "Checklist Item ID")
        _validate_not_empty_param(new_text, "New checklist item text")
        result = await self.put(f"tasks/{task_id}/checklist/{checklist_item_id}", data={"text": new_text})
        return cast("dict[str, Any]", result)

    async def delete_checklist_item_from_task(self, task_id: str, checklist_item_id: str) -> dict[str, Any]:
        """Delete a checklist item from a specified task.

        :param task_id: The ID of the task.
        :param checklist_item_id: The ID of the checklist item to delete.
        :return: The 'data' field of the API response (updated task).
        :raises TaskOperationError: If any ID is empty.
        """
        _validate_not_empty_param(task_id, "Task ID")
        _validate_not_empty_param(checklist_item_id, "Checklist Item ID")
        result = await self.delete(f"tasks/{task_id}/checklist/{checklist_item_id}")
        return cast("dict[str, Any]", result)

    async def score_checklist_item_on_task(self, task_id: str, checklist_item_id: str) -> dict[str, Any]:
        """Toggle the completion status of a checklist item on a task.

        :param task_id: The ID of the task.
        :param checklist_item_id: The ID of the checklist item to score.
        :return: The 'data' field of the API response (updated task and user stats).
        :raises TaskOperationError: If any ID is empty.
        """
        _validate_not_empty_param(task_id, "Task ID")
        _validate_not_empty_param(checklist_item_id, "Checklist Item ID")
        result = await self.post(f"tasks/{task_id}/checklist/{checklist_item_id}/score")
        return cast("dict[str, Any]", result)
