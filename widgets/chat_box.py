from rich.console import RenderableType
from textual.app import ComposeResult
from textual.widgets import RichLog
from textual.containers import Vertical


class ChatBox(Vertical):
    def compose(self):
        yield RichLog(highlight=True, markup=True, wrap=True, id="main")