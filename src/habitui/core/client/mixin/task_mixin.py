# ♥♥─── Task API Methods Mixin ────────────────────────────────────────────────────
from __future__ import annotations

from typing import Any, Literal, TypeVar, cast

from habitui.core.client.api_models import HabiticaResponse
from habitui.core.models import Attribute, HabiTuiBaseModel, ScoreDirection, TaskCreatePayload, TaskType
from habitui.ui.custom_logger import log

T_ClientPydanticModel = TypeVar("T_ClientPydanticModel", bound=HabiTuiBaseModel)
SuccessfulResponseData = dict[str, Any] | list[dict[str, Any]] | list[Any] | HabiticaResponse | None


class TaskOperationError(Exception):
    """Custom exception for failures in task-related API operations."""


class TaskMixin:
    """A mixin class that provides methods for managing user tasks via Habitica API."""

    async def get(
        self,
        api_endpoint: str,
        params: dict[str, Any] | None = None,
        *,
        parse_to_model: type[T_ClientPydanticModel] | None = None,
        return_full_response_object: bool = False,
        **kwargs: Any,
    ) -> SuccessfulResponseData | T_ClientPydanticModel | HabiticaResponse | None: ...

    async def post(
        self,
        api_endpoint: str,
        data: Any | None = None,
        params: dict[str, Any] | None = None,
        *,
        parse_to_model: type[T_ClientPydanticModel] | None = None,
        return_full_response_object: bool = False,
        **kwargs: Any,
    ) -> SuccessfulResponseData | T_ClientPydanticModel | HabiticaResponse | None: ...

    async def put(
        self,
        api_endpoint: str,
        data: Any | None = None,
        params: dict[str, Any] | None = None,
        *,
        parse_to_model: type[T_ClientPydanticModel] | None = None,
        return_full_response_object: bool = False,
        **kwargs: Any,
    ) -> SuccessfulResponseData | T_ClientPydanticModel | HabiticaResponse | None: ...

    async def delete(
        self,
        api_endpoint: str,
        params: dict[str, Any] | None = None,
        *,
        parse_to_model: type[T_ClientPydanticModel] | None = None,
        return_full_response_object: bool = False,
        **kwargs: Any,
    ) -> SuccessfulResponseData | T_ClientPydanticModel | HabiticaResponse | None: ...

    def _validate_not_empty_param(self, value: str, param_name: str) -> str:
        """Validates a string parameter is not empty and returns its stripped version.

        :param value: The string value to validate.
        :param param_name: The name of the parameter for error messages.
        :return: The stripped string value.
        :raises TaskOperationError: If the parameter is empty or just whitespace.
        """
        stripped_value = value.strip() if isinstance(value, str) else ""
        if not stripped_value:
            msg = f"Parameter '{param_name}' cannot be empty or just whitespace."
            raise TaskOperationError(msg)
        return stripped_value

    def _normalize_score_direction(self, direction: ScoreDirection | str) -> str:
        """Normalizes a ScoreDirection enum or string to its string value for API calls.

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

    def _normalize_attribute_parameter(self, attribute: Attribute | str) -> str:
        """Normalizes an Attribute enum or string to its string value for API calls.

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

    def _operation_successful_check(self, api_result: Any) -> bool:
        """Determines if a task action (often returning 204 No Content) was successful.

        :param api_result: The result from an API call.
        :return: True if the operation was successful, False otherwise.
        """
        if isinstance(api_result, HabiticaResponse):
            return api_result.success
        return api_result is None

    async def get_user_tasks_raw_response(
        self, *, task_type_filter: TaskType | Literal["habits", "dailys", "todos", "rewards"] | None = None
    ) -> HabiticaResponse:
        """Fetches user tasks, optionally filtered by type, returning the raw HabiticaResponse.

        :param task_type_filter: Optional filter by task type.
        :return: The full HabiticaResponse object containing user tasks.
        """
        params: dict[str, str] | None = None
        if task_type_filter:
            type_value_str = task_type_filter.value if isinstance(task_type_filter, TaskType) else task_type_filter
            type_mapping = {"habit": "habits", "daily": "dailys", "todo": "todos", "reward": "rewards"}
            api_type_param = type_mapping.get(type_value_str.lower(), type_value_str.lower())
            params = {"type": api_type_param}
        return cast("HabiticaResponse", await self.get("tasks/user", params=params, return_full_response_object=True))

    async def get_user_tasks_data(
        self, *, task_type_filter: TaskType | Literal["habits", "dailys", "todos", "rewards"] | None = None
    ) -> list[dict[str, Any]]:
        """Fetches user tasks, optionally filtered by type, returning the 'data' field.

        :param task_type_filter: Optional filter by task type.
        :return: The 'data' field of the API response containing user tasks.
        """
        params: dict[str, str] | None = None
        if task_type_filter:
            type_value_str = task_type_filter.value if isinstance(task_type_filter, TaskType) else task_type_filter
            type_mapping = {"habit": "habits", "daily": "dailys", "todo": "todos", "reward": "rewards"}
            api_type_param = type_mapping.get(type_value_str.lower(), type_value_str.lower())
            params = {"type": api_type_param}
        result = await self.get("tasks/user", params=params)
        return cast("list[dict[str, Any]]", result)

    async def create_new_task(
        self, task_payload: TaskCreatePayload | dict[str, Any]
    ) -> list[dict[str, Any]] | dict[str, Any] | None:
        """Creates a new task (Habit, Daily, Todo, or Reward).

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
        """Updates an existing task by its ID.

        :param task_id: The ID of the task to update.
        :param update_payload: A dictionary containing the fields to update.
        :return: The 'data' field of the API response (often the updated task object).
        :raises TaskOperationError: If task ID is empty or update payload is empty.
        """
        self._validate_not_empty_param(task_id, "Task ID")
        if not update_payload:
            msg = "Update payload cannot be empty."
            raise TaskOperationError(msg)
        result = await self.put(f"tasks/{task_id}", data=update_payload)
        return cast("dict[str, Any]", result)

    async def delete_existing_task(self, task_id: str) -> bool:
        """Deletes a task by its ID.

        :param task_id: The ID of the task to delete.
        :return: True if the deletion was successful, False otherwise.
        :raises TaskOperationError: If task ID is empty.
        """
        self._validate_not_empty_param(task_id, "Task ID")
        result = await self.delete(f"tasks/{task_id}")
        return self._operation_successful_check(result)

    async def score_task_action(
        self, task_id: str, score_direction: ScoreDirection | Literal["up", "down"] = ScoreDirection.UP
    ) -> dict[str, Any]:
        """Scores a task (e.g., completes a To-Do, clicks + or - on a Habit).

        :param task_id: The ID of the task to score.
        :param score_direction: The direction of the score ('up' or 'down').
        :return: The 'data' field of the API response (user stats delta, drops, etc.).
        :raises TaskOperationError: If task ID is empty or score direction is invalid.
        """
        self._validate_not_empty_param(task_id, "Task ID")
        direction_value_str = self._normalize_score_direction(score_direction)
        result = await self.post(f"tasks/{task_id}/score/{direction_value_str}")
        return cast("dict[str, Any]", result)

    async def assign_task_attribute(
        self, task_id: str, task_attribute: Attribute | Literal["str", "int", "con", "per"]
    ) -> dict[str, Any]:
        """Assigns a primary attribute (STR, INT, CON, PER) to a task.

        :param task_id: The ID of the task.
        :param task_attribute: The attribute to assign.
        :return: The 'data' field of the API response (updated task).
        :raises TaskOperationError: If task ID is empty or attribute is invalid.
        """
        self._validate_not_empty_param(task_id, "Task ID")
        attribute_value_str = self._normalize_attribute_parameter(task_attribute)
        result = await self.update_existing_task(task_id, {"attribute": attribute_value_str})
        return cast("dict[str, Any]", result)

    async def move_task_to_new_position(self, task_id: str, new_target_position: int) -> list[str]:
        """Moves a task to a specific position 0 or 1) within its list type.

        :param task_id: The ID of the task to move.
        :param new_target_position: 0 or 1.
        :return: The 'data' field of the API response (new order of task IDs, etc.).
        :raises TaskOperationError: If task ID is empty or target position is invalid.
        """
        self._validate_not_empty_param(task_id, "Task ID")
        if not isinstance(new_target_position, int):
            msg = "Target position must be an integer."
            raise TaskOperationError(msg)
        result = await self.post(f"tasks/{task_id}/move/to/{new_target_position}")
        return cast("list[str]", result)

    async def clear_all_completed_todos(self) -> bool:
        """Clears all To-Do tasks that have been marked as completed.

        :return: True if the operation was successful, False otherwise.
        """
        result = await self.post("tasks/clearCompletedTodos")
        return self._operation_successful_check(result)

    async def add_tag_to_task(self, task_id: str, tag_id_to_add: str) -> dict[str, Any]:
        """Adds an existing tag to a specific task.

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
        """Removes a tag from a specific task.

        :param task_id: The ID of the task.
        :param tag_id_to_remove: The ID of the tag to remove.
        :return: The 'data' field of the API response (updated task object).
        :raises TaskOperationError: If task ID or tag ID is empty.
        """
        validated_tag_id = tag_id_to_remove
        result = await self.delete(f"tasks/{task_id}/tags/{validated_tag_id}")
        return cast("dict[str, Any]", result)

    async def add_checklist_item_to_task(self, task_id: str, item_text: str) -> dict[str, Any]:
        """Adds a new checklist item to a specified task.

        :param task_id: The ID of the task.
        :param item_text: The text content of the checklist item.
        :return: The 'data' field of the API response (updated task).
        :raises TaskOperationError: If task ID or item text is empty.
        """
        self._validate_not_empty_param(task_id, "Task ID")
        validated_text = self._validate_not_empty_param(item_text, "Checklist item text")
        result = await self.post(f"tasks/{task_id}/checklist", data={"text": validated_text})
        return cast("dict[str, Any]", result)

    async def update_checklist_item_on_task(
        self, task_id: str, checklist_item_id: str, new_text: str
    ) -> dict[str, Any]:
        """Updates the text of an existing checklist item on a task.

        :param task_id: The ID of the task.
        :param checklist_item_id: The ID of the checklist item to update.
        :param new_text: The new text content for the checklist item.
        :return: The 'data' field of the API response (updated task).
        :raises TaskOperationError: If any ID or text is empty.
        """
        self._validate_not_empty_param(task_id, "Task ID")
        validated_item_id = self._validate_not_empty_param(checklist_item_id, "Checklist Item ID")
        validated_new_text = self._validate_not_empty_param(new_text, "New checklist item text")
        result = await self.put(f"tasks/{task_id}/checklist/{validated_item_id}", data={"text": validated_new_text})
        return cast("dict[str, Any]", result)

    async def delete_checklist_item_from_task(self, task_id: str, checklist_item_id: str) -> dict[str, Any]:
        """Deletes a checklist item from a specified task.

        :param task_id: The ID of the task.
        :param checklist_item_id: The ID of the checklist item to delete.
        :return: The 'data' field of the API response (updated task).
        :raises TaskOperationError: If any ID is empty.
        """
        self._validate_not_empty_param(task_id, "Task ID")
        validated_item_id = self._validate_not_empty_param(checklist_item_id, "Checklist Item ID")
        result = await self.delete(f"tasks/{task_id}/checklist/{validated_item_id}")
        return cast("dict[str, Any]", result)

    async def score_checklist_item_on_task(self, task_id: str, checklist_item_id: str) -> dict[str, Any]:
        """Toggles the completion status of a checklist item on a task.

        :param task_id: The ID of the task.
        :param checklist_item_id: The ID of the checklist item to score.
        :return: The 'data' field of the API response (updated task and user stats).
        :raises TaskOperationError: If any ID is empty.
        """
        self._validate_not_empty_param(task_id, "Task ID")
        validated_item_id = self._validate_not_empty_param(checklist_item_id, "Checklist Item ID")
        result = await self.post(f"tasks/{task_id}/checklist/{validated_item_id}/score")
        return cast("dict[str, Any]", result)
