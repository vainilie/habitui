# ─── Markdown to Rich Text Converter ──────────────────────────────────────────
"""Provides utilities for converting Markdown to Rich Text objects.

Uses markdown-it-py for parsing and Rich for constructing styled text.
Includes default styling and allows for custom style overrides.
Optionally integrates with Textual via a MarkdownStatic widget.
"""

# ──────────────────────────────────────────────────────────────────────────────
# ─── Imports ───
# ──────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import re
from typing import Any
from collections.abc import Sequence


# Markdown parsing (markdown-it-py)
try:
    import markdown_it
    from markdown_it.token import Token as MarkdownToken  # Alias for clarity

    MARKDOWN_IT_AVAILABLE = True
except ImportError:
    MARKDOWN_IT_AVAILABLE = False

    # Define a dummy type if markdown-it-py is not available
    class MarkdownToken:  # type: ignore[no-redef]
        pass


# Rich library components
from rich.text import Text, TextType  # Text objects
from rich.panel import Panel
from rich.style import Style  # Style objects
from rich.console import Console  # Console components


# Textual integration (optional)
try:
    from textual.widgets import Static
    from textual.reactive import reactive

    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False

    # Define dummy classes if Textual is not available, for type hinting primarily
    class Static:  # type: ignore[no-redef]
        """Dummy Static class for type hinting when Textual is not available."""

    def reactive(default: Any, layout: bool = False) -> Any:  # type: ignore[no-redef]
        """Dummy reactive function for type hinting when Textual is not available."""
        return default


# Attempt to use a themed console if available from a central Rich setup module
try:
    from pyxabit.handlers.rich_handler import console as _themed_console

    # Basic check to ensure the imported object is a Rich Console instance
    if not isinstance(_themed_console, Console):
        raise ImportError(
            "Themed console from .handlers.rich_handler is not a Rich Console instance.",
        )
    _console: Console = _themed_console
except ImportError:
    # Fallback to a basic Rich Console if the themed one can't be imported
    _console = Console()


# ──────────────────────────────────────────────────────────────────────────────
# ─── Utility Functions ───
# ──────────────────────────────────────────────────────────────────────────────
def escape_rich_text_markup(text: str) -> str:
    """Escapes Rich text markup control characters (square brackets) in a string.

    This is useful when displaying literal text that might contain Rich's markup
    syntax, preventing it from being interpreted as styling.

    :param text: The input string.
    :return: The string with Rich markup characters ('[' and ']') escaped.
             Returns an empty string if the input is None or empty.
    """
    if not text:
        return ""
    # Replace '[' with '\[', and ']' with '\]'
    return text.replace("[", r"\[").replace("]", r"\]")


# ──────────────────────────────────────────────────────────────────────────────
# ─── Markdown Renderer Class ───
# ──────────────────────────────────────────────────────────────────────────────
class MarkdownToRichRenderer:
    """Converts Markdown strings to Rich Text objects using markdown-it-py.

    This class parses Markdown into tokens and then renders these tokens into
    Rich `Text` objects with customizable styling.

    :ivar DEFAULT_STYLES: A class variable dictionary holding default Rich
                          `Style` objects for various Markdown elements.
    :ivar md_parser: The `markdown_it.MarkdownIt` parser instance.
    :ivar styles: The effective styles used for rendering.
    """

    DEFAULT_STYLES: dict[str, Style] = {
        "h1": Style(bold=True, color="cyan", underline=True),
        "h2": Style(bold=True, color="bright_cyan"),
        "h3": Style(bold=True, color="blue"),
        "h4": Style(underline=True, color="bright_blue"),
        "h5": Style(italic=True, color="blue"),
        "h6": Style(italic=True, dim=True),
        "strong": Style(bold=True),
        "em": Style(italic=True),
        "code_inline": Style(
            bgcolor="grey19",
            color="bright_green",
        ),
        "code_block": Style(
            dim=True,
            bgcolor="grey11",
        ),
        "strike": Style(strike=True),
        "link": Style(underline=True, color="bright_blue", bold=True),
        "list_item": Style(),
        "blockquote": Style(italic=True, color="green"),
        "hr": Style(color="bright_black", dim=True),
        "checkbox_unchecked": Style(color="yellow"),
        "checkbox_checked": Style(dim=True, color="green"),
    }

    # ──────────────────────────────────────────────────────────────────────────────
    def __init__(self, custom_styles: dict[str, Style] | None = None) -> None:
        """Initializes the MarkdownToRichRenderer.

        :param custom_styles: An optional dictionary mapping Markdown element names
                              (e.g., 'h1', 'link') to Rich `Style` objects.
        :raises ImportError: If `markdown-it-py` is not installed.
        """
        if not MARKDOWN_IT_AVAILABLE:
            raise ImportError(
                "MarkdownToRichRenderer requires 'markdown-it-py' to be installed."
                " Please install it via pip: pip install markdown-it-py",
            )
        self.md_parser = markdown_it.MarkdownIt(
            "commonmark",
            {"breaks": True, "html": False},
        ).enable("strikethrough")
        self.styles = self.DEFAULT_STYLES.copy()
        if custom_styles:
            self.styles.update(custom_styles)

    # ──────────────────────────────────────────────────────────────────────────────
    # ─── Style Application Helpers (Internal) ───
    def _apply_style(self, current_style_base: Style, style_key_to_add: str) -> Style:
        """Applies a named style on top of a base style.

        :param current_style_base: The base `Style` object.
        :param style_key_to_add: The key (e.g., "strong", "h1") of the style to add.
        :return: A new `Style` object representing the combination.
        """
        additional_style = self.styles.get(style_key_to_add)
        if additional_style:
            return current_style_base + additional_style
        return current_style_base

    # ──────────────────────────────────────────────────────────────────────────────
    # ─── Core Conversion Method ───
    def convert(self, markdown_string: str) -> Text:
        """Converts a Markdown string to a Rich `Text` object.

        :param markdown_string: The Markdown-formatted string to convert.
        :return: A Rich `Text` object representing the styled content.
        """
        if not markdown_string:
            return Text()
        tokens = self.md_parser.parse(markdown_string)
        output_text = Text()
        self._process_tokens_recursive(tokens, output_text, style_stack=[Style()])
        return output_text.rstrip()

    # ──────────────────────────────────────────────────────────────────────────────
    # ─── Token Processing Logic (Internal) ───
    def _process_tokens_recursive(
        self,
        tokens: Sequence[MarkdownToken],
        text_obj_to_append_to: Text,
        style_stack: list[Style],
    ) -> None:
        """Recursively processes markdown-it tokens and appends styled content.

        :param tokens: A sequence of `MarkdownToken` objects.
        :param text_obj_to_append_to: The Rich `Text` object being built.
        :param style_stack: A list representing the stack of active styles.
        """
        i = 0
        while i < len(tokens):
            token = tokens[i]
            current_effective_style = style_stack[-1]

            if token.type == "inline" and token.children:
                self._process_tokens_recursive(
                    token.children,
                    text_obj_to_append_to,
                    style_stack,
                )
                i += 1
                continue

            if token.type.endswith("_open"):
                new_style_for_tag = current_effective_style
                style_key_for_tag = ""
                prefix_for_block = ""
                ensure_newline_before = False

                if token.type == "heading_open":
                    level = int(token.tag[1])
                    style_key_for_tag = f"h{level}"
                    ensure_newline_before = True
                elif token.type == "strong_open":
                    style_key_for_tag = "strong"
                elif token.type == "em_open":
                    style_key_for_tag = "em"
                elif token.type == "s_open":
                    style_key_for_tag = "strike"
                elif token.type == "link_open":
                    style_key_for_tag = "link"
                    href = token.attrs.get("href", "") if token.attrs else ""
                    new_style_with_link = self._apply_style(
                        current_effective_style,
                        style_key_for_tag,
                    )
                    if href:
                        new_style_with_link = new_style_with_link.update_link(href)
                    style_stack.append(new_style_with_link)
                    i += 1
                    continue
                elif token.type == "blockquote_open":
                    style_key_for_tag = "blockquote"
                    prefix_for_block = "> "
                    ensure_newline_before = True
                elif token.type in ("bullet_list_open", "ordered_list_open"):
                    style_key_for_tag = "list_item"
                    ensure_newline_before = True
                elif token.type == "list_item_open":
                    style_key_for_tag = "list_item"

                if style_key_for_tag:
                    new_style_for_tag = self._apply_style(
                        current_effective_style,
                        style_key_for_tag,
                    )
                if (
                    ensure_newline_before
                    and text_obj_to_append_to
                    and not text_obj_to_append_to.plain.endswith("\n")
                ):
                    text_obj_to_append_to.append("\n")
                if prefix_for_block:
                    text_obj_to_append_to.append(prefix_for_block, new_style_for_tag)
                style_stack.append(new_style_for_tag)
            elif token.type.endswith("_close"):
                if len(style_stack) > 1:
                    style_stack.pop()
                if (
                    token.type
                    in {
                        "paragraph_close",
                        "blockquote_close",
                        "heading_close",
                        "bullet_list_close",
                        "ordered_list_close",
                        "list_item_close",
                    }
                    and text_obj_to_append_to
                    and not text_obj_to_append_to.plain.endswith(
                        "\n\n",
                    )
                ):
                    if text_obj_to_append_to.plain.endswith("\n"):
                        text_obj_to_append_to.append("\n")
                    else:
                        text_obj_to_append_to.append("\n\n")
            elif token.type == "text":
                content_text = token.content
                text_style_to_apply = current_effective_style
                is_in_list_item = (
                    i > 0 and tokens[i - 1].type == "list_item_open"
                ) or (
                    len(style_stack) > 1
                    and style_stack[-2] == self.styles.get("list_item")
                )
                if is_in_list_item and not text_obj_to_append_to.plain.endswith(
                    ("\n", " ", "• ", "☐ ", "☑ "),
                ):
                    item_prefix = "• "
                    stripped_content = content_text.lstrip()
                    if stripped_content.startswith(("[ ] ", "[ ]")):
                        item_prefix = "☐ "
                        content_text = stripped_content[len("[ ] ") :].lstrip()
                        text_style_to_apply = self._apply_style(
                            text_style_to_apply,
                            "checkbox_unchecked",
                        )
                    elif re.match(r"\[[xX]\]\s", stripped_content, re.IGNORECASE):
                        item_prefix = "☑ "
                        content_text = re.sub(
                            r"\[[xX]\]\s*",
                            "",
                            stripped_content,
                            count=1,
                            flags=re.IGNORECASE,
                        )
                        text_style_to_apply = self._apply_style(
                            text_style_to_apply,
                            "checkbox_checked",
                        )
                    text_obj_to_append_to.append(
                        item_prefix,
                        self.styles.get("list_item", Style()),
                    )
                text_obj_to_append_to.append(
                    escape_rich_text_markup(content_text),
                    text_style_to_apply,
                )
            elif token.type == "code_inline":
                text_obj_to_append_to.append(
                    token.content,
                    self.styles.get("code_inline", Style()),
                )
            elif token.type in ("code_block", "fence"):
                if text_obj_to_append_to and not text_obj_to_append_to.plain.endswith(
                    "\n",
                ):
                    text_obj_to_append_to.append("\n")

                text_obj_to_append_to.append(
                    token.content.rstrip("\n"),
                    self.styles.get("code_block"),
                )
                text_obj_to_append_to.append("\n")
            elif token.type == "softbreak":
                if self.md_parser.options.get("breaks"):
                    text_obj_to_append_to.append("\n")
                else:
                    text_obj_to_append_to.append(" ")
            elif token.type == "hardbreak":
                text_obj_to_append_to.append("\n")
            elif token.type == "hr":
                if text_obj_to_append_to and not text_obj_to_append_to.plain.endswith(
                    "\n",
                ):
                    text_obj_to_append_to.append("\n")
                hr_char = "─"
                rule_width = _console.width if _console else 80
                text_obj_to_append_to.append(
                    hr_char * rule_width,
                    self.styles.get("hr", Style()),
                )
                text_obj_to_append_to.append("\n\n")
            i += 1

    # ──────────────────────────────────────────────────────────────────────────────
    # ─── Convenience Rendering Methods ───
    def render_to_console(
        self,
        markdown_string: str,
        target_console: Console | None = None,
    ) -> None:
        """Renders the Markdown string directly to a Rich console.

        :param markdown_string: The Markdown-formatted string.
        :param target_console: Optional Rich `Console` instance to print to.
        """
        console_to_use = target_console or _console
        rich_text_output = self.convert(markdown_string)
        console_to_use.print(rich_text_output)

    # ──────────────────────────────────────────────────────────────────────────────
    def render_to_panel(
        self,
        markdown_string: str,
        title: str | TextType | None = None,
        **panel_kwargs: Any,
    ) -> Panel:
        """Renders the Markdown string inside a Rich `Panel`.

        :param markdown_string: The Markdown-formatted string.
        :param title: Optional title for the panel. Can be a string or Rich Text.
        :param panel_kwargs: Additional keyword arguments to pass to the `Panel` constructor.
        :return: A Rich `Panel` object containing the rendered Markdown content.
        """
        rich_text_output = self.convert(markdown_string)
        return Panel(rich_text_output, title=title, **panel_kwargs)


# ──────────────────────────────────────────────────────────────────────────────
# ─── Textual Integration (Optional) ───
# ──────────────────────────────────────────────────────────────────────────────
if TEXTUAL_AVAILABLE and MARKDOWN_IT_AVAILABLE:

    class MarkdownStaticWidget(Static):
        """A Textual `Static` widget that renders Markdown content.

        This widget uses the `MarkdownToRichRenderer` to convert Markdown strings
        into Rich `Text` objects, which are then displayed by the `Static` widget.
        The Markdown content can be updated dynamically via the `markdown_content`
        reactive property.
        """

        markdown_content = reactive("", layout=True)

        # ──────────────────────────────────────────────────────────────────────────────
        def __init__(
            self,
            initial_markdown: str = "",
            renderer_instance: MarkdownToRichRenderer | None = None,
            *args: Any,
            **kwargs: Any,
        ):
            """Initializes the MarkdownStaticWidget.

            :param initial_markdown: The initial Markdown string to render.
            :param renderer_instance: An optional custom `MarkdownToRichRenderer` instance.
            :param args: Positional arguments for the base `Static` widget.
            :param kwargs: Keyword arguments for the base `Static` widget.
            """
            super().__init__("", *args, **kwargs)
            self._md_renderer = renderer_instance or MarkdownToRichRenderer()
            self.markdown_content = initial_markdown

        # ──────────────────────────────────────────────────────────────────────────────
        def watch_markdown_content(self, new_markdown_string: str) -> None:
            """Called automatically when the `markdown_content` reactive property changes.

            This method re-renders the Markdown and updates the widget's display.

            :param new_markdown_string: The new Markdown string to render.
            """
            if not hasattr(self, "_md_renderer"):
                self._md_renderer = MarkdownToRichRenderer()
            rich_text_output = self._md_renderer.convert(new_markdown_string)
            self.update(rich_text_output)

        # ──────────────────────────────────────────────────────────────────────────────
        def set_markdown(self, new_markdown_string: str) -> None:
            """Programmatically updates the widget with new Markdown content.

            This is an alternative to setting the `markdown_content` reactive property
            directly.

            :param new_markdown_string: The new Markdown string.
            """
            self.markdown_content = new_markdown_string


# ──────────────────────────────────────────────────────────────────────────────
# ─── Exports ───
# ──────────────────────────────────────────────────────────────────────────────
__all__ = [
    "MarkdownToRichRenderer",
    "escape_rich_text_markup",
]
if TEXTUAL_AVAILABLE and MARKDOWN_IT_AVAILABLE:
    __all__.append("MarkdownStaticWidget")
