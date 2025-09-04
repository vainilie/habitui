from __future__ import annotations

from typing import Any
from collections.abc import Generator

from textual.widgets import Static, ProgressBar
from textual.reactive import reactive
from textual.containers import Horizontal


class SimpleProgressWidget(Horizontal):
    """Widget simple para mostrar progreso de la cola."""

    current = reactive(0)
    total = reactive(0)
    is_working = reactive(False)
    status = reactive("")

    def compose(self) -> Generator[ProgressBar | Static, Any]:
        yield ProgressBar(total=100, id="progress")
        yield Static( id="status")

    def show_progress(self, current: int, total: int, status: str = "") -> None:
        self.current = current
        self.total = total
        self.status = status
        self.is_working = True

        progress_bar = self.query_one("#progress", ProgressBar)
        progress_bar.total = total
        progress_bar.progress = current

        status_text = self.query_one("#status", Static)
        if status:
            status_text.update(f"{status} ({current}/{total})")
        else:
            status_text.update(f"Procesando... {current}/{total}")

    def hide_progress(self) -> None:
        self.is_working = False
        progress_bar = self.query_one("#progress", ProgressBar)
        progress_bar.total = 0
        progress_bar.progress = 0

        status_text = self.query_one("#status", Static)
        status_text.update()
