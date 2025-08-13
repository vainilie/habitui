# ♥♥─── API Models ───────────────────────────────────────────────────────────────

from __future__ import annotations

from typing import Any

from pydantic import Field, BaseModel, ConfigDict, AliasChoices


# ─── Habitica Response ────────────────────────────────────────────────────────
class HabiticaResponse(BaseModel):
    """A generic base model for common Habitica API responses."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    success: bool = Field(
        ...,
        description="Indicates if the API request was successful.",
    )
    data: dict[str, Any] | list[Any] | bool | str | int | float | None = Field(
        default=None,
    )
    message: str | None = Field(default=None)
    notifications: list[Any] | None = Field(default=None)
    user_version: int | None = Field(
        default=None,
        validation_alias=AliasChoices("userV", "_v"),
        alias="userV",
    )
    app_version: str | None = Field(default=None, alias="appVersion")
    error: str | None = Field(default=None)
    errors: list[HabiticaApiErrorDetail] | None = Field(default=None)


# ─── Habitica API Error ───────────────────────────────────────────────────────
class HabiticaAPIError(Exception):
    """Custom exception raised for errors originating from the Habitica API.

    :param message: The primary error message.
    :param status_code: The HTTP status code of the API response, if available.
    :param error_type: A Habitica-specific error type string (e.g., 'NotFound', 'InvalidInput').
    :param response_data: The raw response data (often a dict) from the API, if available.
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        error_type: str | None = None,
        response_data: Any | None = None,
    ) -> None:
        """Initialize a custom exception raised for errors originating from the Habitica API."""
        super().__init__(message)
        self.status_code: int | None = status_code
        self.error_type: str | None = error_type
        self.response_data: Any | None = response_data
        self.base_message = message

    def __str__(self) -> str:
        """Return a string representation of the error, including available details."""
        details_parts: list[str] = []

        if self.status_code is not None:
            details_parts.append(f"Status Code: {self.status_code}")
        if self.error_type:
            details_parts.append(f"Error Type: '{self.error_type}'")

        base_error_message = self.args[0] if self.args else "Habitica API Error"

        if details_parts:
            details_string = f" ({', '.join(details_parts)})"
            return f"{base_error_message}{details_string}"

        return base_error_message


# ─── Habitica API Error Detail ────────────────────────────────────────────────
class HabiticaApiErrorDetail(BaseModel):
    """Represent detailed information about an error returned by the Habitica API."""

    model_config = ConfigDict(extra="allow")

    message: str | None = Field(None, description="User-friendly error message.")
    path: str | None = Field(
        None,
        description="The path or field related to the error.",
    )
    param: str | None = Field(None)
    value: int | str | list[Any] | None = Field(None)
