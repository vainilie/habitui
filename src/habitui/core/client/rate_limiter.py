# ♥♥─── Rate Limiter ─────────────────────────────────────────────────────────────
from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any
import asyncio

from habitui.custom_logger import log


if TYPE_CHECKING:
    import httpx


# ─── Constants ──────────────────────────────────────────────────────────────────
DEFAULT_REQUESTS_PER_MINUTE: int = 29
MIN_REQUEST_INTERVAL_SECONDS: float = 60.0 / DEFAULT_REQUESTS_PER_MINUTE


# ─── Rate Limiter ──────────────────────────────────────────────────────────────
class RateLimiter:
    """A simple asynchronous rate limiter to respect API request frequency limits."""

    def __init__(self, initial_interval: float = MIN_REQUEST_INTERVAL_SECONDS) -> None:
        """Initialize the RateLimiter.

        :param initial_interval: The initial minimum interval between requests in seconds.
        """
        self._current_interval: float = initial_interval
        self._last_request_time: float = 0.0
        log.debug(
            "RateLimiter initialized with interval: {:.2f}s",
            self._current_interval,
        )

    async def wait_if_needed(self) -> None:
        """Pause execution if the time since the last request is less than the current interval.

        Also updates the last request time after waiting or immediately if no wait is needed.
        """
        elapsed_since_last = time.monotonic() - self._last_request_time
        wait_duration = self._current_interval - elapsed_since_last

        if wait_duration > 0:
            log.debug(
                "RateLimiter: Waiting for {:.2f}s to respect rate limit.",
                wait_duration,
            )
            await asyncio.sleep(wait_duration)

        self._last_request_time = time.monotonic()

    def update_rules_from_headers(self, response_headers: httpx.Headers) -> None:
        """Update the rate limiting interval based on information from API response headers.

        :param response_headers: The HTTP response headers.
        """
        retry_after_seconds = response_headers.get("Retry-After")
        if retry_after_seconds:
            try:
                new_interval = float(retry_after_seconds)
                self._current_interval = max(
                    MIN_REQUEST_INTERVAL_SECONDS / 2,
                    new_interval,
                )
                log.warning(
                    "RateLimiter: HTTP 429 or Retry-After received. Adjusted interval to {:.2f}s.",
                    self._current_interval,
                )
            except ValueError:
                log.warning(
                    "RateLimiter: Could not parse Retry-After header value: '{}'.",
                    retry_after_seconds,
                )
            else:
                return

        remaining_requests_str = response_headers.get("X-RateLimit-Remaining")
        limit_per_window_str = response_headers.get("X-RateLimit-Limit")

        if remaining_requests_str and limit_per_window_str:
            try:
                remaining = int(remaining_requests_str)
                limit = int(limit_per_window_str)
                lowest_threshold = 0.1

                if limit > 0 and (remaining / limit) < lowest_threshold:
                    new_suggested_interval = (60.0 / DEFAULT_REQUESTS_PER_MINUTE) * 1.5
                    self._current_interval = max(
                        self._current_interval,
                        new_suggested_interval,
                    )
                    log.warning(
                        "RateLimiter: Low requests remaining ({}/{}). Proactively adjusted interval to {:.2f}s.",
                        remaining,
                        limit,
                        self._current_interval,
                    )
            except ValueError:
                log.warning("RateLimiter: Could not parse X-RateLimit headers.")


# ─── Request Execution Stats ──────────────────────────────────────────────────
class RequestExecutionStats:
    """Track statistics about API request executions."""

    def __init__(self) -> None:
        """Initialize the RequestExecutionStats tracker."""
        self.total_requests: int = 0
        self.successful_requests: int = 0
        self.failed_requests: int = 0
        self._total_response_time_seconds: float = 0.0

    def record_successful_request(self, duration_seconds: float) -> None:
        """Record a successfully completed API request.

        :param duration_seconds: The duration of the successful request in seconds.
        """
        self.total_requests += 1
        self.successful_requests += 1
        self._total_response_time_seconds += duration_seconds

    def record_failed_request(self) -> None:
        """Record a failed API request."""
        self.total_requests += 1
        self.failed_requests += 1

    @property
    def average_response_time_seconds(self) -> float:
        """Calculate the average response time for successful requests.

        :returns: The average response time in seconds, or 0.0 if no successful requests.
        """
        if self.successful_requests > 0:
            return self._total_response_time_seconds / self.successful_requests
        return 0.0

    def get_summary_dict(self) -> dict[str, Any]:
        """Return the current request statistics as a dictionary.

        :returns: A dictionary containing total, successful, failed requests, and average response time.
        """
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "average_response_time_seconds": round(
                self.average_response_time_seconds,
                3,
            ),
        }
