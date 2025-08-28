# ♥♥─── User API Methods Mixin ────────────────────────────────────────────────────
from __future__ import annotations

from typing import Any, cast

from habitui.custom_logger import log
from habitui.core.client.api_models import HabiticaResponse, UserOperationError, T_ClientPydanticModel, SuccessfulResponseData, _operation_successful_check


class UserMixin:
    """A mixin class that provides methods for managing user data and actions via the Habitica API."""

    async def get(self, api_endpoint: str, params: dict[str, Any] | None = None, *, parse_to_model: type[T_ClientPydanticModel] | None = None, return_full_response_object: bool = False, **kwargs: Any) -> SuccessfulResponseData | T_ClientPydanticModel | HabiticaResponse | None: ...
    async def post(self, api_endpoint: str, data: Any | None = None, params: dict[str, Any] | None = None, *, parse_to_model: type[T_ClientPydanticModel] | None = None, return_full_response_object: bool = False, **kwargs: Any) -> SuccessfulResponseData | T_ClientPydanticModel | HabiticaResponse | None: ...
    async def put(self, api_endpoint: str, data: Any | None = None, params: dict[str, Any] | None = None, *, parse_to_model: type[T_ClientPydanticModel] | None = None, return_full_response_object: bool = False, **kwargs: Any) -> SuccessfulResponseData | T_ClientPydanticModel | HabiticaResponse | None: ...
    async def get_current_user_raw_response(self) -> HabiticaResponse:
        """Get the current authenticated user's data, returning the full HabiticaResponse object."""
        return cast("HabiticaResponse", await self.get("/user", return_full_response_object=True))

    async def get_current_user_data(self) -> dict[str, Any]:
        """Get the current authenticated user's data, returning only the 'data' field from the API response."""
        result = await self.get("/user")
        return cast("dict[str, Any]", result)

    async def update_user_settings_or_data(self, update_payload: dict[str, Any]) -> dict[str, Any]:
        """Update various user settings, preferences, or other writable user data.

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
        """Toggle the user's sleep status (resting in the Inn)."""
        result = await self.post("user/sleep")
        return _operation_successful_check(result)

    async def trigger_user_cron_run(self) -> bool:
        """Manually triggers the user's cron process.

        :return: True if the cron run was successfully triggered (API returns 204 or success), False otherwise.
        """
        result = await self.post("cron")
        return _operation_successful_check(result)

    async def set_user_custom_day_start(self, start_hour: int) -> bool:
        """Set the user's custom day start hour (0-23) for when Dailies reset.

        :param start_hour: The hour (0-23) at which the user's day starts.
        :raises UserOperationError: If the start hour is out of range.
        """
        if not (0 <= start_hour <= 23):
            msg = "Start hour must be an integer between 0 and 23 (inclusive)."
            raise UserOperationError(msg)
        payload = {"dayStart": start_hour}
        result = await self.post("user/custom-day-start", data=payload)
        return _operation_successful_check(result)
