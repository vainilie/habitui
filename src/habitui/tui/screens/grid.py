from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import Label, Button
from textual.containers import ItemGrid, Container


class GridApp(App):
    def compose(self) -> ComposeResult:
        with Container(), ItemGrid(min_column_width=80):
            yield Button("Botón 1")
            yield Button("Botón 2")
            yield Button("Botón 3")
            yield Button("Botón 4")
            yield Label("Etiqueta 1")
            yield Label("Etiqueta 2")


GridApp().run()
