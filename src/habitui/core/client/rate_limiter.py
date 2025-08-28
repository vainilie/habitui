# ♥♥─── Rate Limiter ─────────────────────────────────────────────────────────────
from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any
import asyncio
from collections import deque
from dataclasses import field, dataclass
from collections.abc import Callable

from habitui.custom_logger import log


if TYPE_CHECKING:
    import httpx
# ─── Constants ──────────────────────────────────────────────────────────────────
DEFAULT_REQUESTS_PER_MINUTE: int = 29
MIN_REQUEST_INTERVAL_SECONDS: float = 60.0 / DEFAULT_REQUESTS_PER_MINUTE


# ─── Queue Monitoring Data Classes ──────────────────────────────────────────────
@dataclass
class QueuedRequest:
    """Represents a request waiting in the rate limiter queue."""

    id: str
    endpoint: str
    method: str
    queued_at: float
    estimated_execute_at: float


@dataclass
class RateLimiterQueueStats:
    """Statistics about the rate limiter queue state."""

    current_queue_size: int = 0
    estimated_wait_time_seconds: float = 0.0
    total_requests_queued: int = 0
    total_requests_processed: int = 0
    current_requests_per_minute: float = 0.0
    queued_requests: list[QueuedRequest] = field(default_factory=list)


# ─── Enhanced Rate Limiter ──────────────────────────────────────────────────────
class RateLimiter:
    """A simple asynchronous rate limiter with optional queue monitoring capabilities."""

    def __init__(self, initial_interval: float = MIN_REQUEST_INTERVAL_SECONDS, enable_queue_monitoring: bool = False) -> None:
        """Initialize the RateLimiter.

        :param initial_interval: The initial minimum interval between requests in seconds.
        :param enable_queue_monitoring: Whether to enable queue monitoring features.
        """
        self.current_interval: float = initial_interval
        self.last_request_time: float = 0.0
        self._queue_monitoring_enabled = enable_queue_monitoring
        if enable_queue_monitoring:
            self._request_queue: deque[QueuedRequest] = deque()
            self._request_counter: int = 0
            self._total_queued: int = 0
            self._total_processed: int = 0
            self._queue_change_callback: Callable[[RateLimiterQueueStats], None] | None = None
        log.debug("RateLimiter initialized with interval: {:.2f}s, monitoring: {}", self.current_interval, enable_queue_monitoring)

    async def wait_if_needed(self, endpoint: str = "", method: str = "GET") -> QueuedRequest | None:
        """Pause execution if the time since the last request is less than the current interval.

        :param endpoint: Optional endpoint name for monitoring (only used if monitoring enabled).
        :param method: Optional HTTP method for monitoring (only used if monitoring enabled).
        :returns: QueuedRequest object if monitoring enabled, None otherwise.
        """
        current_time = time.monotonic()
        queued_request = None
        if self._queue_monitoring_enabled:
            self._request_counter += 1
            self._total_queued += 1
            estimated_execute_time = max(current_time, self.last_request_time + self.current_interval)
            queued_request = QueuedRequest(id=f"req_{self._request_counter}", endpoint=endpoint, method=method, queued_at=current_time, estimated_execute_at=estimated_execute_time)
            self._request_queue.append(queued_request)
            self._notify_queue_change()
        elapsed_since_last = current_time - self.last_request_time
        wait_duration = self.current_interval - elapsed_since_last
        if wait_duration > 0:
            log.debug("RateLimiter: Waiting for {:.2f}s to respect rate limit.", wait_duration)
            await asyncio.sleep(wait_duration)
        self.last_request_time = time.monotonic()
        if self._queue_monitoring_enabled and queued_request:
            queued_request.estimated_execute_at = self.last_request_time
            if queued_request in self._request_queue:
                self._request_queue.remove(queued_request)
            self._total_processed += 1
            self._notify_queue_change()
        return queued_request

    def update_rules_from_headers(self, response_headers: httpx.Headers) -> None:
        """Update the rate limiting interval based on information from API response headers.

        :param response_headers: The HTTP response headers.
        """
        retry_after_seconds = response_headers.get("Retry-After")
        if retry_after_seconds:
            try:
                new_interval = float(retry_after_seconds)
                self.current_interval = max(MIN_REQUEST_INTERVAL_SECONDS / 2, new_interval)
                log.warning("RateLimiter: HTTP 429 or Retry-After received. Adjusted interval to {:.2f}s.", self.current_interval)
                if self._queue_monitoring_enabled:
                    self._update_queue_estimates()
            except ValueError:
                log.warning("RateLimiter: Could not parse Retry-After header value: '{}'.", retry_after_seconds)
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
                    self.current_interval = max(self.current_interval, new_suggested_interval)
                    log.warning("RateLimiter: Low requests remaining ({}/{}). Proactively adjusted interval to {:.2f}s.", remaining, limit, self.current_interval)
                    if self._queue_monitoring_enabled:
                        self._update_queue_estimates()
            except ValueError:
                log.warning("RateLimiter: Could not parse X-RateLimit headers.")

    # ─── Queue Monitoring Methods (only work if monitoring enabled) ─────────────
    def set_queue_change_callback(self, callback: Callable[[RateLimiterQueueStats], None]) -> None:
        """Set callback to be notified of queue state changes.

        :param callback: Function to call when queue state changes.
        :raises RuntimeError: If queue monitoring is not enabled.
        """
        if not self._queue_monitoring_enabled:
            msg = "Queue monitoring must be enabled to use callbacks"
            raise RuntimeError(msg)
        self._queue_change_callback = callback

    @property
    def get_queue_stats(self) -> RateLimiterQueueStats | None:
        """Get current queue statistics.

        :returns: Queue statistics if monitoring enabled, None otherwise.
        """
        if not self._queue_monitoring_enabled:
            return None
        current_time = time.monotonic()
        estimated_wait = max(0, (self.last_request_time + self.current_interval) - current_time)
        current_rpm = 60.0 / self.current_interval if self.current_interval > 0 else 0
        return RateLimiterQueueStats(current_queue_size=len(self._request_queue), estimated_wait_time_seconds=estimated_wait, total_requests_queued=self._total_queued, total_requests_processed=self._total_processed, current_requests_per_minute=current_rpm, queued_requests=list(self._request_queue))

    def get_queue_summary(self) -> dict[str, Any]:
        """Get a simple dictionary summary of queue state.

        :returns: Dictionary with queue information, empty if monitoring disabled.
        """
        if not self._queue_monitoring_enabled:
            return {"monitoring_enabled": False}
        stats = self.get_queue_stats
        if not stats:
            return {"monitoring_enabled": True, "error": "Could not get stats"}
        return {
            "monitoring_enabled": True,
            "queue_size": stats.current_queue_size,
            "estimated_wait_seconds": round(stats.estimated_wait_time_seconds, 2),
            "requests_per_minute": round(stats.current_requests_per_minute, 1),
            "total_queued": stats.total_requests_queued,
            "total_processed": stats.total_requests_processed,
            "queued_endpoints": [req.endpoint for req in stats.queued_requests],
        }

    def _update_queue_estimates(self) -> None:
        """Update estimated execution times for queued requests."""
        if not self._queue_monitoring_enabled:
            return
        current_time = time.monotonic()
        next_execution_time = max(current_time, self.last_request_time)
        for i, request in enumerate(self._request_queue):
            request.estimated_execute_at = next_execution_time + (i * self.current_interval)

    def _notify_queue_change(self) -> None:
        """Notify callback about queue state change."""
        if not self._queue_monitoring_enabled or not self._queue_change_callback:
            return
        stats = self.get_queue_stats
        if stats:
            self._queue_change_callback(stats)


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
        return {"total_requests": self.total_requests, "successful_requests": self.successful_requests, "failed_requests": self.failed_requests, "average_response_time_seconds": round(self.average_response_time_seconds, 3)}
