# ♥♥─── Party Mixin ──────────────────────────────────────────────────────────────
from __future__ import annotations

from typing import Any, TypeVar, cast

from habitui.core.models import HabiTuiBaseModel
from habitui.core.client.api_models import HabiticaResponse


T_ClientPydanticModel = TypeVar("T_ClientPydanticModel", bound=HabiTuiBaseModel)
SuccessfulResponseData = (
    dict[str, Any] | list[dict[str, Any]] | list[Any] | HabiticaResponse | None
)


class PartyOperationError(Exception):
    """Custom exception for failures in party or group-related operations."""


class PartyMixin:
    """Provide methods for interacting with the Habitica API's party endpoints."""

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
        """Validate that a given string parameter is not empty.

        :param value: The string value to validate.
        :param param_name: The name of the parameter for error messages.
        :raises PartyOperationError: If the value is empty.
        """
        if not value or not value.strip():
            msg = f"{param_name} cannot be empty."
            raise PartyOperationError(msg)

    def _operation_successful_check(self, api_result: Any) -> bool:
        """Determine if a party action (often POST) was successful.

        :param api_result: The result from an API call.
        :return: True if the operation was successful, False otherwise.
        """
        if isinstance(api_result, HabiticaResponse):
            return api_result.success
        return (
            api_result is None
            or (isinstance(api_result, dict) and not api_result)
            or (isinstance(api_result, list) and not api_result)
        )

    async def get_current_party_raw_response(self) -> HabiticaResponse:
        """Get the current user's party data, returning the full HabiticaResponse object.

        :return: The full HabiticaResponse object for the current party.
        """
        return cast(
            "HabiticaResponse",
            await self.get("/groups/party", return_full_response_object=True),
        )

    async def get_current_party_data(self) -> dict[str, Any]:
        """Get the current user's party data, returning only the 'data' field from the API response.

        :return: The 'data' field of the API response for the current party.
        """
        result = await self.get("/groups/party")
        return cast("dict[str, Any]", result)

    async def get_group_chat_messages_raw_response(
        self,
        group_id: str = "party",
    ) -> HabiticaResponse:
        """Fetch chat messages for a specific group, returning the full HabiticaResponse. Defaults to 'party'.

        :param group_id: The ID of the group to fetch chat messages for.
        :return: The full HabiticaResponse object containing group chat messages.
        :raises PartyOperationError: If group ID is empty.
        """
        self._validate_not_empty_param(group_id, "Group ID")
        return cast(
            "HabiticaResponse",
            await self.get(
                f"/groups/{group_id}/chat",
                return_full_response_object=True,
            ),
        )

    async def get_group_chat_messages_data(
        self,
        group_id: str = "party",
    ) -> list[dict[str, Any]]:
        """Fetch chat messages for a group, returning the 'data' field (list of messages).

        :param group_id: The ID of the group to fetch chat messages for.
        :return: The 'data' field of the API response containing chat messages.
        :raises PartyOperationError: If group ID is empty.
        """
        self._validate_not_empty_param(group_id, "Group ID")
        result = await self.get(f"/groups/{group_id}/chat")
        return cast("list[dict[str, Any]]", result)

    async def like_group_chat_message(self, group_id: str, chat_id: str) -> bool:
        """Like a specific chat message within a group.

        :param group_id: The ID of the group.
        :param chat_id: The ID of the chat message to like.
        :return: The 'data' field of the API response after liking the message.
        :raises PartyOperationError: If group ID or chat ID is empty.
        """
        self._validate_not_empty_param(group_id, "Group ID")
        self._validate_not_empty_param(chat_id, "Chat Message ID")
        result = await self.post(f"/groups/{group_id}/chat/{chat_id}/like")
        return self._operation_successful_check(result)

    async def delete_group_chat_message(self, group_id: str, chat_id: str) -> bool:
        """Delete a specific chat message within a group.

        :param group_id: The ID of the group.
        :param chat_id: The ID of the chat message to delete.
        :return: The 'data' field of the API response after deleting the message.
        :raises PartyOperationError: If group ID or chat ID is empty.
        """
        self._validate_not_empty_param(group_id, "Group ID")
        self._validate_not_empty_param(chat_id, "Chat Message ID")
        result = await self.delete(f"/groups/{group_id}/chat/{chat_id}")
        return self._operation_successful_check(result)

    async def mark_group_chat_as_seen(self, group_id: str = "party") -> bool:
        """Mark messages in a group chat as seen by the current user.

        :param group_id: The ID of the group chat.
        :return: True if the operation was successful, False otherwise.
        :raises PartyOperationError: If group ID is empty.
        """
        self._validate_not_empty_param(group_id, "Group ID")
        result = await self.post(f"/groups/{group_id}/chat/seen")
        return self._operation_successful_check(result)

    async def post_message_to_group_chat(
        self,
        group_id: str = "party",
        message_content: str = "",
    ) -> SuccessfulResponseData:
        """Post a message to a specified group chat.

        :param group_id: The ID of the group chat.
        :param message_content: The text content of the message to post.
        :return: The 'data' field of the API response (often the posted message).
        :raises PartyOperationError: If group ID or message content is empty.
        """
        self._validate_not_empty_param(group_id, "Group ID")
        stripped_message_content = message_content.strip()
        if not stripped_message_content:
            msg = "Message content cannot be empty."
            raise PartyOperationError(msg)
        payload = {"message": stripped_message_content}
        return await self.post(f"/groups/{group_id}/chat", data=payload)

    async def accept_party_quest_invite(
        self,
        group_id: str = "party",
    ) -> dict[str, Any]:
        """Accept a pending quest invitation for the specified group (usually current party).

        :param group_id: The ID of the group.
        :return: The 'data' field of the API response after accepting the quest.
        :raises PartyOperationError: If group ID is empty.
        """
        self._validate_not_empty_param(group_id, "Group ID")
        result = await self.post(f"/groups/{group_id}/quests/accept")
        return cast("dict[str, Any]", result)

    async def reject_party_quest_invite(
        self,
        group_id: str = "party",
    ) -> dict[str, Any]:
        """Reject a pending quest invitation for the specified group.

        :param group_id: The ID of the group.
        :return: The 'data' field of the API response after rejecting the quest.
        :raises PartyOperationError: If group ID is empty.
        """
        self._validate_not_empty_param(group_id, "Group ID")
        result = await self.post(f"/groups/{group_id}/quests/reject")
        return cast("dict[str, Any]", result)

    async def leave_active_party_quest(
        self,
        group_id: str = "party",
        keep_tasks: bool = True,
    ) -> dict[str, Any]:
        """Leave an active quest without leaving the party itself.

        :param group_id: The ID of the group.
        :param keep_tasks: If True, keep tasks associated with the quest.
        :return: The 'data' field of the API response after leaving the quest.
        :raises PartyOperationError: If group ID is empty.
        """
        self._validate_not_empty_param(group_id, "Group ID")
        params = {"keep": "keep"} if keep_tasks else None
        result = await self.post(f"/groups/{group_id}/quests/leave", params=params)
        return cast("dict[str, Any]", result)

    async def abort_active_party_quest(self, group_id: str = "party") -> dict[str, Any]:
        """Abort an active quest (usually only possible by the quest leader/party leader).

        :param group_id: The ID of the group.
        :return: The 'data' field of the API response after aborting the quest.
        :raises PartyOperationError: If group ID is empty.
        """
        self._validate_not_empty_param(group_id, "Group ID")
        result = await self.post(f"/groups/{group_id}/quests/abort")
        return cast("dict[str, Any]", result)

    async def cast_skill_on_target(
        self,
        spell_key: str,
        target_id: str | None = None,
    ) -> SuccessfulResponseData:
        """Cast a class skill/spell, optionally targeting another user.

        :param spell_key: The key of the spell to cast.
        :param target_id: Optional ID of the user or task to target.
        :return: The 'data' field of the API response after casting the skill.
        :raises PartyOperationError: If spell key is empty.
        """
        self._validate_not_empty_param(spell_key, "Spell ID")
        params = {"targetId": target_id} if target_id else None
        return await self.post(f"/user/class/cast/{spell_key}", params=params)
