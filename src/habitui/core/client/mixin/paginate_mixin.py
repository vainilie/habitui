# ♥♥─── Pagination API Methods ───────────────────────────────────────────────────

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

from habitui.core.models import TaskCollection, HabiTuiBaseModel, ChallengeCollection
from habitui.custom_logger import log
from habitui.core.client.api_models import HabiticaResponse


if TYPE_CHECKING:
	from collections.abc import Callable, Awaitable, AsyncIterator


T_Item = TypeVar("T_Item")
T_ListModel = TypeVar("T_ListModel", bound=HabiTuiBaseModel)
T_ApiClientPydanticModel = TypeVar("T_ApiClientPydanticModel", bound=HabiTuiBaseModel)

SuccessfulResponseData = dict[str, Any] | list[dict[str, Any]] | list[Any] | None


class BasePaginationUtilitiesMixin:
	"""Base mixin providing core pagination utilities."""

	async def get(
		self,
		api_endpoint: str,
		params: dict[str, Any] | None = None,
		*,
		parse_to_model: type[T_ApiClientPydanticModel] | None = None,
		return_full_response_object: bool = False,
		**kwargs: Any,
	) -> SuccessfulResponseData | T_ApiClientPydanticModel | HabiticaResponse | None:
		"""Abstract method declaration for the main 'get' method from HabiticaAPI."""

	async def _fetch_all_pages_incrementally(  # noqa: C901
		self,
		page_fetcher_callable: Callable[[int], Awaitable[Any]],
	) -> AsyncIterator[Any]:
		"""Fetch pages and yields each page's result until an empty or invalid page is encountered.

		:param page_fetcher_callable: A callable that accepts a page number and returns an awaitable page result.
		:yield: The result of each fetched page.
		"""
		current_page_number = 0
		while True:
			log.debug("Pagination: Attempting to fetch page {}...", current_page_number)
			page_result = await page_fetcher_callable(current_page_number)

			log.debug("Pagination: Page {} result type: {}", current_page_number, type(page_result))
			if isinstance(page_result, list):
				log.debug("Pagination: Page {} list length: {}", current_page_number, len(page_result))

			is_empty = False
			if page_result is None:
				is_empty = True
				log.debug("Pagination: Page result is None")
			elif isinstance(page_result, list) and not page_result:
				is_empty = True
				log.debug("Pagination: Page result is empty list")
			elif isinstance(page_result, HabiticaResponse):
				if not page_result.success:
					is_empty = True
					log.debug("Pagination: Response unsuccessful: {}", page_result)
				elif page_result.data is None:
					is_empty = True
					log.debug("Pagination: Response data is None")
				elif isinstance(page_result.data, list) and not page_result.data:
					is_empty = True
					log.debug("Pagination: Response data is empty list")
			elif isinstance(page_result, ChallengeCollection) and not page_result.challenges:
				is_empty = True
				log.debug("Pagination: ChallengeCollection has no challenges")
			elif isinstance(page_result, TaskCollection) and not page_result.all_tasks:
				is_empty = True
				log.debug("Pagination: TaskCollection has no tasks")

			if is_empty:
				log.debug("Pagination: Page {} considered empty. Stopping.", current_page_number)
				break

			log.debug("Pagination: Successfully fetched page {}.", current_page_number)
			yield page_result
			current_page_number += 1

	async def _collect_all_items_from_paginated_source(
		self,
		page_fetcher_callable: Callable[[int], Awaitable[Any]],
		items_extractor_from_page: Callable[[Any], list[T_Item]],
	) -> list[T_Item]:
		"""Collect all individual items from a paginated source into a single list.

		:param page_fetcher_callable: Callable to fetch a page of data.
		:param items_extractor_from_page: Callable to extract a list of items from the fetched page.
		:return: A list containing all collected items.
		"""
		all_collected_items: list[T_Item] = []
		async for page_data_object in self._fetch_all_pages_incrementally(page_fetcher_callable):
			if page_data_object is not None:
				try:
					items_from_this_page = items_extractor_from_page(page_data_object)
					if isinstance(items_from_this_page, list):
						all_collected_items.extend(items_from_this_page)
					else:
						log.warning("Pagination: items_extractor_from_page did not return a list.")
				except Exception as e:
					log.error("Pagination: Error extracting items from page data: {}", e, exc_info=True)
		return all_collected_items


class ChallengePaginationMixin(BasePaginationUtilitiesMixin):
	"""Provide methods to fetch all pages of Habitica challenges."""

	async def get_user_challenges_raw_response(
		self,
		*,
		member_only: bool = True,
		page: int = 0,
		owned_filter: str | None = None,
	) -> HabiticaResponse: ...
	async def get_user_challenges_data(
		self,
		*,
		member_only: bool = True,
		owned_filter: str | None = None,
		page: int = 0,
	) -> SuccessfulResponseData: ...

	async def get_all_user_challenges_raw_responses(
		self,
		*,
		member_only: bool = True,
		owned_filter: str | None = None,
	) -> list[HabiticaResponse]:
		"""Fetch all pages of challenges and returns them as a list of raw HabiticaResponse objects.

		:param member_only: If True, returns only challenges the user is a member of.
		:param owned_filter: Filter by ownership ("owned", "not_owned").
		:return: A list of full HabiticaResponse objects.
		"""
		responses: list[HabiticaResponse] = [
			page_response
			async for page_response in self._fetch_all_pages_incrementally(
				lambda p: self.get_user_challenges_raw_response(
					member_only=member_only,
					page=p,
					owned_filter=owned_filter,
				),
			)
			if isinstance(page_response, HabiticaResponse)
		]
		return responses

	async def iterate_all_user_challenges_raw_responses(
		self,
		*,
		member_only: bool = True,
		owned_filter: str | None = None,
	) -> AsyncIterator[HabiticaResponse]:
		"""Iterate through all pages of challenges, yielding raw HabiticaResponse objects.

		:param member_only: If True, yields only challenges the user is a member of.
		:param owned_filter: Filter by ownership ("owned", "not_owned").
		:yield: Full HabiticaResponse objects.
		"""
		async for page_response in self._fetch_all_pages_incrementally(
			lambda p: self.get_user_challenges_raw_response(member_only=member_only, page=p, owned_filter=owned_filter),
		):
			if isinstance(page_response, HabiticaResponse):
				yield page_response

	async def get_all_user_challenges_data(
		self,
		*,
		member_only: bool = True,
		owned_filter: str | None = None,
	) -> list[dict[str, Any]]:
		"""Fetch all challenges and returns them as a list of dictionaries (data field).

		:param member_only: If True, returns only challenges the user is a member of.
		:param owned_filter: Filter by ownership ("owned", "not_owned").
		:return: A list of dictionaries representing challenge data.
		"""
		return await self._collect_all_items_from_paginated_source(
			page_fetcher_callable=lambda p: self.get_user_challenges_data(
				member_only=member_only,
				owned_filter=owned_filter,
				page=p,
			),
			items_extractor_from_page=lambda page_data: (page_data if isinstance(page_data, list) else []),
		)

	async def iterate_all_user_challenges_data(
		self,
		*,
		member_only: bool = True,
		owned_filter: str | None = None,
	) -> AsyncIterator[dict[str, Any]]:
		"""Iterate through all challenges, yielding individual challenge data dictionaries.

		:param member_only: If True, yields only challenges the user is a member of.
		:param owned_filter: Filter by ownership ("owned", "not_owned").
		:yield: Individual challenge data dictionaries.
		"""
		async for page_data_list in self._fetch_all_pages_incrementally(
			lambda p: self.get_user_challenges_data(member_only=member_only, owned_filter=owned_filter, page=p),
		):
			if isinstance(page_data_list, list):
				for item_dict in page_data_list:
					if isinstance(item_dict, dict):
						yield item_dict


class InboxPaginationMixin(BasePaginationUtilitiesMixin):
	"""Provide methods to fetch all pages of Habitica inbox messages."""

	async def get_inbox_messages_raw_response(
		self,
		*,
		conversation_id: str | None = None,
		page_number: int | None = None,
	) -> HabiticaResponse: ...
	async def get_inbox_messages_data(
		self,
		*,
		conversation_id: str | None = None,
		page_number: int | None = None,
	) -> SuccessfulResponseData: ...

	async def get_all_inbox_messages_raw_responses(
		self,
		*,
		conversation_id: str | None = None,
	) -> list[HabiticaResponse]:
		"""Fetch all pages of inbox messages and returns them as a list of raw HabiticaResponse objects.

		:param conversation_id: Optional ID to fetch messages for a specific conversation.
		:return: A list of full HabiticaResponse objects.
		"""
		responses: list[HabiticaResponse] = [
			page_response
			async for page_response in self._fetch_all_pages_incrementally(
				lambda p: self.get_inbox_messages_raw_response(conversation_id=conversation_id, page_number=p),
			)
			if isinstance(page_response, HabiticaResponse)
		]
		return responses

	async def iterate_all_inbox_messages_raw_responses(
		self,
		*,
		conversation_id: str | None = None,
	) -> AsyncIterator[HabiticaResponse]:
		"""Iterate through all pages of inbox messages, yielding raw HabiticaResponse objects.

		:param conversation_id: Optional ID to fetch messages for a specific conversation.
		:yield: Full HabiticaResponse objects.
		"""
		async for page_response in self._fetch_all_pages_incrementally(
			lambda p: self.get_inbox_messages_raw_response(conversation_id=conversation_id, page_number=p),
		):
			if isinstance(page_response, HabiticaResponse):
				yield page_response

	async def get_all_inbox_messages_data(self, *, conversation_id: str | None = None) -> list[dict[str, Any]]:
		"""Fetch all inbox messages and returns them as a list of dictionaries (data field).

		:param conversation_id: Optional ID to fetch messages for a specific conversation.
		:return: A list of dictionaries representing message data.
		"""
		return await self._collect_all_items_from_paginated_source(
			page_fetcher_callable=lambda p: self.get_inbox_messages_data(
				conversation_id=conversation_id,
				page_number=p,
			),
			items_extractor_from_page=lambda page_data: (page_data if isinstance(page_data, list) else []),
		)

	async def iterate_all_inbox_messages_data(
		self,
		*,
		conversation_id: str | None = None,
	) -> AsyncIterator[dict[str, Any]]:
		"""Iterate through all inbox messages, yielding individual message data dictionaries.

		:param conversation_id: Optional ID to fetch messages for a specific conversation.
		:yield: Individual message data dictionaries.
		"""
		async for page_data_list in self._fetch_all_pages_incrementally(
			lambda p: self.get_inbox_messages_data(conversation_id=conversation_id, page_number=p),
		):
			if isinstance(page_data_list, list):
				for item_dict in page_data_list:
					if isinstance(item_dict, dict):
						yield item_dict
