# ♥♥─── Textual Dashboard Components ──────────────────────────────────────────
from __future__ import annotations

from typing import Any
from dataclasses import dataclass

from textual.app import ComposeResult
from textual.widgets import Label, Collapsible, ProgressBar
from textual.containers import Vertical, VerticalGroup, VerticalScroll, HorizontalGroup

from pyxabit.console import Markdown, icons


# ─── Data Models ─────────────────────────────────────────────────────────────
@dataclass
class RowData:
	"""Data for a horizontal row with an icon, label, progress bar, and value."""

	value: int | float | str | None = None
	icon: str | None = None
	show_progress_bar: bool = False
	css_classes: str | None = None
	element_id: str | None = None
	total_value: int | float | None = None
	label_text: str | None = None
	show_progress_text: bool = False

	def __post_init__(self) -> None:
		"""Post-initialization to cast float values to int and set icons."""
		if isinstance(self.value, float):
			self.value = int(self.value)

		if isinstance(self.total_value, float):
			self.total_value = int(self.total_value)

		if self.icon:
			self.icon = getattr(icons, self.icon, icons.SMALL_CIRCLE)


@dataclass
class PanelRowData:
	"""Data for a row containing multiple panels arranged horizontally."""

	panels: list[PanelData]
	css_classes: str | None = None
	element_id: str | None = None


@dataclass
class PanelData:
	"""Data for an information panel with a title, subtitle, and rows."""

	rows_data: list[Any]

	title_icon: str | None = None
	title: str | None = None
	subtitle_icon: str | None = None
	subtitle: str | None = None
	element_id: str | None = None
	css_classes: str | None = None

	def __post_init__(self) -> None:
		"""Post-initialization to set icons for title and subtitle."""
		if self.title_icon:
			self.title_icon = getattr(icons, self.title_icon, icons.BEE)

		if self.subtitle_icon:
			self.subtitle_icon = getattr(icons, self.subtitle_icon, icons.BEE)


@dataclass
class MarkdownData:
	"""Data for a markdown component with title, subtitle, and text content."""

	text: str | None = None
	title_icon: str | None = None
	title: str | None = None
	subtitle_icon: str | None = None
	subtitle: str | None = None
	css_classes: str | None = None
	element_id: str | None = None

	def __post_init__(self) -> None:
		"""Post-initialization to set icons."""
		if self.title_icon:
			self.title_icon = getattr(icons, self.title_icon, icons.BEE)

		if self.subtitle_icon:
			self.subtitle_icon = getattr(icons, self.subtitle_icon, icons.BEE)


@dataclass
class MarkdownPanelData:
	"""Data for building a markdown panel with multiple markdown sections."""

	markdown_sections: list[MarkdownData]
	title_icon: str | None = None
	title: str | None = None
	subtitle_icon: str | None = None
	subtitle: str | None = None
	element_id: str | None = None
	css_classes: str | None = None
	collapsible: bool = False
	scrollable: bool = False

	def __post_init__(self) -> None:
		"""Post-initialization to set icons for title and subtitle."""
		if self.title_icon:
			self.title_icon = getattr(icons, self.title_icon, icons.BEE)

		if self.subtitle_icon:
			self.subtitle_icon = getattr(icons, self.subtitle_icon, icons.BEE)


# ─── Textual Widgets ──────────────────────────────────────────────────────────
class HorizontalRow(HorizontalGroup):
	"""A horizontal visual row constructed from RowData."""

	def __init__(self, row_data: RowData) -> None:
		"""Initializes the HorizontalRow with row data."""
		self.row_data = row_data

		super().__init__()

	def compose(self) -> ComposeResult:
		"""Composes the child widgets for the horizontal row."""
		parts = []

		if self.row_data.icon:
			parts.append("icon")

		if self.row_data.label_text:
			parts.append("label")

		if self.row_data.show_progress_bar:
			parts.append("bar")

		if self.row_data.value is not None:
			parts.append("value")

		base_class = "-".join(parts) + "-row" if parts else "empty-row"
		extra_classes = f" {self.row_data.css_classes}" if self.row_data.css_classes else ""
		combined_classes = base_class + extra_classes

		with HorizontalGroup(
			id=self.row_data.element_id,
			classes=combined_classes,
		):
			if self.row_data.icon:
				yield Label(
					self.row_data.icon,
					classes="icon",
					id=f"{self.row_data.element_id}-icon" if self.row_data.element_id else None,
				)

			if self.row_data.label_text:
				yield Label(
					str(self.row_data.label_text),
					classes="label",
					id=f"{self.row_data.element_id}-label" if self.row_data.element_id else None,
				)

			if self.row_data.value is not None and not self.row_data.show_progress_bar:
				yield Label(
					str(self.row_data.value),
					classes="value",
					id=f"{self.row_data.element_id}-value" if self.row_data.element_id else None,
				)

			if (
				self.row_data.show_progress_bar
				and isinstance(self.row_data.value, int)
				and isinstance(self.row_data.total_value, int)
				and self.row_data.total_value > 0
			):
				progress_bar = ProgressBar(
					id=f"{self.row_data.element_id}-bar" if self.row_data.element_id else None,
					total=self.row_data.total_value,
					show_eta=False,
					classes="bar",
				)
				progress_bar.progress = self.row_data.value

				yield progress_bar

				if self.row_data.show_progress_text:
					progress_text = f"{self.row_data.value}/{self.row_data.total_value}"

					yield Label(
						progress_text,
						classes="progress",
						id=f"{self.row_data.element_id}-progress" if self.row_data.element_id else None,
					)


class PanelRow(HorizontalGroup):
	"""A horizontal row containing multiple panels."""

	def __init__(self, panel_row_data: PanelRowData) -> None:
		"""Initializes the PanelRow with panel row data."""
		self.panel_row_data = panel_row_data

		classes = "panel-row"
		if panel_row_data.css_classes:
			classes += f" {panel_row_data.css_classes}"

		super().__init__(id=panel_row_data.element_id, classes=classes)

	def compose(self) -> ComposeResult:
		"""Composes the child panels for the horizontal row."""
		for panel_data in self.panel_row_data.panels:
			yield Panel(panel_data)


class Panel(VerticalGroup):
	"""A vertical panel with a border, title, subtitle, and internal rows."""

	def __init__(self, panel_data: PanelData) -> None:
		"""Initializes the Panel with panel data."""
		self.panel_data = panel_data

		super().__init__(id=panel_data.element_id, classes=self._build_classes())

	def _build_classes(self) -> str:
		"""Builds the CSS classes for the panel."""
		base_class = "dashboard-panel"
		extra = f" {self.panel_data.css_classes}" if self.panel_data.css_classes else ""

		return base_class + extra

	def compose(self) -> ComposeResult:
		"""Composes the child widgets for the panel."""
		if self.panel_data.title_icon and self.panel_data.title:
			self.border_title = f"{self.panel_data.title_icon} {self.panel_data.title}"

		elif self.panel_data.title:
			self.border_title = self.panel_data.title

		if self.panel_data.subtitle_icon and self.panel_data.subtitle:
			self.border_subtitle = f"{self.panel_data.subtitle_icon} {self.panel_data.subtitle}"

		elif self.panel_data.subtitle:
			self.border_subtitle = self.panel_data.subtitle

		for row_item in self.panel_data.rows_data:
			if isinstance(row_item, RowData):
				yield HorizontalRow(row_item)

			elif isinstance(row_item, PanelData):
				yield Panel(row_item)

			elif isinstance(row_item, PanelRowData):
				yield PanelRow(row_item)


class MarkdownWidget(Vertical):
	"""A widget for displaying markdown content with optional title and subtitle."""

	def __init__(self, markdown_data: MarkdownData) -> None:
		"""Initializes the MarkdownWidget with markdown data."""
		self.markdown_data = markdown_data
		super().__init__(id=markdown_data.element_id, classes=self._build_classes())

	def _build_classes(self) -> str:
		return " ".join(filter(None, ["markdown-widget", self.markdown_data.css_classes]))

	def compose(self) -> ComposeResult:
		if self.markdown_data.title_icon and self.markdown_data.title:
			self.border_title = f"{self.markdown_data.title_icon} {self.markdown_data.title}"
		elif self.markdown_data.title:
			self.border_title = self.markdown_data.title

		if self.markdown_data.subtitle_icon and self.markdown_data.subtitle:
			self.border_subtitle = f"{self.markdown_data.subtitle_icon} {self.markdown_data.subtitle}"
		elif self.markdown_data.subtitle:
			self.border_subtitle = self.markdown_data.subtitle

		if self.markdown_data.text:
			yield Label(Markdown(self.markdown_data.text))


class MarkdownPanel(Vertical):
	"""A panel containing multiple markdown widgets with dynamic container type."""

	def __init__(self, panel_data: MarkdownPanelData) -> None:
		"""Initializes the VerticalMarkdownPanel with panel data."""
		self.panel_data = panel_data
		super().__init__(id=panel_data.element_id, classes=self._build_classes())

	def _build_classes(self) -> str:
		return " ".join(filter(None, ["markdown-panel", self.panel_data.css_classes]))

	def compose(self) -> ComposeResult:
		if self.panel_data.collapsible:
			container = Collapsible()
		elif self.panel_data.scrollable:
			container = VerticalScroll()
		else:
			container = Vertical()

		if self.panel_data.title_icon and self.panel_data.title:
			container.border_title = f"{self.panel_data.title_icon} {self.panel_data.title}"
		elif self.panel_data.title:
			container.border_title = self.panel_data.title

		if self.panel_data.subtitle_icon and self.panel_data.subtitle:
			container.border_subtitle = f"{self.panel_data.subtitle_icon} {self.panel_data.subtitle}"
		elif self.panel_data.subtitle:
			container.border_subtitle = self.panel_data.subtitle

		# Agregar los widgets internos
		with container:
			for markdown_data in self.panel_data.markdown_sections:
				yield MarkdownWidget(markdown_data)

		yield container
