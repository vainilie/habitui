# ♥♥─── Textual Global Logging Integration ──────────────────────────────────────
"""Integrates Textual with the global logging system."""

from __future__ import annotations

from typing import Any

from loguru import logger

from rich.text import Text

from textual.widgets import RichLog

from habitui.custom_logger import LEVEL_CONFIG


# ─── Enhanced Textual Console Widget ──────────────────────────────────────────
class TextualLogConsole(RichLog):
	"""Enhanced console widget for Textual logging."""

	def __init__(self, **kwargs: Any) -> None:
		"""Initializes the TextualLogConsole widget."""
		super().__init__(**kwargs)
		self.file = False

	def print(self, *args: Any, sep: str = " ", end: str = "\n", **kwargs: Any) -> None:  # noqa: ARG002
		"""Prints content to the RichLog, compatible with Rich console interface."""
		if len(args) == 1 and isinstance(args[0], Text):
			self.write(args[0])
		else:
			content = sep.join(str(arg) for arg in args)
			if end != "\n":
				content += end
			text_obj = Text(content)
			self.write(text_obj)

	def on_mount(self) -> None:
		"""Registers this console with the app's logging mixin."""
		from textual.app import App
		if isinstance(self.app, App) and hasattr(self.app, "setup_logging_widget"):
			self.app.setup_logging_widget(self)


# ─── Textual Sink for Loguru ──────────────────────────────────────────────────
class TextualSink:
	"""Loguru sink optimized for Textual widgets."""

	def __init__(self, console_widget: TextualLogConsole) -> None:
		self.console = console_widget
		self._enabled = True

	def __call__(self, message: Any) -> None:
		if not self._enabled:
			return
		try:
			record = message.record
			self._write_formatted_message(record)
		except Exception as e:
			self.console.write(f"ERROR in TextualSink: {e}")

	def _write_formatted_message(self, record: dict[str, Any]) -> None:
		time_str = record["time"].strftime("%H:%M:%S")
		module_str = record["module"]  # noqa: F841
		level_name = record["level"].name
		message_text = record["message"]
		level_config = LEVEL_CONFIG.get(level_name, {"icon": "•", "color": "#908caa"})
		icon = level_config.get("icon", "•")
		level_color = level_config.get("color", "#908caa")
		full_text = Text()
		full_text.append(time_str, style="#6e6a86")
		full_text.append("│", style="#6e6a86")
		full_text.append(f"{module_str:<10}", style="#908caa")
		full_text.append(f"  {icon:<4}", style=level_color)
		try:
			message_part = Text.from_markup(message_text)
		except Exception:
			message_part = Text(message_text)
		if not any(span.style for span in message_part._spans):  # noqa: SLF001
			message_part.stylize(level_color)
		full_text.append_text(message_part)
		self.console.write(full_text)

	def enable(self) -> None:
		"""Enables the sink."""
		self._enabled = True

	def disable(self) -> None:
		"""Disables the sink."""
		self._enabled = False

	def flush(self) -> None:
		"""Flushes the sink (required by the sink protocol)."""
		...


# ─── Integration Helper Functions ──────────────────────────────────────────────
def add_textual_sink(
	console_widget: TextualLogConsole,
	level: str = "INFO",
) -> int:
	"""Adds a Textual sink to the global logger."""
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
	"""Removes a Textual sink from the logger."""
	try:  # noqa: SIM105
		logger.remove(sink_id)
	except ValueError:
		...


# ─── Textual App Mixin ─────────────────────────────────────────────────────────
class LoggingMixin:
	"""Mixin for Textual apps that want to integrate logging."""

	def __init__(self, *args: Any, **kwargs: Any) -> None:
		super().__init__(*args, **kwargs)
		self._textual_sink_id: int | None = None
		self._log_console: TextualLogConsole | None = None

	def _ensure_logging_attrs(self) -> None:
		"""Ensures that logging attributes are initialized."""
		if not hasattr(self, "_textual_sink_id"):
			self._textual_sink_id = None
		if not hasattr(self, "_log_console"):
			self._log_console = None

	def setup_logging_widget(
		self,
		log_widget: TextualLogConsole,
		level: str = "INFO",
	) -> None:
		"""Sets up the logging widget."""
		self._ensure_logging_attrs()
		# Remove existing sink if any
		if self._textual_sink_id is not None:
			remove_textual_sink(self._textual_sink_id)
			self._textual_sink_id = None
		self._log_console = log_widget
		self._textual_sink_id = add_textual_sink(log_widget, level)

	def teardown_logging(self) -> None:
		"""Cleans up logging configuration when the app closes."""
		self._ensure_logging_attrs()
		if self._textual_sink_id is not None:
			remove_textual_sink(self._textual_sink_id)
			self._textual_sink_id = None

	

	def on_unmount(self) -> None:
		"""Textual hook - cleans up logging on unmount."""
		self._ensure_logging_attrs()
		if hasattr(super(), "on_unmount"):
			super().on_unmount()  # pyright: ignore[reportAttributeAccessIssue]
		self.teardown_logging()
