from __future__ import annotations

from textual.app import App
from textual.widgets import Header


class MinimalApp(App):
    TITLE = "Minimal Title"
    SUB_TITLE = "Minimal Subtitle"

    def compose(self):
        yield Header(show_clock=True)


MinimalApp().run()
