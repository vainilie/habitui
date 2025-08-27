# ♥♥─── Global Application Logger Configuration ───────────────────────────
from __future__ import annotations

from typing import TYPE_CHECKING, Any
from pathlib import Path
from functools import wraps

from loguru import logger
import logging

from rich.text import Text

from .ui.console import console


if TYPE_CHECKING:
    from collections.abc import Callable

# ─── Configuration ─────────────────────────────────────────────────────────────

LEVEL_CONFIG: dict[str, dict[str, str]] = {
    "TRACE": {"icon": "󱐋", "color": "#908caa"},
    "DEBUG": {"icon": "󱏿", "color": "#6e6a86"},
    "INFO": {"icon": "󰫍", "color": "#31748f"},
    "SUCCESS": {"icon": "󰸞", "color": "#9ccfd8"},
    "WARNING": {"icon": "󱍢", "color": "#f6c177"},
    "ERROR": {"icon": "󱎘", "color": "#eb6f92"},
    "CRITICAL": {"icon": "󰚌", "color": "#eb6f92"},
}


# ─── Utility Functions ─────────────────────────────────────────────────────────


def get_project_root() -> Path:
    """Discover the project root directory by searching for marker files."""
    current_path = Path.cwd()
    for parent in [current_path, *current_path.parents]:
        if any(
            (parent / marker).exists()
            for marker in ["pyproject.toml", "setup.py", ".git"]
        ):
            return parent
    return current_path


def get_log_dir() -> Path:
    """Get or create the directory for application logs."""
    log_directory = get_project_root() / "app_data" / "logs"
    log_directory.mkdir(parents=True, exist_ok=True)
    return log_directory


# ─── Logger Class ──────────────────────────────────────────────────────────────


class MinimalLogger:
    """A minimalist logger class encapsulating Loguru configuration."""

    def __init__(self) -> None:
        """Initialize the MinimalLogger and set up logging."""
        self._configured: bool = False
        self.console: Any = console
        self.path: Path = get_log_dir()

        self.setup()

    def setup(
        self,
        console_level: str = "INFO",
        file_level: str = "INFO",
        log_file: str = "app.log",
        rotation: str = "10 MB",
        retention: str = "7 days",
    ) -> None:
        """
        Configure Loguru sinks for console and file output.

        :param console_level: Minimum level for console output (e.g., "INFO", "DEBUG")
        :param file_level: Minimum level for file output (e.g., "INFO", "DEBUG")
        :param log_file: Name of the log file
        :param rotation: Rotation policy (e.g., "10 MB", "daily")
        :param retention: Log file retention policy (e.g., "7 days", "1 month")
        """
        if self._configured:
            return

        logger.remove()  # Remove default handler

        logger.add(
            sink=self._console_sink,  # type: ignore
            level=console_level,
            format="{time:HH:mm:ss}|{module}|{level.name}|{message}",
            colorize=True,
            backtrace=False,
            diagnose=False,
        )  # type: ignore

        log_path = self.path / log_file
        logger.add(
            sink=log_path,
            level=file_level,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
            backtrace=True,
            diagnose=True,
            rotation=rotation,
            retention=retention,
            compression="zip",
            encoding="utf-8",
        )

        self._setup_stdlib_logging()
        self._configured = True

    def _console_sink(self, message: dict[str, Any]) -> None:
        """Get a custom sink function for Rich console output."""
        record = message.record  # pyright: ignore[reportAttributeAccessIssue]
        time_str = record["time"].strftime("%H:%M:%S")
        module_str = record["module"]
        level_name = record["level"].name
        message_text = record["message"]

        level_config = LEVEL_CONFIG.get(level_name, {"icon": "•", "color": "white"})

        time_part = Text(time_str, style="log.time")
        separator = Text("|", style="log.separator")
        module_part = Text(f"{module_str}", style="log.module")
        icon_part = Text(
            f"{level_config['icon']:<2}",
            style=f"log.level.{level_name.lower()}",
        )
        message_part = Text.from_markup(
            message_text,
            style=f"log.level.{level_name.lower()}",
        )

        self.console.print(
            time_part,
            separator,
            module_part,
            icon_part,
            message_part,
            sep=" ",
            end="\n",
        )

    def _setup_stdlib_logging(self) -> None:
        """Integrate standard Python logging with Loguru."""

        class LoguruHandler(logging.Handler):
            """Routes standard logging messages through Loguru."""

            def emit(self, record: logging.LogRecord) -> None:
                """Emit a log record."""
                try:
                    level = logger.level(record.levelname).name
                except ValueError:
                    level = record.levelno

                # Find the caller's frame to correctly attribute the log source
                frame = logging.currentframe()
                depth = 2
                while frame and frame.f_code.co_filename == logging.__file__:
                    frame = frame.f_back
                    depth += 1

                logger.opt(depth=depth, exception=record.exc_info).log(
                    level,
                    record.getMessage(),
                )

        logging.basicConfig(handlers=[LoguruHandler()], level=0, force=True)

        # Suppress verbose output from third-party libraries
        # for name in ["httpx", "httpcore", "urllib3", "requests", "asyncio"]:
        # logging.getLogger(name).setLevel(logging.WARNING)


# ─── Global Logger Instance and Helper Functions ───────────────────────────────

logger_instance = MinimalLogger()


def setup_logging(
    console_level: str = "INFO",
    file_level: str = "INFO",
    log_file: str = "app.log",
    **kwargs: str,
) -> None:
    """
    Initialize the global logger instance.

    :param console_level: Minimum level for console output
    :param file_level: Minimum level for file output
    :param log_file: Name of the log file
    :param kwargs: Additional keyword arguments for Loguru setup (e.g., rotation, retention)
    """
    logger_instance.setup(console_level, file_level, log_file, **kwargs)


def get_logger() -> Any:
    """Get the configured Loguru logger instance."""
    folder_path = get_log_dir()

    if not folder_path.exists():
        folder_path.mkdir(parents=True, exist_ok=True)

    return logger


def logged(func: Callable) -> Callable:
    """Return a decorator to log function calls and their completion/errors.

    :param func: The function to be decorated
    :returns: The wrapped function
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        func_name = f"[i white]{func.__module__}.{func.__name__}[/i white]"
        logger.debug(f"→ Calling {func_name}")

        try:
            result = func(*args, **kwargs)
            logger.debug(f"{LEVEL_CONFIG['INFO']['icon']}  Completed {func_name}")
        except Exception as e:
            logger.error(f"Error in {func_name}: {e}")
            raise
        else:
            return result

    return wrapper


def add_textual_sink(textual_widget: Any, level: str = "TRACE") -> int:
    """
    Add a Loguru sink to a Textual widget for real-time log display.

    :param textual_widget: The Textual widget instance with a `write` method
    :param level: The minimum logging level for this sink
    :returns: The handler ID for the added sink
    """

    def textual_sink(message: dict[str, Any]) -> None:
        record = message.record  # pyright: ignore[reportAttributeAccessIssue]
        time_str = record["time"].strftime("%H:%M:%S")
        level_name = record["level"].name
        msg = record["message"]
        level_config = LEVEL_CONFIG.get(level_name, {"icon": "•", "color": "#908caa"})
        formatted_message = f"{time_str}│{level_config['icon']:<3}{msg}"

        textual_widget.write(formatted_message)

    return logger.add(textual_sink, level=level, format="{message}")  # type: ignore


if not logger_instance._configured:  # noqa: SLF001
    setup_logging()
log = logger
