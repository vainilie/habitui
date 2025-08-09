# ♥♥─── User API Methods Mixin ────────────────────────────────────────────────────

from __future__ import annotations

from typing import Any, TypeVar, cast

from habitui.core.client.api_models import HabiticaResponse
from habitui.core.models import HabiTuiBaseModel
from habitui.ui.custom_logger import log

T_ClientPydanticModel = TypeVar("T_ClientPydanticModel", bound=HabiTuiBaseModel)
SuccessfulResponseData = dict[str, Any] | list[dict[str, Any]] | list[Any] | HabiticaResponse | None


class UserOperationError(Exception):
    """Custom exception for failures in user-related API operations."""


class UserMixin:
    """A mixin class that provides methods for managing user data and actions via the Habitica API."""

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

    def _operation_successful_check(self, api_result: Any) -> bool:
        """Determines if a task action (often returning 204 No Content) was successful.

        :param api_result: The result from an API call.
        :return: True if the operation was successful, False otherwise.
        """
        if isinstance(api_result, HabiticaResponse):
            return api_result.success
        return api_result is None

    async def get_current_user_raw_response(self) -> HabiticaResponse:
        """Gets the current authenticated user's data, returning the full HabiticaResponse object."""
        return cast("HabiticaResponse", await self.get("/user", return_full_response_object=True))

    async def get_current_user_data(self) -> dict[str, Any]:
        """Gets the current authenticated user's data, returning only the 'data' field from the API response."""
        result = await self.get("/user")
        return cast("dict[str, Any]", result)

    async def update_user_settings_or_data(self, update_payload: dict[str, Any]) -> dict[str, Any]:
        """Updates various user settings, preferences, or other writable user data.

        :param update_payload: A dictionary containing the fields and new values to update.
        :return: A dict representing the 'data' field of the API response, which usually contains the updated object.
        :raises UserOperationError: If the update payload is empty.
        """
        if not update_payload:
            msg = "Update payload (update_data) cannot be empty."
            raise UserOperationError(msg)
        log.info("Updating user with payload: {}", update_payload)
        result = await self.put("user", data=update_payload)
        return cast("dict[str, Any]", result)

    async def toggle_user_sleep_status(self) -> bool:
        """Toggles the user's sleep status (resting in the Inn)."""
        result = await self.post("user/sleep")
        return self._operation_successful_check(result)

    async def trigger_user_cron_run(self) -> bool:
        """Manually triggers the user's cron process.

        :return: True if the cron run was successfully triggered (API returns 204 or success), False otherwise.
        """
        result = await self.post("cron")
        return self._operation_successful_check(result)

    async def set_user_custom_day_start(self, start_hour: int) -> bool:
        """Sets the user's custom day start hour (0-23) for when Dailies reset.

        :param start_hour: The hour (0-23) at which the user's day starts.
        :raises UserOperationError: If the start hour is out of range.
        """
        if not (0 <= start_hour <= 23):  # noqa: PLR2004
            msg = "Start hour must be an integer between 0 and 23 (inclusive)."
            raise UserOperationError(msg)
        payload = {"dayStart": start_hour}
        result = await self.post("user/custom-day-start", data=payload)
        return self._operation_successful_check(result)
