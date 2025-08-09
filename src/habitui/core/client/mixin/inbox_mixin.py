# ♥♥─── Inbox Mixin ──────────────────────────────────────────────────────────────
from __future__ import annotations

from typing import Any, TypeVar, cast

from habitui.core.client.api_models import HabiticaResponse
from habitui.core.models import HabiTuiBaseModel
from habitui.custom_logger import log

T_ClientPydanticModel = TypeVar("T_ClientPydanticModel", bound=HabiTuiBaseModel)
SuccessfulResponseData = dict[str, Any] | list[dict[str, Any]] | list[Any] | HabiticaResponse | None


class InboxOperationError(Exception):
    """Custom exception for failures in inbox/private message operations."""


class InboxMixin:
    """A mixin class that provides methods for interacting with the Habitica API's inbox."""

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
    async def delete(
        self,
        api_endpoint: str,
        params: dict[str, Any] | None = None,
        *,
        parse_to_model: type[T_ClientPydanticModel] | None = None,
        return_full_response_object: bool = False,
        **kwargs: Any,
    ) -> SuccessfulResponseData | T_ClientPydanticModel | HabiticaResponse | None: ...
    def _validate_not_empty_param(self, value: str, param_name: str) -> None:
        """Validates that a given ID string is not empty.

        :param value: The string value to validate.
        :param param_name: The name of the parameter for error messages.
        :raises InboxOperationError: If the value is empty.
        """
        if not value or not value.strip():
            e = f"{param_name} cannot be empty."
            raise InboxOperationError(e)

    def _operation_successful_check(self, api_result: Any) -> bool:
        """Determines if a simple action (often POST/DELETE with no complex data return) was successful."""
        if isinstance(api_result, HabiticaResponse):
            return api_result.success
        return api_result is None

    async def get_inbox_messages_raw_response(
        self, *, conversation_id: str | None = None, page_number: int | None = None
    ) -> HabiticaResponse:
        """Fetches inbox messages, returning the full HabiticaResponse object.

        :param conversation_id: Optional ID to fetch messages for a specific conversation.
        :param page_number: Optional page number for paginated results.
        :return: The full HabiticaResponse object.
        """
        params: dict[str, Any] = {}
        if page_number is not None:
            params["page"] = page_number
        if conversation_id:
            params["conversation"] = conversation_id

        return cast(
            "HabiticaResponse", await self.get("/inbox/messages", params=params, return_full_response_object=True)
        )

    async def get_inbox_messages_data(
        self, *, conversation_id: str | None = None, page_number: int | None = None
    ) -> list[dict[str, Any]]:
        """Fetches inbox messages, returning only the 'data' field from the API response.

        :param conversation_id: Optional ID to fetch messages for a specific conversation.
        :param page_number: Optional page number for paginated results.
        :return: The 'data' field of the API response.
        """
        params: dict[str, Any] = {}
        if page_number is not None:
            params["page"] = page_number
        if conversation_id:
            params["conversation"] = conversation_id
        result = await self.get("/inbox/messages", params=params)
        return cast("list[dict[str, Any]]", result)

    async def send_private_message(self, recipient_user_id: str, message_content: str) -> dict[str, Any]:
        """Sends a private message to another user.

        :param recipient_user_id: The UUID of the recipient user.
        :param message_content: The text content of the message.
        :return: A dictionary representing the sent message, or None on failure.
        :raises InboxOperationError: If recipient ID or message content is empty.
        """
        self._validate_not_empty_param(recipient_user_id, "Recipient User ID")
        message_text_stripped = message_content.strip()
        if not message_text_stripped:
            e = "Message content cannot be empty."
            raise InboxOperationError(e)
        payload = {"toUserId": recipient_user_id, "message": message_text_stripped}
        result = await self.post("/members/send-private-message", data=payload)
        return cast("dict[str, Any]", result)

    async def mark_all_private_messages_as_read(self) -> bool:
        """Marks all private messages as read for the current authenticated user.

        :return: True if the operation was successful, False otherwise.
        """
        result = await self.post("/user/mark-pms-read")
        return self._operation_successful_check(result)

    async def delete_private_message(self, message_id_to_delete: str) -> bool:
        """Deletes a specific private message by its ID.

        :param message_id_to_delete: The ID of the message to delete.
        :return: True if the operation was successful, False otherwise.
        :raises InboxOperationError: If message ID is empty.
        """
        self._validate_not_empty_param(message_id_to_delete, "Message ID")
        result = await self.delete(f"/user/messages/{message_id_to_delete}")
        return self._operation_successful_check(result)

    async def like_message(self, message_id_to_like: str) -> bool:
        """Likes a specific message (private or group chat).

        Note: API suggest /inbox/like/:messageId for PMs, and /groups/:groupId/chat/:chatId/like for group messages.
        This implementation uses the V4 PM like endpoint.
        :param message_id_to_like: The ID of the message to like.
        :return: True if the operation was successful, False otherwise.
        :raises InboxOperationError: If message ID is empty.
        """
        self._validate_not_empty_param(message_id_to_like, "Message ID")
        log.info("Liking private message: {}", message_id_to_like[:8])
        result = await self.post(f"/inbox/messages/{message_id_to_like}/like")
        return self._operation_successful_check(result)
