# ♥♥─── Challenge Mixin ──────────────────────────────────────────────────────────
from __future__ import annotations

from typing import Any, Literal, TypeVar, cast

from habitui.core.client.api_models import HabiticaResponse
from habitui.core.models import (
    ChallengeCreate,
    ChallengeTaskKeepOption,
    HabiTuiBaseModel,
    TaskCreatePayload,
    TaskKeepOption,
)

T_ClientPydanticModel = TypeVar("T_ClientPydanticModel", bound=HabiTuiBaseModel)
SuccessfulResponseData = dict[str, Any] | list[dict[str, Any]] | list[Any] | None


class ChallengeOperationError(Exception):
    """Custom exception for failures in challenge-related operations."""


class ChallengeMixin:
    """Provides methods for interacting with the Habitica API's challenge endpoints."""

    async def get(
        self,
        api_endpoint: str,
        params: dict[str, Any] | None = None,
        *,
        parse_to_model: type[T_ClientPydanticModel] | None = None,
        return_full_response_object: bool = False,
        **kwargs: Any,
    ) -> SuccessfulResponseData | T_ClientPydanticModel | HabiticaResponse | None:
        """Placeholder for GET requests."""

    async def post(
        self,
        api_endpoint: str,
        data: Any | None = None,
        params: dict[str, Any] | None = None,
        *,
        parse_to_model: type[T_ClientPydanticModel] | None = None,
        return_full_response_object: bool = False,
        **kwargs: Any,
    ) -> SuccessfulResponseData | T_ClientPydanticModel | HabiticaResponse | None:
        """Placeholder for POST requests."""

    async def put(
        self,
        api_endpoint: str,
        data: Any | None = None,
        params: dict[str, Any] | None = None,
        *,
        parse_to_model: type[T_ClientPydanticModel] | None = None,
        return_full_response_object: bool = False,
        **kwargs: Any,
    ) -> SuccessfulResponseData | T_ClientPydanticModel | HabiticaResponse | None:
        """Placeholder for PUT requests."""

    async def delete(
        self,
        api_endpoint: str,
        params: dict[str, Any] | None = None,
        *,
        parse_to_model: type[T_ClientPydanticModel] | None = None,
        return_full_response_object: bool = False,
        **kwargs: Any,
    ) -> SuccessfulResponseData | T_ClientPydanticModel | HabiticaResponse | None:
        """Placeholder for DELETE requests."""

    def _validate_not_empty_param(self, value: str, param_name: str) -> None:
        """Validates that a given string parameter is not empty."""
        if not value or not value.strip():
            msg = f"{param_name} cannot be empty."
            raise ChallengeOperationError(msg)

    def _normalize_challenge_task_keep_option(self, keep_option_input: ChallengeTaskKeepOption | str) -> str:
        """Normalizes the keep option for challenge tasks when leaving a challenge."""
        if isinstance(keep_option_input, ChallengeTaskKeepOption):
            return keep_option_input.value

        if isinstance(keep_option_input, str) and keep_option_input in {"keep-all", "remove-all"}:
            return keep_option_input

        msg = "Challenge task keep option must be 'keep-all' or 'remove-all', or ChallengeTaskKeepOption enum."
        raise ChallengeOperationError(msg)

    def _normalize_task_keep_option(self, keep_option_input: TaskKeepOption | str) -> str:
        """Validates and normalizes the keep option for individual tasks when unlinking."""
        if isinstance(keep_option_input, TaskKeepOption):
            return keep_option_input.value
        if isinstance(keep_option_input, str) and keep_option_input in {"keep", "remove"}:
            return keep_option_input
        msg = "Individual task keep option must be 'keep' or 'remove', or TaskKeepOption enum."
        raise ChallengeOperationError(msg)

    def _validate_task_creation_dict(self, task_payload: dict[str, Any]) -> None:
        """Basic validation for task creation data dictionary."""
        if not task_payload.get("text") or not task_payload.get("type"):
            msg = "Task data for creation requires at least 'text' and 'type' fields."
            raise ChallengeOperationError(msg)
        if task_payload["type"] not in {"habit", "daily", "todo", "reward"}:
            msg = f"Invalid task type '{task_payload['type']}'. Must be one of 'habit', 'daily', 'todo', 'reward'."
            raise ChallengeOperationError(msg)

    def _validate_challenge_creation_dict(self, challenge_payload: dict[str, Any]) -> None:
        """Basic validation for challenge creation data dictionary."""
        required_fields = {"name", "shortName", "group"}
        missing = [field for field in required_fields if not challenge_payload.get(field)]

        if missing:
            msg = f"Challenge creation data is missing required fields: {', '.join(missing)}."
            raise ChallengeOperationError(msg)

    def _operation_successful_check(self, api_result: Any) -> bool:
        """Determines if an API operation was successful."""
        if isinstance(api_result, HabiticaResponse):
            return api_result.success

        return api_result is None or (isinstance(api_result, (dict, list)) and not api_result)

    async def get_user_challenges_raw(
        self, *, member_only: bool = True, page: int = 0, owned_filter: str | None = None
    ) -> HabiticaResponse:
        """Fetches a single page of challenges for the user, returning the raw HabiticaResponse."""
        params: dict[str, Any] = {"page": page}

        if member_only:
            params["member"] = "true"
        if owned_filter and owned_filter in {"owned", "not_owned"}:
            params["owned"] = owned_filter

        return cast(
            "HabiticaResponse", await self.get("/challenges/user", params=params, return_full_response_object=True)
        )

    async def get_user_challenges_data(
        self, *, member_only: bool = True, owned_filter: str | None = None, page: int = 0
    ) -> list[dict[str, Any]]:
        """Fetches a single page of challenges, returning the 'data' field from the API response."""
        params: dict[str, Any] = {"page": page}

        if member_only:
            params["member"] = "true"
        if owned_filter and owned_filter in {"owned", "not_owned"}:
            params["owned"] = owned_filter

        result = await self.get("/challenges/user", params=params)
        return cast("list[dict[str, Any]]", result)

    async def get_challenge_tasks_raw(self, challenge_id: str) -> HabiticaResponse:
        """Fetches tasks for a challenge, returning the raw HabiticaResponse."""
        self._validate_not_empty_param(challenge_id, "Challenge ID")

        return cast(
            "HabiticaResponse", await self.get(f"/tasks/challenge/{challenge_id}", return_full_response_object=True)
        )

    async def get_challenge_tasks_data(self, challenge_id: str) -> list[dict[str, Any]]:
        """Fetches tasks for a challenge, returning the 'data' field."""
        self._validate_not_empty_param(challenge_id, "Challenge ID")

        result = await self.get(f"/tasks/challenge/{challenge_id}")
        return cast("list[dict[str, Any]]", result)

    async def join_challenge(self, challenge_id: str) -> dict[str, Any]:
        """Joins a specific challenge."""
        self._validate_not_empty_param(challenge_id, "Challenge ID")

        result = await self.post(f"/challenges/{challenge_id}/join")
        return cast("dict[str, Any]", result)

    async def leave_challenge(
        self,
        challenge_id: str,
        task_handling_option: ChallengeTaskKeepOption
        | Literal["keep-all", "remove-all"] = ChallengeTaskKeepOption.KEEP_ALL,
    ) -> bool:
        """Leaves a challenge, specifying how to handle its tasks."""
        self._validate_not_empty_param(challenge_id, "Challenge ID")

        keep_value_str = self._normalize_challenge_task_keep_option(task_handling_option)
        result = await self.post(f"/challenges/{challenge_id}/leave", params={"keep": keep_value_str})
        return self._operation_successful_check(result)

    async def unlink_task_from_challenge(
        self, task_id: str, task_handling_option: TaskKeepOption | Literal["keep", "remove"] = TaskKeepOption.KEEP
    ) -> bool:
        """Unlinks a specific task from its challenge."""
        self._validate_not_empty_param(task_id, "Task ID")

        keep_value_str = self._normalize_task_keep_option(task_handling_option)
        result = await self.post(f"/tasks/unlink-one/{task_id}", params={"keep": keep_value_str})
        return self._operation_successful_check(result)

    async def unlink_all_tasks_from_challenge(
        self,
        challenge_id: str,
        task_handling_option: ChallengeTaskKeepOption
        | Literal["keep-all", "remove-all"] = ChallengeTaskKeepOption.KEEP_ALL,
    ) -> bool:
        """Unlinks all tasks from a specific challenge."""
        self._validate_not_empty_param(challenge_id, "Challenge ID")

        keep_value_str = self._normalize_challenge_task_keep_option(task_handling_option)
        result = await self.post(f"/tasks/unlink-all/{challenge_id}", params={"keep": keep_value_str})
        return self._operation_successful_check(result)

    async def create_new_challenge(self, challenge_payload: ChallengeCreate | dict[str, Any]) -> dict[str, Any]:
        """Creates a new challenge."""
        if isinstance(challenge_payload, dict):
            self._validate_challenge_creation_dict(challenge_payload)

        result = await self.post("/challenges", data=challenge_payload)
        return cast("dict[str, Any]", result)

    async def update_existing_challenge(self, challenge_id: str, update_payload: dict[str, Any]) -> dict[str, Any]:
        """Updates an existing challenge."""
        self._validate_not_empty_param(challenge_id, "Challenge ID")

        if not update_payload:
            msg = "Update payload cannot be empty."
            raise ChallengeOperationError(msg)

        result = await self.put(f"/challenges/{challenge_id}", data=update_payload)
        return cast("dict[str, Any]", result)

    async def clone_existing_challenge(self, challenge_id: str) -> dict[str, Any]:
        """Clones an existing challenge."""
        self._validate_not_empty_param(challenge_id, "Challenge ID")

        result = await self.post(f"/challenges/{challenge_id}/clone")
        return cast("dict[str, Any]", result)

    async def create_task_in_challenge(
        self, challenge_id: str, task_payload: TaskCreatePayload | dict[str, Any]
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Creates a new task within a specific challenge."""
        self._validate_not_empty_param(challenge_id, "Challenge ID")

        if isinstance(task_payload, dict):
            self._validate_task_creation_dict(task_payload)

        result = await self.post(f"/tasks/challenge/{challenge_id}", data=task_payload)
        if isinstance(result, list):
            return cast("list[dict[str,Any]]", result)

        return cast("dict[str, Any]", result)
