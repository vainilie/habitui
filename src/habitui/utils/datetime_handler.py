# ♥♥─── Datetime Handler ─────────────────────────────────────────────────────────
from __future__ import annotations

from typing import Self
from datetime import UTC, tzinfo, datetime

from pydantic import Field, BaseModel, ConfigDict, PrivateAttr, computed_field
from dateutil.tz import tzlocal
import dateutil.parser

from habitui.custom_logger import log


SECONDS_IN_MINUTE: int = 60
SECONDS_IN_HOUR: int = 3600
SECONDS_IN_DAY: int = 86400


# ─── DateTimeHandler Class ─────────────────────────────────────────────────────


class DateTimeHandler(BaseModel):
    """Handle various datetime formats and provides convenient conversions."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    MILLISECONDS_TIMESTAMP_THRESHOLD: int = 2_000_000_000

    timestamp: str | datetime | int | float | None = Field(default=None)
    _local_timezone: tzinfo = PrivateAttr(default_factory=tzlocal)

    @computed_field
    @property
    def utc_datetime(self) -> datetime | None:
        """Convert the timestamp to a UTC datetime object."""
        if self.timestamp is None:
            return None

        try:
            if isinstance(self.timestamp, datetime):
                if self.timestamp.tzinfo is None:
                    return self.timestamp.replace(tzinfo=UTC)

                return self.timestamp.astimezone(UTC)

            if isinstance(self.timestamp, int | float):
                ts_seconds = (
                    self.timestamp / 1000
                    if abs(self.timestamp) > self.MILLISECONDS_TIMESTAMP_THRESHOLD
                    else self.timestamp
                )

                return datetime.fromtimestamp(ts_seconds, tz=UTC)

            if isinstance(self.timestamp, str):
                dt_parsed = dateutil.parser.isoparse(self.timestamp)
                return (
                    dt_parsed.replace(tzinfo=UTC)
                    if dt_parsed.tzinfo is None
                    else dt_parsed.astimezone(UTC)
                )

        except (ValueError, OverflowError) as e:
            log.warning("Could not parse timestamp '{}': {}", self.timestamp, e)
        except TypeError as e:
            log.error(
                "Unsupported timestamp type '{}': {}",
                type(self.timestamp).__name__,
                e,
            )

        return None

    @computed_field
    @property
    def local_datetime(self) -> datetime | None:
        """Convert the UTC datetime to the local timezone."""
        if self.utc_datetime:
            return self.utc_datetime.astimezone(self._local_timezone)

        return None

    @classmethod
    def from_iso(cls, iso_timestamp: str) -> Self:
        """
        Create a DateTimeHandler instance from an ISO 8601 formatted string.

        :param iso_timestamp: ISO 8601 formatted timestamp string.
        :returns: A DateTimeHandler instance.
        """
        return cls(timestamp=iso_timestamp)

    @classmethod
    def from_unix_ms(cls, unix_ms: int) -> Self:
        """
        Create a DateTimeHandler instance from a Unix timestamp in milliseconds.

        :param unix_ms: Unix timestamp in milliseconds.
        :returns: A DateTimeHandler instance.
        """
        return cls(timestamp=unix_ms)

    @classmethod
    def from_unix_seconds(cls, unix_seconds: float) -> Self:
        """
        Create a DateTimeHandler instance from a Unix timestamp in seconds.

        :param unix_seconds: Unix timestamp in seconds.
        :returns: A DateTimeHandler instance.
        """
        return cls(timestamp=unix_seconds)

    @classmethod
    def now(cls) -> Self:
        """
        Create a DateTimeHandler instance representing the current UTC time.

        :returns: A DateTimeHandler instance with the current UTC time.
        """
        return cls(timestamp=datetime.now(UTC))

    def is_past(self) -> bool | None:
        """
        Check if the handled datetime is in the past relative to current UTC time.

        :returns: True if in the past, False if in the future, None if datetime is not set.
        """
        if self.utc_datetime:
            return self.utc_datetime < datetime.now(UTC)

        return None

    def format_time_difference(self) -> str:
        """
        Format the time difference between the handled datetime and the current local time.

        :returns: A human-readable string like "5m ago", "in 2h", or "now".
        """
        if not self.local_datetime:
            return "N/A"

        delta = self.local_datetime - datetime.now(self._local_timezone)
        seconds = abs(delta.total_seconds())

        if seconds < SECONDS_IN_MINUTE:
            return "now"

        days, remainder = divmod(seconds, SECONDS_IN_DAY)
        hours, remainder = divmod(remainder, SECONDS_IN_HOUR)
        minutes, _ = divmod(remainder, SECONDS_IN_MINUTE)

        if days >= 1:
            time_str = f"{int(days)}d"
        elif hours >= 1:
            time_str = f"{int(hours)}h"
        else:
            time_str = f"{int(minutes)}m"

        return f"{time_str} ago" if delta.total_seconds() < 0 else f"in {time_str}"

    def format_local(self, fmt: str = "%Y-%m-%d %H:%M") -> str:
        """
        Format the local datetime into a string.

        :param fmt: The desired format string for strftime.
        :returns: Formatted datetime string or "N/A" if datetime is not set.
        """
        if self.local_datetime:
            return self.local_datetime.strftime(fmt)

        return "N/A"

    def format_utc(self, fmt: str = "%Y-%m-%d %H:%M %Z") -> str:
        """
        Format the UTC datetime into a string.

        :param fmt: The desired format string for strftime.
        :returns: Formatted datetime string or "N/A" if datetime is not set.
        """
        if self.utc_datetime:
            return self.utc_datetime.strftime(fmt)

        return "N/A"

    def format_with_diff(self, date_fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
        """
        Format the local datetime with its human-readable time difference.

        :param date_fmt: The desired format string for the date part.
        :returns: Formatted string like "YYYY-MM-DD HH:MM:SS (X ago)".
        """
        local_time_str = self.format_local(date_fmt)

        if local_time_str == "N/A":
            return "N/A"

        diff_str = self.format_time_difference()
        return f"{local_time_str} ({diff_str})"

    def to_iso(self) -> str | None:
        """
        Convert the UTC datetime to an ISO 8601 formatted string (with 'Z' for UTC).

        :returns: ISO 8601 string or None if datetime is not set.
        """
        if self.utc_datetime:
            return self.utc_datetime.isoformat().replace("+00:00", "Z")

        return None

    def to_unix_ms(self) -> int | None:
        """
        Convert the UTC datetime to a Unix timestamp in milliseconds.

        :returns: Unix timestamp in milliseconds or None if datetime is not set.
        """
        if self.utc_datetime:
            return int(self.utc_datetime.timestamp() * 1000)

        return None

    def to_unix_seconds(self) -> float | None:
        """
        Convert the UTC datetime to a Unix timestamp in seconds.

        :returns: Unix timestamp in seconds or None if datetime is not set.
        """
        if self.utc_datetime:
            return self.utc_datetime.timestamp()

        return None

    @staticmethod
    def get_utc_now() -> datetime:
        """
        Get the current datetime in UTC.

        :returns: The current datetime in UTC.
        """
        return datetime.now(UTC)

    @staticmethod
    def get_local_now() -> datetime:
        """
        Get the current datetime in the local timezone.

        :returns: The current datetime in the local timezone.
        """
        return datetime.now(tzlocal())
