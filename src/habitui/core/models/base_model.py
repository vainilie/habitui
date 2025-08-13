# ♥♥─── HabiTui Base Models ────────────────────────────────────────────────────
"""Common Pydantic models and configurations for HabiTui."""

from __future__ import annotations

from typing import Any, Self
import datetime

from humps import camelize
from pydantic import BaseModel, ConfigDict
from sqlmodel import Field, SQLModel


# ─── Common Model Configuration ────────────────────────────────────────────────
HABITUI_MODEL_CONFIG = ConfigDict(
    extra="ignore",
    populate_by_name=True,
    alias_generator=camelize,
    arbitrary_types_allowed=True,
    validate_assignment=True,
    use_enum_values=True,
)


# ─── Base Models ──────────────────────────────────────────────────────────────
class HabiTuiBaseModel(BaseModel):
    """Base Pydantic model with shared project configuration."""

    model_config = HABITUI_MODEL_CONFIG

    @classmethod
    def from_api_dict(cls, data: dict[str, Any]) -> Self:
        """Create a model instance from a dictionary.

        :param data: The input dictionary.
        :returns: An instance of the model.
        """
        return cls.model_validate(data)


class HabiTuiSQLModel(SQLModel):
    """Base SQLModel for all database tables."""

    model_config = HABITUI_MODEL_CONFIG  # type: ignore
    id: str = Field(primary_key=True)


# ─── Specific Table Models ────────────────────────────────────────────────────
class ContentMetadata(SQLModel, table=True):
    """Store metadata about fetched content."""

    __tablename__ = "content_metadata"  # type: ignore
    type: str = Field(primary_key=True)
    last_fetched_at: datetime.datetime | None = None
