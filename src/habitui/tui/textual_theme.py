# ♥♥─── Textual Theme Bridge ─────────────────────────────────────
"""Bridge between JSON theme system and Textual themes."""

import json
from pathlib import Path

from textual.theme import Theme as TextualTheme

from habitui.custom_logger import log
from habitui.ui.theme_manager import StyleMapper

ThemeData = dict[str, str]

DEFAULT_THEMES_JSON_PATH = Path(__file__).parent / "themes.json"


class TextualThemeBridge:
    """Converts JSON themes to Textual Theme objects."""

    def __init__(self, themes_file_path: Path | None = None):
        """Initialize the bridge with theme loader."""
        self._textual_themes_cache: dict[str, TextualTheme] = {}
        self.themes_file_path = themes_file_path or DEFAULT_THEMES_JSON_PATH
        self.style_mapper = StyleMapper()

    def _load_themes(self) -> dict[str, ThemeData]:
        """Load theme definitions from the JSON file, with caching."""
        if self._themes is not None:
            return self._themes

        try:
            if not self.themes_file_path.exists():
                log.warning(f"Theme file not found: {self.themes_file_path}")
                self._themes = self.style_mapper.DEFAULT_THEME.copy()

                return self._themes

            with self.themes_file_path.open(encoding="utf-8") as f:
                data = json.load(f)

            raw_themes = data.get("themes", data)
            all_themes = {
                key: value.get("colors", value) for key, value in raw_themes.items() if isinstance(value, dict)
            }

            if not all_themes:
                log.warning("No valid themes found in JSON, using default.")
                all_themes = self.style_mapper.DEFAULT_THEME.copy()

            self._themes = all_themes

            return all_themes

        except json.JSONDecodeError as e:
            log.error(f"Error parsing theme JSON: {e}")
            self._themes = self.style_mapper.DEFAULT_THEME.copy()

            return self._themes
        except Exception as e:
            log.opt(exception=True).error(f"Unexpected error loading themes: {e}")
            self._themes = self.style_mapper.DEFAULT_THEME.copy()

            return self._themes

    def json_to_textual_theme(self, theme_name: str) -> TextualTheme | None:
        """Convert a JSON theme to a Textual Theme object."""
        themes = self._load_themes()
        theme_data = themes.get(theme_name)

        if not theme_data:
            log.warning(f"Theme '{theme_name}' not found, using fallbacks.")
            return None

        # Map colors
        colors = self.style_mapper.map_json_to_textual_colors(theme_data=theme_data)
        variables = self.style_mapper.create_textual_variables(theme_data)

        # Create Textual theme
        textual_theme = TextualTheme(
            name=theme_data.get("name", theme_name),
            dark=True,
            text_alpha=100,
            luminosity_spread=0.9,
            # Most terminal themes are dark
            **colors,
            variables=variables,
        )

        # Cache the theme
        self._textual_themes_cache[theme_name] = textual_theme
        log.info(f"Created Textual theme for '{theme_name}'")

        return textual_theme

    def get_available_themes(self) -> list[str]:
        """Returns a list of all available theme names."""
        themes = self._load_themes()

        return list(themes.keys())

    def get_all_textual_themes(self) -> dict[str, TextualTheme]:
        """Get all available themes as Textual Theme objects."""
        themes = {}
        available_theme_names = self.get_available_themes()

        for theme_name in available_theme_names:
            textual_theme = self.json_to_textual_theme(theme_name)
            if textual_theme:
                themes[theme_name] = textual_theme

        return themes


# ─── Enhanced Theme Manager for Textual ─────────────────────────────────────
class TextualThemeManager:
    """Enhanced theme manager that works with both JSON and Textual systems."""

    def __init__(self, app, themes_file_path: Path | None = None):
        """Initialize with Textual app reference."""
        self.app = app
        self.bridge = TextualThemeBridge(themes_file_path)
        self._setup_default_themes()
        self.current_theme = "Rose Pine"

    def _setup_default_themes(self) -> None:
        """Setup default themes including rose_pine fallback."""
        rose_pine_theme = self.bridge.json_to_textual_theme("rose_pine")
        if rose_pine_theme:
            self.app.register_theme(rose_pine_theme)
        # Register other available themes
        textual_themes = self.bridge.get_all_textual_themes()
        for theme_name, theme in textual_themes.items():
            if theme_name != "rose_pine":  # Already registered
                self.app.register_theme(theme)

        log.info(f"Registered {len(textual_themes)} themes from JSON")

    def switch_theme(self, theme_name: str):
        """Switch to a specific theme."""
        try:
            # Switch to the theme
            self.theme = theme_name
            log.info(f"Switched to theme: {theme_name}")

        except Exception as e:
            log.error(f"Error switching theme to '{theme_name}': {e}")
