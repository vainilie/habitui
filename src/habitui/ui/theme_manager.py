# ♥♥─── Console Style Manager ────────────────────────────────────────────────────
import json
import os
from pathlib import Path

from rich.console import Console
from rich.style import Style
from rich.theme import Theme

from .custom_logger import log

# ─── Configuration & Types ─────────────────────────────────────────────────────

ThemeData = dict[str, str]
StyleMapping = dict[str, Style]

DEFAULT_THEMES_JSON_PATH = Path(__file__).parent / "themes.json"


def ensure_true_color() -> None:
    """Set environment variables to hint for true color support."""
    os.environ.update({"COLORTERM": "truecolor", "TERM": "xterm-256color"})


# ─── Style Mapper ──────────────────────────────────────────────────────────────


class StyleMapper:
    """Creates rich Style mappings from theme color data."""

    DEFAULT_THEME: dict[str, ThemeData] = {
        "rose_pine": {
            "background": "#191825",
            "foreground": "#777777",
            "brightBlack": "#706e86",
            "brightBlue": "#31748f",
            "brightCyan": "#ebbcba",
            "brightGreen": "#9ccfd8",
            "brightPurple": "#c4a7e7",
            "brightRed": "#eb6f92",
            "brightWhite": "#e0def4",
            "brightYellow": "#f6c177",
            "black": "#706e86",
            "blue": "#31748f",
            "cyan": "#ebbcba",
            "green": "#9ccfd8",
            "purple": "#c4a7e7",
            "red": "#eb6f92",
            "white": "#e0def4",
            "yellow": "#f6c177",
        }
    }

    STYLE_FALLBACKS: dict[str, str] = {
        "primary": "bold blue",
        "secondary": "cyan",
        "success": "green",
        "warning": "yellow",
        "error": "red",
        "info": "blue",
        "muted": "dim white",
        "dim": "dim",
        "text": "white",
        "habit": "cyan",
        "daily": "magenta",
        "todo": "red",
        "reward": "yellow",
        "selected": "reverse",
        "help.key": "bold blue",
        "help.description": "dim white",
        "panel.border": "blue",
        "table.header": "bold blue",
        "log.level.trace": "dim white",
        "log.level.debug": "dim white",
        "log.level.info": "blue",
        "log.level.success": "green",
        "log.level.warning": "yellow",
        "log.level.error": "red",
        "log.level.critical": "bold red",
        "log.time": "dim white",
        "log.separator": "blue",
        "log.module": "dim blue",
    }

    COLOR_MAPPINGS: dict[str, str] = {
        "primary": "purple",
        "secondary": "cyan",
        "success": "green",
        "warning": "yellow",
        "error": "red",
        "info": "blue",
        "muted": "brightBlack",
        "text": "white",
        "selected_bg": "selectionBackground",
        "panel_border": "blue",
        "table_header": "purple",
        "habit": "cyan",
        "daily": "purple",
        "todo": "red",
        "reward": "yellow",
        "hp": "red",
        "mp": "purple",
        "exp": "yellow",
        "accent": "purple",
        "highlight": "yellow",
        "link": "blue",
        "disabled": "brightBlack",
    }

    @staticmethod
    def _get_color(theme_data: ThemeData, key: str, fallback: str = "#888888") -> str:
        """Get a color value from the theme data."""
        return theme_data.get(key, fallback)

    @classmethod
    def create_styles_from_theme(cls, theme_data: ThemeData) -> StyleMapping:
        """Create a rich Style mapping from a theme color dictionary."""
        styles: StyleMapping = {}
        bold_styles = {"primary", "error", "table_header", "help.key", "accent"}
        dim_styles = {"muted", "disabled", "dim"}

        for style_name, color_field in cls.COLOR_MAPPINGS.items():
            color_value = theme_data.get(color_field)
            if not color_value:
                continue

            bold = style_name in bold_styles
            dim = style_name in dim_styles

            if style_name == "selected":
                bg_color = theme_data.get("selectionBackground") or theme_data.get("background") or "#000000"
                styles[style_name] = Style(color=color_value, bgcolor=bg_color, bold=True)
            elif style_name == "selected_bg":
                styles[style_name] = Style(bgcolor=color_value)
            else:
                styles[style_name] = Style(color=color_value, bold=bold, dim=dim)

        styles.update(cls._create_log_styles(theme_data))
        styles.update(cls._create_help_styles(theme_data))
        styles.update(cls._create_ui_styles(theme_data))

        return styles

    @classmethod
    def _create_log_styles(cls, theme_data: ThemeData) -> StyleMapping:
        """Create specific styles for logging output."""
        return {
            "log.level.trace": Style(color=cls._get_color(theme_data, "brightBlack"), dim=True),
            "log.level.debug": Style(color=cls._get_color(theme_data, "brightBlack")),
            "log.level.info": Style(color=cls._get_color(theme_data, "blue")),
            "log.level.success": Style(color=cls._get_color(theme_data, "green")),
            "log.level.warning": Style(color=cls._get_color(theme_data, "yellow")),
            "log.level.error": Style(color=cls._get_color(theme_data, "red")),
            "log.level.critical": Style(color=cls._get_color(theme_data, "red"), bold=True),
            "log.time": Style(color=cls._get_color(theme_data, "brightBlack")),
            "log.separator": Style(color=cls._get_color(theme_data, "blue")),
            "log.module": Style(color=cls._get_color(theme_data, "purple"), dim=True),
        }

    @classmethod
    def _create_help_styles(cls, theme_data: ThemeData) -> StyleMapping:
        """Create specific styles for help text."""
        return {
            "help.key": Style(color=cls._get_color(theme_data, "purple"), bold=True),
            "help.description": Style(color=cls._get_color(theme_data, "brightBlack")),
            "help.title": Style(color=cls._get_color(theme_data, "yellow"), bold=True),
            "help.section": Style(color=cls._get_color(theme_data, "cyan")),
        }

    @classmethod
    def _create_ui_styles(cls, theme_data: ThemeData) -> StyleMapping:
        """Create specific styles for common UI elements."""
        return {
            "panel.border": Style(color=cls._get_color(theme_data, "blue")),
            "panel.title": Style(color=cls._get_color(theme_data, "purple"), bold=True),
            "table.header": Style(color=cls._get_color(theme_data, "purple"), bold=True),
            "table.row_even": Style(bgcolor=cls._get_color(theme_data, "background")),
            "table.row_odd": Style(bgcolor=cls._get_color(theme_data, "black")),
            "progress.complete": Style(color=cls._get_color(theme_data, "green")),
            "progress.remaining": Style(color=cls._get_color(theme_data, "brightBlack")),
            "status.good": Style(color=cls._get_color(theme_data, "green")),
            "status.bad": Style(color=cls._get_color(theme_data, "red")),
            "status.neutral": Style(color=cls._get_color(theme_data, "yellow")),
        }


class ConsoleManager:
    """Manage rich Console instances and their themes."""

    def __init__(self, themes_file_path: Path | None = None):
        """Initialize the manager with an optional path to a themes JSON file."""
        self.themes_file_path = themes_file_path or DEFAULT_THEMES_JSON_PATH
        self._themes: dict[str, ThemeData] | None = None

    def _load_themes(self) -> dict[str, ThemeData]:
        """Load theme definitions from the JSON file, with caching."""
        if self._themes is not None:
            return self._themes

        try:
            if not self.themes_file_path.exists():
                log.warning(f"Theme file not found: {self.themes_file_path}")
                self._themes = StyleMapper.DEFAULT_THEME.copy()

                return self._themes

            with self.themes_file_path.open(encoding="utf-8") as f:
                data = json.load(f)

            raw_themes = data.get("themes", data)
            all_themes = {
                key: value.get("colors", value) for key, value in raw_themes.items() if isinstance(value, dict)
            }

            if not all_themes:
                log.warning("No valid themes found in JSON, using default.")
                all_themes = StyleMapper.DEFAULT_THEME.copy()

            self._themes = all_themes

            return all_themes

        except json.JSONDecodeError as e:
            log.error(f"Error parsing theme JSON: {e}")
            self._themes = StyleMapper.DEFAULT_THEME.copy()

            return self._themes
        except Exception as e:
            log.opt(exception=True).error(f"Unexpected error loading themes: {e}")
            self._themes = StyleMapper.DEFAULT_THEME.copy()

            return self._themes

    def create_theme(self, theme_name: str) -> Theme:
        """Create a rich Theme object from a loaded theme name."""
        themes = self._load_themes()
        theme_data = themes.get(theme_name)

        if not theme_data:
            log.warning(f"Theme '{theme_name}' not found, using fallbacks.")
            fallback_styles = {name: Style.parse(style) for name, style in StyleMapper.STYLE_FALLBACKS.items()}

            return Theme(fallback_styles)

        styles = StyleMapper.create_styles_from_theme(theme_data)

        for style_name, fallback in StyleMapper.STYLE_FALLBACKS.items():
            if style_name not in styles:
                try:
                    styles[style_name] = Style.parse(fallback)
                except Exception as e:
                    log.error(f"Error creating fallback style '{style_name}': {e}")
                    styles[style_name] = Style()

        return Theme(styles)

    def create_console(self, theme_name: str = "rose_pine") -> Console:
        """Create a new rich Console with the specified theme."""
        ensure_true_color()

        theme = self.create_theme(theme_name)

        console = Console(
            theme=theme,
            color_system="auto",
            highlight=True,
            markup=True,
            emoji=True,
            force_terminal=True,
            soft_wrap=True,
        )

        return console

    def switch_theme(self, console: Console, theme_name: str) -> bool:
        """Switches the theme of an existing Console instance."""
        try:
            new_theme = self.create_theme(theme_name)
            console.push_theme(new_theme)

            return True
        except Exception as e:
            log.opt(exception=True).error(f"Error switching theme: {e}")

            return False

    def get_available_themes(self) -> list[str]:
        """Returns a list of all available theme names."""
        themes = self._load_themes()

        return list(themes.keys())
