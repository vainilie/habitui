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

    def on_tab_activated(self) -> None:
        log.info("BaseTab: on_tab_activated called, refreshing data")
        self.refresh_data()

    async def execute_operation(
        self,
        operations: list,
        description: str,
        sync_after: str = "user",
    ) -> None:
        """Execute API operations and sync data afterwards.

        :param operations: List of operations to execute
        :param description: Description of the operation
        :param sync_after: Type of synchronization to perform after execution
        """
        await self.api_handler.execute_and_sync(operations, description, sync_after)  # type: ignore

    def _format_date(self, timestamp: datetime) -> str:
        """Format account creation date."""
        return timestamp.strftime("%d %b %Y") if timestamp else "N/A"

    def _batch_update_labels(self, updates: list[tuple[str, str]]) -> None:
        """Update multiple labels at once."""
        for label_id, text in updates:
            try:
                self.query_one(f"#{label_id}", Label).update(text)
            except Exception as e:
                log.debug(f"Could not update label {label_id}: {e}")

    def _create_icon_value_row(
        self,
        row_id: str,
        icon: str,
        text_id: str,
    ) -> ComposeResult:
        """Create a standard icon-value row."""
        with Horizontal(classes="icon-value-row", id=row_id):
            yield Label(getattr(icons, icon), classes="icon")
            yield Label("Loading...", classes="value", id=text_id)

    def _create_progress_bar_row(
        self,
        stat_type: str,
        label: str,
        icon: str,
        css_class: str,
    ) -> ComposeResult:
        """Create a progress bar row."""
        with Horizontal(classes="icon-label-bar-row", id=f"{stat_type}-stats-row"):
            yield Label(getattr(icons, icon), classes=f"icon {css_class}")
            yield Label(label, classes=f"label {css_class}")
            yield ProgressBar(
                id=f"{stat_type}-progress-bar",
                total=100,
                show_eta=False,
                classes=f"stat-bar {css_class}",
            )
            yield Label(
                "0/0",
                id=f"{stat_type}-progress-text",
                classes=f"value {css_class}",
            )

    def _create_icon_label_value_row(
        self,
        row_id: str,
        icon: str,
        label: str,
        text_id: str,
    ) -> ComposeResult:
        """Create an icon-label-value row."""
        with Horizontal(classes="icon-label-value-row", id=row_id):
            yield Label(getattr(icons, icon), classes="icon")
            yield Label(label, classes="label")
            yield Label("Loading...", classes="value", id=text_id)

    def _create_label_value_row(
        self,
        row_id: str,
        label: str,
        text_id: str,
    ) -> ComposeResult:
        """Create a label-value row."""
        with Horizontal(classes="label-value-row", id=row_id):
            yield Label(label, classes="label")
            yield Label("Loading...", classes="value", id=text_id)

    def _update_progress_bar_widget(
        self,
        bar_id: str,
        text_id: str,
        current: int,
        total: int,
    ) -> None:
        """Update a single progress bar and its associated text."""
        try:
            progress_bar = self.query_one(bar_id, ProgressBar)
            progress_bar.total = total
            progress_bar.progress = current
            self.query_one(text_id, Label).update(f"{current}/{total}")
        except Exception as e:
            log.warning(f"Failed to update progress bar {bar_id}: {e}")

    def _get_class_icon(self, klass: str) -> str:
        class_icons = {
            "wizard": icons.WIZARD,
            "mage": icons.WIZARD,
            "healer": icons.HEALER,
            "warrior": icons.WARRIOR,
            "rogue": icons.ROGUE,
            "no class": icons.USER,
        }
        return class_icons[klass]
