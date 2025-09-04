# ♥♥─── Textual Global Logging Integration ──────────────────────────────────────
"""Integrates Textual with the global logging system."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
import contextlib

from loguru import logger

from textual.widgets import RichLog

from habitui.custom_logger import LEVEL_CONFIG


if TYPE_CHECKING:
    from habitui.tui.main_app import HabiTUI


# ─── Enhanced Textual Console Widget ──────────────────────────────────────────
class TextualLogConsole(RichLog):
    """Enhanced console widget for Textual logging."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(markup=True, **kwargs)
        self.app: HabiTUI

    def on_mount(self) -> None:
        self.app.logging.setup_logging_widget(self)


# ─── Textual Sink for Loguru ──────────────────────────────────────────────────
class TextualSink:
    """Loguru sink optimized for Textual widgets."""

    def __init__(self, console_widget: TextualLogConsole) -> None:
        self.console = console_widget

    def __call__(self, message: Any) -> None:
        try:
            record = message.record
            self._write_formatted_message(record)
        except Exception as e:
            self.console.write(f"[red]ERROR in TextualSink: {e}[/]")

    def _write_formatted_message(self, record: dict[str, Any]) -> None:
        # time_str = record["time"].strftime("%H:%M:%S")
        level_name = record["level"].name
        message_text = record["message"]
        level_config = LEVEL_CONFIG.get(level_name, {"icon": "•", "color": "#908caa"})
        icon = level_config.get("icon", "•")
        level_color = level_config.get("color", "#908caa")

        formatted_message = (
            f"[#908caa][/] [{level_color}]{icon}[/] [{level_color}]{message_text}[/]"
        )

        self.console.write(formatted_message, expand=True)


# ─── Integration Helper Functions ──────────────────────────────────────────────
def add_textual_sink(
    console_widget: TextualLogConsole,
    level: str = "INFO",
) -> int:
    sink = TextualSink(console_widget)
    return logger.add(
        sink=sink,
        level=level,
        format="{message}",
        colorize=False,
        backtrace=False,
        diagnose=False,
    )


def remove_textual_sink(sink_id: int) -> None:
    with contextlib.suppress(ValueError):
        logger.remove(sink_id)


# ─── Textual App Mixin ─────────────────────────────────────────────────────────
class LoggingMixin:
    """Mixin for Textual apps that want to integrate logging."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._textual_sink_id: int | None = None

    def setup_logging_widget(
        self,
        log_widget: TextualLogConsole,
        level: str = "INFO",
    ) -> None:
        if self._textual_sink_id is not None:
            remove_textual_sink(self._textual_sink_id)
        self._textual_sink_id = add_textual_sink(log_widget, level)

    def teardown_logging(self) -> None:
        if self._textual_sink_id is not None:
            remove_textual_sink(self._textual_sink_id)
            self._textual_sink_id = None
