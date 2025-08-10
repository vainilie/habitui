# ♥♥─── Tag API Methods Mixin ────────────────────────────────────────────────────
from __future__ import annotations

from typing import Any, TypeVar, cast

from habitui.core.models import HabiTuiBaseModel
from habitui.core.client.api_models import HabiticaResponse


T_ClientPydanticModel = TypeVar("T_ClientPydanticModel", bound=HabiTuiBaseModel)
SuccessfulResponseData = dict[str, Any] | list[dict[str, Any]] | list[Any] | HabiticaResponse | None


class TagOperationError(Exception):
	"""Custom exception for failures in tag-related API operations."""


class TagMixin:
	"""A mixin class that provides methods for managing user tags via the Habitica API."""

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
	def _validate_not_empty_param(self, value: str, param_name: str) -> None:
		"""Validate that a given string parameter is not empty.

		:param value: The string value to validate.
		:param param_name: The name of the parameter for error messages.
		:raises TagOperationError: If the value is empty.
		"""
		if not value or not value.strip():
			msg = f"{param_name} cannot be empty."
			raise TagOperationError(msg)

	def _validate_tag_name(self, tag_name: str) -> str:
		"""Validate that the tag name is not empty and returns stripped version.

		:param tag_name: The tag name to validate.
		:return: Stripped version of the tag name.
		:raises TagOperationError: If the tag name is empty or just whitespace.
		"""
		stripped_name = tag_name.strip()
		if not stripped_name:
			msg = "Tag name cannot be empty or just whitespace."
			raise TagOperationError(msg)
		return stripped_name

	def _operation_successful_check(self, api_result: Any) -> bool:
		"""Determine if a tag action (often returning 204 No Content) was successful.

		:param api_result: The result from an API call.
		:return: True if the operation was successful, False otherwise.
		"""
		if isinstance(api_result, HabiticaResponse):
			return api_result.success
		return api_result is None

	async def get_all_tags_raw_response(self) -> HabiticaResponse:
		"""Fetch all user tags, returning the full HabiticaResponse object.

		:return: The full HabiticaResponse object containing all user tags.
		"""
		return cast("HabiticaResponse", await self.get("tags", return_full_response_object=True))

	async def get_all_tags_data(self) -> list[dict[str, Any]]:
		"""Fetch all user tags, returning only the 'data' field from the API response.

		:return: The 'data' field of the API response containing all user tags.
		"""
		result = await self.get("tags")
		return cast("list[dict[str,Any]]", result)

	async def create_new_tag(self, tag_name: str) -> dict[str, Any]:
		"""Create a new tag with the given name.

		:param tag_name: The name for the new tag.
		:return: A dictionary representing the newly created tag object from API 'data' field, or None if failed.
		"""
		validated_name = self._validate_tag_name(tag_name)
		result = await self.post("tags", data={"name": validated_name})
		return cast("dict[str, Any]", result)

	async def update_existing_tag(self, tag_id: str, new_tag_name: str) -> dict[str, Any]:
		"""Update the name of an existing tag.

		:param tag_id: The ID of the tag to update.
		:param new_tag_name: The new name for the tag.
		:return: A dictionary representing the updated tag object from API 'data' field, or None.
		"""
		self._validate_not_empty_param(tag_id, "Tag ID")
		validated_new_name = self._validate_tag_name(new_tag_name)
		result = await self.put(f"tags/{tag_id}", data={"name": validated_new_name})
		return cast("dict[str, Any]", result)

	async def get_existing_tag(self, tag_id: str) -> dict[str, Any]:
		"""Get an existing tag.

		:param tag_id: The ID of the tag to get.
		:return: A dictionary representing the tag object from API 'data' field, or None.
		"""
		self._validate_not_empty_param(tag_id, "Tag ID")
		result = await self.get(f"tags/{tag_id}")
		return cast("dict[str, Any]", result)

	async def delete_existing_tag(self, tag_id: str) -> bool:
		"""Delete a specific tag by its ID.

		:param tag_id: The ID of the tag to delete.
		:return: True if the deletion was successful (API returned 204 No Content), False otherwise.
		"""
		self._validate_not_empty_param(tag_id, "Tag ID")
		result = await self.delete(f"tags/{tag_id}")
		return self._operation_successful_check(result)

	async def reorder_tag_position(self, tag_id: str, target_position_index: int) -> bool:
		"""Move a tag to a specific position in the user's tag list.

		:param tag_id: The ID of the tag to move.
		:param target_position_index: The desired 0-index for the tag.
		:return: True if successful (API returned 204 No Content), False otherwise.
		:raises TagOperationError: If target position is not a non-negative integer.
		"""
		self._validate_not_empty_param(tag_id, "Tag ID")
		if not isinstance(target_position_index, int) or target_position_index < 0:
			msg = "Target position must be a non-negative integer."
			raise TagOperationError(msg)
		payload = {"tagId": tag_id, "to": target_position_index}
		result = await self.post("reorder-tags", data=payload)
		return self._operation_successful_check(result)
