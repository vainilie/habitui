# ♥♥─── Habitica API Client Core ──────────────────────────────────────────────────
"""Core asynchronous HTTP client for interacting with the Habitica API."""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any, Self, Literal, NoReturn, overload
import asyncio

import httpx
from pydantic import BaseModel, ValidationError

from habitui.custom_logger import log
from habitui.config.app_config import app_config

from .api_models import T_PydanticModel, HabiticaAPIError, HabiticaResponse, SuccessfulResponseData
from .rate_limiter import RateLimiter, RequestExecutionStats


if TYPE_CHECKING:
    from uuid import UUID
# ─── Constants ─────────────────────────────────────────────────────────────────
DEFAULT_REQUESTS_PER_MINUTE: int = 29
MIN_REQUEST_INTERVAL_SECONDS: float = 60.0 / DEFAULT_REQUESTS_PER_MINUTE
FALLBACK_BASE_URL: str = "https://habitica.com/api/v3/"
CODE_RATE_LIMIT_EXCEEDED = 429
CODE_SUCCESS_NO_MSG = 204


# ─── Habitica API ──────────────────────────────────────────────────────────────
def _format_response_data(habitica_response: HabiticaResponse, response: httpx.Response, parse_to_model: type[T_PydanticModel] | None, normalized_endpoint: str, return_full_response_object: bool) -> Any:
    """Format and return the appropriate response data."""
    if return_full_response_object:
        return habitica_response

    response_data_field = habitica_response.data
    if parse_to_model and response_data_field is not None:
        try:
            return parse_to_model.model_validate(response_data_field)
        except ValidationError as model_val_err:
            log.error("Pydantic validation error for target model {} on {}: {}", parse_to_model.__name__, normalized_endpoint, model_val_err.errors(include_input=False))
            raise HabiticaAPIError(
                message=f"Failed to validate response data into model {parse_to_model.__name__}: {model_val_err}",
                status_code=response.status_code,
                response_data=response_data_field,
            ) from model_val_err

    return response_data_field


class HabiticaAPI:
    """Asynchronous base client for the Habitica API v3."""

    user_id: UUID
    api_token: str
    base_api_url: str
    _client: httpx.AsyncClient | None = None
    api_headers: dict[str, str]
    rate_limiter: RateLimiter
    request_stats: RequestExecutionStats

    def __init__(self, config_override: Any | None = None, enable_queue_monitoring: bool = False) -> None:
        """Initialize the Habitica API client.

        :param config_override: Optional configuration object to override `application_settings.api`.
        :param enable_queue_monitoring: Whether to enable queue monitoring features.
        """
        api_config_source = config_override or app_config.habitica
        if not (hasattr(api_config_source, "user_id") and hasattr(api_config_source, "api_token") and hasattr(api_config_source.api_token, "get_secret_value")):
            log.critical("HabiticaAPI: API configuration is missing or invalid (user_id, api_token).")
            msg = "Invalid API configuration provided for HabiticaAPI client."
            raise ValueError(msg)
        self.user_id = api_config_source.user_id
        self.api_token = api_config_source.api_token.get_secret_value()
        self.base_api_url = FALLBACK_BASE_URL
        if not (self.user_id and self.api_token):
            log.critical("HabiticaAPI: User ID or API Token is missing after configuration load.")
            msg = "User ID and API Token are required for HabiticaAPI client."
            raise ValueError(msg)
        self.api_headers = {"x-client": f"{self.user_id}-HabiTUIClient", "x-api-user": str(self.user_id), "x-api-key": self.api_token, "Content-Type": "application/json", "Accept": "application/json"}
        self.rate_limiter = RateLimiter(enable_queue_monitoring=enable_queue_monitoring)
        self.request_stats = RequestExecutionStats()
        log.success("Connected to Habitica API.")
        log.debug("HabiticaAPI client initialized for user {}... Base URL: {}", str(self.user_id)[:8], self.base_api_url)

    @property
    def async_http_client(self) -> httpx.AsyncClient:
        """Provide access to the `httpx.AsyncClient` instance, creating it if necessary.

        :returns: The httpx.AsyncClient instance.
        """
        if self._client is None or self._client.is_closed:
            log.debug("Initializing new httpx.AsyncClient instance.")
            self._client = httpx.AsyncClient(headers=self.api_headers, base_url=self.base_api_url, timeout=httpx.Timeout(120.0, connect=30.0), follow_redirects=True)
        return self._client

    async def close_client_session(self) -> None:
        """Close the underlying `httpx.AsyncClient` session if it's open."""
        if self._client and not self._client.is_closed:
            log.debug("Closing httpx.AsyncClient session.")
            await self._client.aclose()
        self._client = None

    async def __aenter__(self) -> Self:
        """Enable use as an asynchronous context manager, returns self.

        :returns: The instance of HabiticaAPI.
        """
        return self

    async def __aexit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: object) -> None:
        """Close the client session when exiting the async context manager.

        :param exc_type: The exception type, if an exception was raised.
        :param exc_val: The exception value, if an exception was raised.
        :param exc_tb: The traceback, if an exception was raised.
        """
        await self.close_client_session()

    def get_current_rate_limit_info(self) -> dict[str, Any]:
        """Return current rate limit status and request statistics.

        :returns: A dictionary containing rate limit interval, time since last request, and request statistics summary.
        """
        return {"current_request_interval_s": self.rate_limiter.current_interval, "time_since_last_request_s": round(time.monotonic() - self.rate_limiter.last_request_time, 3), "request_stats": self.request_stats.get_summary_dict()}

    @staticmethod
    def _prepare_request_data(data: Any | None) -> dict[str, Any] | None:
        """Prepare data for an HTTP request body, typically by serializing Pydantic models.

        :param data: The data to prepare. Can be a Pydantic model, a dictionary, or None.
        :returns: The prepared data as a dictionary suitable for JSON serialization, or None.
        """
        if data is None:
            return None
        if isinstance(data, BaseModel):
            return data.model_dump(exclude_unset=True, exclude_none=True, mode="json")
        if isinstance(data, dict):
            return data
        log.warning("Request data is not a Pydantic model or dict, attempting to pass as is: {}", type(data).__name__)
        return data

    async def _execute_request(self, http_method: str, api_endpoint: str, parse_to_model: type[T_PydanticModel] | None = None, return_full_response_object: bool = False, **kwargs: Any) -> Any:
        """Core method for making an HTTP request to the API. Handles rate limiting, request execution, response, error.

        :param http_method: The HTTP method (e.g., "GET", "POST").
        :param api_endpoint: The API endpoint path (e.g., "/user", "tasks/user").
        :param parse_to_model: The 'data' part of a successful response will be parsed into a Pydantic Model.
        :param return_full_response_object: If True, returns the full HabiticaResponse object instead of just 'data'.
        :param kwargs: Additional arguments for `httpx.AsyncClient.request()`.
        :returns:
            - If `return_full_response_object` is True: The full `HabiticaResponse` object.
            - If `parse_to_model` is provided and response is successful with data: An instance of `parse_to_model`.
            - If response is successful with data and no `parse_to_model`: The raw 'data' field (dict/list).
            - If response is successful but no data (e.g., 204 No Content): None.
            - On error, raises :exc:`~habitui.client.exceptions.HabiticaAPIError`.
        :raises HabiticaAPIError: If an API-specific error occurs.
        """
        await self.rate_limiter.wait_if_needed()
        start_time_mono = time.monotonic()
        normalized_endpoint = api_endpoint.lstrip("/")

        try:
            response = await self._make_http_request(http_method, normalized_endpoint, **kwargs)
            if response.status_code == CODE_RATE_LIMIT_EXCEEDED:
                return await self._handle_rate_limit_and_retry(http_method, api_endpoint, response, parse_to_model, return_full_response_object, **kwargs)
            response.raise_for_status()
            request_duration_s = time.monotonic() - start_time_mono
            if response.status_code == CODE_SUCCESS_NO_MSG or not response.content:
                return self._handle_empty_response(response, request_duration_s, http_method, normalized_endpoint, return_full_response_object)
            habitica_response = self._parse_response_json(response, http_method, normalized_endpoint)
            self._validate_api_success(habitica_response, response, normalized_endpoint)
            self.request_stats.record_successful_request(request_duration_s)
            log.debug("Success ({}) : {} {} in {:.3f}s", response.status_code, http_method.upper(), normalized_endpoint, request_duration_s)

            return _format_response_data(habitica_response, response, parse_to_model, normalized_endpoint, return_full_response_object)

        except httpx.HTTPStatusError as http_err:
            self._handle_http_status_error(http_err, http_method, normalized_endpoint)
        except (httpx.RequestError, httpx.TimeoutException) as transport_err:
            self._handle_transport_error(transport_err, http_method, normalized_endpoint)
        except Exception as e:
            self._handle_unexpected_error(e, normalized_endpoint)

    async def _make_http_request(self, http_method: str, normalized_endpoint: str, **kwargs: Any) -> httpx.Response:
        """Make the actual HTTP request and update rate limiter."""
        log.debug("Requesting: {} {} with params: {}, data: {}", http_method.upper(), f"{self.base_api_url}{normalized_endpoint}", kwargs.get("params"), kwargs.get("json") or kwargs.get("data"))
        response = await self.async_http_client.request(method=http_method.upper(), url=normalized_endpoint, **kwargs)
        self.rate_limiter.update_rules_from_headers(response.headers)
        return response

    async def _handle_rate_limit_and_retry(self, http_method: str, api_endpoint: str, response: httpx.Response, parse_to_model: type[T_PydanticModel] | None, return_full_response_object: bool, **kwargs: Any) -> HabiticaResponse | T_PydanticModel | None:
        """Handle rate limit exceeded response and retry the request."""
        retry_after_str = response.headers.get("Retry-After", str(self.rate_limiter.current_interval * 1.5))
        try:
            retry_wait_seconds = float(retry_after_str)
        except ValueError:
            retry_wait_seconds = self.rate_limiter.current_interval * 1.5
        log.warning("Rate limit exceeded (HTTP 429). Retrying after {:.2f} seconds for {}.", retry_wait_seconds, api_endpoint.lstrip("/"))
        await asyncio.sleep(retry_wait_seconds)
        self._last_request_time = time.monotonic()
        return await self._execute_request(http_method, api_endpoint, parse_to_model=parse_to_model, return_full_response_object=return_full_response_object, **kwargs)

    def _handle_empty_response(self, response: httpx.Response, request_duration_s: float, http_method: str, normalized_endpoint: str, return_full_response_object: bool) -> HabiticaResponse | None:
        """Handle responses with no content (204 No Content)."""
        self.request_stats.record_successful_request(request_duration_s)
        log.debug("Success (204 No Content): {} {} in {:.3f}s", http_method.upper(), normalized_endpoint, request_duration_s)
        if return_full_response_object:
            return HabiticaResponse(success=True, data=None, appVersion=response.headers.get("X-App-Version"))
        return None

    def _parse_response_json(self, response: httpx.Response, http_method: str, normalized_endpoint: str) -> HabiticaResponse:
        """Parse JSON response and validate it as HabiticaResponse."""
        try:
            response_json_data = response.json()
        except json.JSONDecodeError as json_err:
            self.request_stats.record_failed_request()
            log.error("JSONDecodeError for {} {}: {}. Response text: {}", http_method.upper(), normalized_endpoint, json_err, response.text[:200])
            raise HabiticaAPIError(
                message=f"Failed to decode JSON response from API: {json_err}",
                status_code=response.status_code,
                response_data=response.text,
            ) from json_err

        try:
            return HabiticaResponse.model_validate(response_json_data)
        except ValidationError as pydantic_err:
            self.request_stats.record_failed_request()
            log.error("Pydantic validation error for HabiticaResponse shell on {}: {}", normalized_endpoint, pydantic_err.errors(include_input=False))
            raise HabiticaAPIError(
                message=f"Could not validate the base API response structure: {pydantic_err}",
                status_code=response.status_code,
                response_data=response_json_data,
            ) from pydantic_err

    def _validate_api_success(self, habitica_response: HabiticaResponse, response: httpx.Response, normalized_endpoint: str) -> None:
        """Validate that the API response indicates success."""
        if not habitica_response.success:
            self.request_stats.record_failed_request()
            error_message = f"API indicated failure: {habitica_response.error} - {habitica_response.message}"
            log.warning("{} for {}. Details: {}", error_message, normalized_endpoint, habitica_response.errors)
            raise HabiticaAPIError(
                message=(habitica_response.message or "API request failed but no message provided."),
                status_code=response.status_code,
                error_type=habitica_response.error,
                response_data=habitica_response.model_dump(),
            )

    def _handle_http_status_error(self, http_err: httpx.HTTPStatusError, http_method: str, normalized_endpoint: str) -> NoReturn:
        """Handle HTTP status errors."""
        self.request_stats.record_failed_request()
        error_response_data = None
        error_message_detail = http_err.response.text[:200]

        try:
            error_response_data = http_err.response.json()
            if isinstance(error_response_data, dict):
                hab_err_resp = HabiticaResponse.model_validate(error_response_data)
                error_message_detail = hab_err_resp.message or hab_err_resp.error or error_message_detail
        except (json.JSONDecodeError, ValidationError):
            pass

        log.warning("HTTPStatusError for {} {}: {} - {}", http_method.upper(), normalized_endpoint, http_err.response.status_code, error_message_detail)

        raise HabiticaAPIError(
            message=f"API request failed with HTTP status {http_err.response.status_code}: {error_message_detail}",
            status_code=http_err.response.status_code,
            error_type=(error_response_data.get("error") if isinstance(error_response_data, dict) else None),
            response_data=error_response_data or http_err.response.text,
        ) from http_err

    def _handle_transport_error(self, transport_err: Exception, http_method: str, normalized_endpoint: str) -> NoReturn:
        """Handle transport and timeout errors."""
        self.request_stats.record_failed_request()
        log.error("Transport/Timeout error for {} {}: {}", http_method.upper(), normalized_endpoint, transport_err)
        raise HabiticaAPIError(
            message=f"API request transport error: {transport_err.__class__.__name__} - {transport_err}",
        ) from transport_err

    def _handle_unexpected_error(self, error: Exception, normalized_endpoint: str) -> NoReturn:
        """Handle unexpected errors."""
        self.request_stats.record_failed_request()
        log.exception("Unexpected error during API request to {}: {}", normalized_endpoint, error)
        raise HabiticaAPIError(message=f"An unexpected error occurred: {error}") from error

    # ─── Overloaded HTTP Methods ──────────────────────────────────────────
    @overload
    async def get(self, api_endpoint: str, *, parse_to_model: type[T_PydanticModel], params: dict[str, Any] | None = None, **kwargs: Any) -> T_PydanticModel | None: ...
    @overload
    async def get(self, api_endpoint: str, *, return_full_response_object: Literal[True], params: dict[str, Any] | None = None, **kwargs: Any) -> HabiticaResponse: ...
    @overload
    async def get(self, api_endpoint: str, params: dict[str, Any] | None = None, **kwargs: Any) -> SuccessfulResponseData: ...
    async def get(self, api_endpoint: str, params: dict[str, Any] | None = None, *, parse_to_model: type[T_PydanticModel] | None = None, return_full_response_object: bool = False, **kwargs: Any) -> SuccessfulResponseData | T_PydanticModel | HabiticaResponse | None:
        """Make a GET request to the specified API endpoint.

        :param api_endpoint: The API endpoint path.
        :param params: Optional dictionary of query parameters.
        :param parse_to_model: If provided, the response data will be parsed into an instance of this Pydantic model.
        :param return_full_response_object: If True, returns the full HabiticaResponse object.
        :param kwargs: Additional arguments passed to the underlying HTTP request.
        :returns: The parsed response data, a Pydantic model instance, the full HabiticaResponse object, or None.
        """
        return await self._execute_request("GET", api_endpoint, parse_to_model=parse_to_model, return_full_response_object=return_full_response_object, params=params, **kwargs)

    @overload
    async def post(self, api_endpoint: str, data: Any | None = None, *, parse_to_model: type[T_PydanticModel], params: dict[str, Any] | None = None, **kwargs: Any) -> T_PydanticModel | None: ...
    @overload
    async def post(self, api_endpoint: str, data: Any | None = None, *, return_full_response_object: Literal[True], params: dict[str, Any] | None = None, **kwargs: Any) -> HabiticaResponse: ...
    @overload
    async def post(self, api_endpoint: str, data: Any | None = None, params: dict[str, Any] | None = None, **kwargs: Any) -> SuccessfulResponseData: ...
    async def post(self, api_endpoint: str, data: Any | None = None, params: dict[str, Any] | None = None, *, parse_to_model: type[T_PydanticModel] | None = None, return_full_response_object: bool = False, **kwargs: Any) -> SuccessfulResponseData | T_PydanticModel | HabiticaResponse | None:
        """Make a POST request, serializing Pydantic models in `data` if provided.

        :param api_endpoint: The API endpoint path.
        :param data: The data to send in the request body. Can be a Pydantic model, a dictionary, or None.
        :param params: Optional dictionary of query parameters.
        :param parse_to_model: If provided, the response data will be parsed into an instance of this Pydantic model.
        :param return_full_response_object: If True, returns the full HabiticaResponse object.
        :param kwargs: Additional arguments passed to the underlying HTTP request.
        :returns: The parsed response data, a Pydantic model instance, the full HabiticaResponse object, or None.
        """
        prepared_body = self._prepare_request_data(data)
        return await self._execute_request("POST", api_endpoint, parse_to_model=parse_to_model, return_full_response_object=return_full_response_object, json=prepared_body, params=params, **kwargs)

    @overload
    async def put(self, api_endpoint: str, data: Any | None = None, *, parse_to_model: type[T_PydanticModel], params: dict[str, Any] | None = None, **kwargs: Any) -> T_PydanticModel | None: ...
    @overload
    async def put(self, api_endpoint: str, data: Any | None = None, *, return_full_response_object: Literal[True], params: dict[str, Any] | None = None, **kwargs: Any) -> HabiticaResponse: ...
    @overload
    async def put(self, api_endpoint: str, data: Any | None = None, params: dict[str, Any] | None = None, **kwargs: Any) -> SuccessfulResponseData: ...
    async def put(self, api_endpoint: str, data: Any | None = None, params: dict[str, Any] | None = None, *, parse_to_model: type[T_PydanticModel] | None = None, return_full_response_object: bool = False, **kwargs: Any) -> SuccessfulResponseData | T_PydanticModel | HabiticaResponse | None:
        """Make a PUT request, serializing Pydantic models in `data` if provided.

        :param api_endpoint: The API endpoint path.
        :param data: The data to send in the request body. Can be a Pydantic model, a dictionary, or None.
        :param params: Optional dictionary of query parameters.
        :param parse_to_model: If provided, the response data will be parsed into an instance of this Pydantic model.
        :param return_full_response_object: If True, returns the full HabiticaResponse object.
        :param kwargs: Additional arguments passed to the underlying HTTP request.
        :returns: The parsed response data, a Pydantic model instance, the full HabiticaResponse object, or None.
        """
        prepared_body = self._prepare_request_data(data)
        return await self._execute_request("PUT", api_endpoint, parse_to_model=parse_to_model, return_full_response_object=return_full_response_object, json=prepared_body, params=params, **kwargs)

    @overload
    async def delete(self, api_endpoint: str, *, parse_to_model: type[T_PydanticModel], params: dict[str, Any] | None = None, **kwargs: Any) -> T_PydanticModel | None: ...
    @overload
    async def delete(self, api_endpoint: str, *, return_full_response_object: Literal[True], params: dict[str, Any] | None = None, **kwargs: Any) -> HabiticaResponse: ...
    @overload
    async def delete(self, api_endpoint: str, params: dict[str, Any] | None = None, **kwargs: Any) -> SuccessfulResponseData: ...
    async def delete(self, api_endpoint: str, params: dict[str, Any] | None = None, *, parse_to_model: type[T_PydanticModel] | None = None, return_full_response_object: bool = False, **kwargs: Any) -> SuccessfulResponseData | T_PydanticModel | HabiticaResponse | None:
        """Make a DELETE request.

        :param api_endpoint: The API endpoint path.
        :param params: Optional dictionary of query parameters.
        :param parse_to_model: If provided, the response data will be parsed into an instance of this Pydantic model.
        :param return_full_response_object: If True, returns the full HabiticaResponse object.
        :param kwargs: Additional arguments passed to the underlying HTTP request.
        :returns: The parsed response data, a Pydantic model instance, the full HabiticaResponse object, or None.
        """
        return await self._execute_request("DELETE", api_endpoint, parse_to_model=parse_to_model, return_full_response_object=return_full_response_object, params=params, **kwargs)

    # ──────────────────────────────────────────────────────────────────────────
    async def get_game_content(self) -> SuccessfulResponseData:
        """Fetch the main game content object (gear, quests, spells, etc.).

        :returns: The game content data.
        """
        return await self.get("/content")

    async def get_anonymized_user_data(self, *, full_response: bool = False) -> SuccessfulResponseData:
        """Fetch the current anonymized user's data.

        :param full_response: If True, returns the full HabiticaResponse object.
        :returns: The user data or the full HabiticaResponse object.
        """
        if full_response:
            return await self.get("/user/anonymized", return_full_response_object=True)
        return await self.get("/user/anonymized")
