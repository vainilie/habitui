# ♥♥─── Themed Icon Provider ───────────────────────────────────────────────────
from __future__ import annotations

from typing import Literal, ClassVar
from functools import lru_cache

from .icon_definitions import IconName


# ─── Icon Retriever ─────────────────────────────────────────────────────────────
@lru_cache(maxsize=256)
def get_icon(icon_name: str, shape: str | None = None, outline: bool = False, alt: bool = False) -> str:
    """Find the best-matching icon variant based on theme settings."""
    candidates = []
    suffix = "_O" if outline else ""
    if shape:
        base = f"{icon_name}_{shape.upper()}{suffix}"
        if alt:
            candidates.append(f"{base}_ALT")
        candidates.append(base)
    if alt:
        candidates.append(f"{icon_name}_ALT")
    if outline:
        candidates.append(f"{icon_name}_O")
    candidates.append(icon_name)
    for variant in candidates:
        if hasattr(IconName, variant):
            return getattr(IconName, variant).value
    return "●"


# ─── Auto-discovery Helper ──────────────────────────────────────────────────────
def _discover_base_icons() -> set[str]:
    """Automatically discover base icon names from the IconName enum."""
    base_icons = set()
    for icon_attr in dir(IconName):
        if icon_attr.startswith("_"):
            continue
        # Extract base name by removing suffixes
        base_name = icon_attr
        # Remove common suffixes to get the base name
        suffixes = ["_CIRCLE", "_SQUARE", "_O", "_ALT", "_CIRCLE_O", "_SQUARE_O", "_CIRCLE_ALT", "_SQUARE_ALT", "_CIRCLE_O_ALT", "_SQUARE_O_ALT"]
        for suffix in sorted(suffixes, key=len, reverse=True):  # Sort by length to check longer suffixes first
            if base_name.endswith(suffix):
                base_name = base_name[: -len(suffix)]
                break
        base_icons.add(base_name)
    return base_icons


# ─── Themed Icon Class ──────────────────────────────────────────────────────────
class ThemedIcons:
    """Provide themed icons with support for shapes, outlines, and alternates."""

    # Auto-discover available icons from the enum
    AVAILABLE_ICONS: ClassVar[set[str]] = _discover_base_icons()

    def __init__(self, shape: Literal["SIMPLE", "CIRCLE", "SQUARE"] = "SIMPLE", outline: bool = False, alt: bool = False) -> None:
        """Initialize the icon theme."""
        self.shape: Literal["SIMPLE", "CIRCLE", "SQUARE"] | None = shape if shape != "SIMPLE" else None
        self.outline = outline
        self.alt = alt

    def __getattr__(self, name: str) -> str:
        """Dynamically retrieve an icon by its base name."""
        if name in self.AVAILABLE_ICONS:
            return get_icon(name, self.shape, self.outline, self.alt)
        if hasattr(IconName, name):
            return getattr(IconName, name).value
        msg = f"Icon '{name}' not found. Available: {sorted(self.AVAILABLE_ICONS)}"
        raise AttributeError(msg)

    def get_specific(self, icon_name: str) -> str:
        """Get a specific icon variant by its full name."""
        if hasattr(IconName, icon_name):
            return getattr(IconName, icon_name).value
        msg = f"Icon variant '{icon_name}' not found"
        raise ValueError(msg)

    def with_theme(self, shape: Literal["SIMPLE", "CIRCLE", "SQUARE"] | None = None, outline: bool | None = None, alt: bool | None = None) -> ThemedIcons:
        """Create a new ThemedIcons instance with modified theme settings."""
        new_shape: Literal["SIMPLE", "CIRCLE", "SQUARE"] = shape if shape is not None else (self.shape or "SIMPLE")
        return ThemedIcons(shape=new_shape, outline=outline if outline is not None else self.outline, alt=alt if alt is not None else self.alt)

    def list_variants(self, base_name: str) -> list[str]:
        """List all available variants for a base icon name."""
        upper_base_name = base_name.upper()
        return [icon.name for icon in IconName if icon.name.startswith(upper_base_name)]

    def __dir__(self) -> list[str]:
        """Provide a list of available icons for autocompletion."""
        methods = ["get_specific", "with_theme", "list_variants"]
        return [*sorted(self.AVAILABLE_ICONS), *methods]


# ─── Pre-configured Themes ──────────────────────────────────────────────────────
class Icons:
    """Provide easy access to pre-configured icon themes."""

    simple = ThemedIcons(shape="SIMPLE", outline=False, alt=False)
    circle = ThemedIcons(shape="CIRCLE", outline=False, alt=False)
    circle_outline = ThemedIcons(shape="CIRCLE", outline=True, alt=False)
    square = ThemedIcons(shape="SQUARE", outline=False, alt=False)
    square_outline = ThemedIcons(shape="SQUARE", outline=True, alt=False)

    @classmethod
    def custom(cls, shape: Literal["SIMPLE", "CIRCLE", "SQUARE"] = "SIMPLE", outline: bool = False, alt: bool = False) -> ThemedIcons:
        """Create a ThemedIcons instance with a custom theme."""
        return ThemedIcons(shape, outline, alt)


# ─── Export for easy access ─────────────────────────────────────────────────────
icons = Icons.simple
