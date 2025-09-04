# ♥♥─── Textual Dashboard Components ──────────────────────────────────────────
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from rich.markdown import Markdown

from textual.widgets import Label, Collapsible, ProgressBar
from textual.containers import Vertical, VerticalGroup, VerticalScroll, HorizontalGroup

from habitui.ui import icons


if TYPE_CHECKING:
    from textual.app import ComposeResult


def get_icon(icon_name: str | None) -> str:
    if not icon_name:
        return ""
    return getattr(icons, icon_name, icons.SMALL_CIRCLE)


def build_border_title(icon: str | None = None, title: str | None = None) -> str | None:
    if not title:
        return None
    icon_str = get_icon(icon)
    return f"{icon_str} {title}" if icon_str else title


class HorizontalRow(HorizontalGroup):
    def __init__(self, *, value: Any = None, icon: str | None = None, label: str | None = None, progress_total: float | None = None, show_progress_text: bool = False, css_classes: str | None = None, element_id: str | None = None, **kwargs) -> None:
        if isinstance(value, float):
            value = int(value)
        if isinstance(progress_total, float):
            progress_total = int(progress_total)
        self.value = value
        self.icon = get_icon(icon)
        self.label = label
        self.progress_total = progress_total
        self.show_progress_text = show_progress_text
        parts = []
        if self.icon:
            parts.append("icon")
        if self.label:
            parts.append("label")
        if self.progress_total:
            parts.append("bar")
        if self.value is not None:
            parts.append("value")
        base_class = "-".join(parts) + "-row" if parts else "empty-row"
        classes = f"{base_class} {css_classes}" if css_classes else base_class
        super().__init__(id=element_id, classes=classes, **kwargs)

    def compose(self) -> ComposeResult:
        if self.icon:
            yield Label(self.icon, classes="icon")
        if self.label:
            yield Label(str(self.label), classes="label")
        if self.progress_total and isinstance(self.value, (int, float)) and self.progress_total > 0:
            progress_bar = ProgressBar(total=self.progress_total, show_eta=False, classes="bar")
            progress_bar.progress = self.value
            yield progress_bar
            if self.show_progress_text:
                yield Label(f"{self.value}/{self.progress_total}", classes="progress")
        elif self.value is not None and not self.progress_total:
            yield Label(str(self.value), classes="value")


class Panel(VerticalGroup):
    def __init__(self, *children, title: str | None = None, title_icon: str | None = None, subtitle: str | None = None, subtitle_icon: str | None = None, css_classes: str | None = None, element_id: str | None = None, **kwargs) -> None:
        self.children_widgets = children
        self.title_text = build_border_title(title_icon, title)
        self.subtitle_text = build_border_title(subtitle_icon, subtitle)
        classes = f"dashboard-panel {css_classes}" if css_classes else "dashboard-panel"
        super().__init__(id=element_id, classes=classes, **kwargs)

    def compose(self) -> ComposeResult:
        if self.title_text:
            self.border_title = self.title_text
        if self.subtitle_text:
            self.border_subtitle = self.subtitle_text
        yield from self.children_widgets


class MarkdownWidget(Vertical):
    def __init__(self, text: str, *, title: str | None = None, title_icon: str | None = None, subtitle: str | None = None, subtitle_icon: str | None = None, css_classes: str | None = None, element_id: str | None = None, **kwargs) -> None:
        self.text = text
        self.title_text = build_border_title(title_icon, title)
        self.subtitle_text = build_border_title(subtitle_icon, subtitle)
        classes = f"markdown-widget {css_classes}" if css_classes else "markdown-widget"
        super().__init__(id=element_id, classes=classes, **kwargs)

    def compose(self) -> ComposeResult:
        if self.title_text:
            self.border_title = self.title_text
        if self.subtitle_text:
            self.border_subtitle = self.subtitle_text
        if self.text:
            yield Label(Markdown(self.text))


class FlexibleContainer(Vertical):
    def __init__(self, *children, container_type: Literal["normal", "collapsible", "scrollable"] = "normal", title: str | None = None, title_icon: str | None = None, subtitle: str | None = None, subtitle_icon: str | None = None, css_classes: str | None = None, element_id: str | None = None, **kwargs) -> None:
        self.children_widgets = children
        self.container_type = container_type
        self.title_text = build_border_title(title_icon, title)
        self.subtitle_text = build_border_title(subtitle_icon, subtitle)
        classes = f"flexible-container {css_classes}" if css_classes else "flexible-container"
        super().__init__(id=element_id, classes=classes, **kwargs)

    def compose(self) -> ComposeResult:
        if self.container_type == "collapsible":
            container = Collapsible()
        elif self.container_type == "scrollable":
            container = VerticalScroll()
        else:
            container = Vertical()
        if self.title_text:
            container.border_title = self.title_text
        if self.subtitle_text:
            container.border_subtitle = self.subtitle_text
        with container:
            yield from self.children_widgets
        yield container


def create_dashboard_row(label: str | None = None, value: Any = None, icon: str | None = None, progress_total: int | None = None, **kwargs) -> HorizontalRow:
    return HorizontalRow(label=label, value=value, icon=icon, progress_total=progress_total, **kwargs)


def create_info_panel(*rows: HorizontalRow, title: str | None = None, title_icon: str | None = None, **kwargs) -> Panel:
    return Panel(*rows, title=title, title_icon=title_icon, **kwargs)


def create_markdown_section(text: str, title: str | None = None, title_icon: str | None = None, **kwargs) -> MarkdownWidget:
    return MarkdownWidget(text, title=title, title_icon=title_icon, **kwargs)


def example_usage() -> FlexibleContainer:
    health_row = create_dashboard_row(label="Health", value=85, icon="HEART", progress_total=100, show_progress_text=True)
    energy_row = create_dashboard_row(label="Energy", value="High", icon="LIGHTNING")
    stats_panel = create_info_panel(health_row, energy_row, title="Player Stats", title_icon="GAME_CONTROLLER")
    readme_section = create_markdown_section("# Welcome\nThis is your dashboard!", title="Documentation", title_icon="BOOK")
    return FlexibleContainer(stats_panel, readme_section, container_type="scrollable", title="Main Dashboard", title_icon="DASHBOARD")
