# ♥♥─── Global Console and Utilities ───────────────────────────────────────────
from enum import Enum
from typing import Any

from rich.style import Style
from rich.traceback import install as install_rich_traceback

from .theme_manager import ConsoleManager
from .themed_icons import Icons


# ─── Definitions ─────────────────────────────────────────────────────────────
class IconStyle(str, Enum):
    """Enumeration for available icon styles."""

    SIMPLE = "simple"
    CIRCLE = "circle"
    SQUARE = "square"
    CIRCLE_OUTLINE = "circle_outline"
    SQUARE_OUTLINE = "square_outline"


# ─── Initialization ────────────────────────────────────────────────────────────
theme_manager = ConsoleManager()
console = theme_manager.create_console("rose_pine")
icons = Icons.simple

install_rich_traceback(console=console, show_locals=False, word_wrap=True, extra_lines=3, suppress=[])


# ─── Core Functions ────────────────────────────────────────────────────────────
def switch_theme(name: str) -> None:
    """Switch the active console theme."""
    global console

    if not theme_manager.switch_theme(console, name):
        available = theme_manager.get_available_themes()
        msg = f"Theme '{name}' not found. Available: {available}"

        raise ValueError(msg)

    console = theme_manager.create_console(name)


def switch_icons(style: IconStyle) -> None:
    """Switch the active icon set."""
    global icons

    icon_map = {
        IconStyle.SIMPLE: Icons.simple,
        IconStyle.CIRCLE: Icons.circle,
        IconStyle.SQUARE: Icons.square,
        IconStyle.CIRCLE_OUTLINE: Icons.circle_outline,
        IconStyle.SQUARE_OUTLINE: Icons.square_outline,
    }

    icons = icon_map[style]


# ─── Console Utilities ─────────────────────────────────────────────────────────
def get_style_obj_with_console(style_name: str) -> Style:
    """Safely get a Style object from the console, returning an empty style on failure."""
    try:
        style = console.get_style(style_name)

    except Exception:
        style = Style()

    return style


def print(*args: Any, **kwargs: Any) -> None:
    """Print to the console using Rich."""
    console.print(*args, **kwargs)


def clear() -> None:
    """Clear the console screen."""
    console.clear()


def bell() -> None:
    """Make the terminal bell sound."""
    console.bell()
