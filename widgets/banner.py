from rich.text import Text
from rich.panel import Panel
from rich.align import Align
from rich.console import RenderableType

from textual.widget import Widget


class Banner(Widget):
    text = Text("Loading...", style="bold blue")

    def set_text(self, text: str):
        self.text = Text(text, style="bold blue")
        self.refresh()

    def render(self) -> RenderableType:
        return Panel(Align.center(self.text))