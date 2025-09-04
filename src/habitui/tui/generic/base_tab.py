# ─── Textual Imports ───────────────────────────────────────────────────────────
from __future__ import annotations

from typing import TYPE_CHECKING
from datetime import datetime

from textual.widget import Widget
from textual.widgets import Label, ProgressBar
from textual.containers import Horizontal

from habitui.ui import icons

# ─── Project-Specific Imports ──────────────────────────────────────────────────
from habitui.core.client import HabiticaClient
from habitui.custom_logger import log
from habitui.core.services.data_vault import DataVault


if TYPE_CHECKING:
    from textual.app import ComposeResult


# ─── Base Tab Class ────────────────────────────────────────────────────────────
def _get_class_icon(klass: str) -> str:
    class_icons = {
        "wizard": icons.WIZARD,
        "mage": icons.WIZARD,
        "healer": icons.HEALER,
        "warrior": icons.WARRIOR,
        "rogue": icons.ROGUE,
        "no class": icons.USER,
    }
    return class_icons[klass]


def _format_date(timestamp: datetime) -> str:
    """Format account creation date."""
    return timestamp.strftime("%d %b %Y") if timestamp else "N/A"


class BaseTab(Widget):
    """Base class for all tabs with unified access to vault and API operations."""

    @property
    def vault(self) -> DataVault:
        """Direct access to app-level vault."""
        return self.app.vault  # type: ignore

    @property
    def client(self) -> HabiticaClient:
        """Direct access to client from vault."""
        return self.vault.client

    @property
    def logger(self):  # noqa: ANN201
        """Direct access to app-level logger."""
        return self.app.logger  # type: ignore

    @property
    def api_handler(self) -> object:
        """Direct access to unified API handler."""
        return self.app.api_handler  # type: ignore

    def refresh_data(self) -> None:
        """Override this method to refresh tab-specific data from vault."""
