from dataclasses import dataclass

from .base import BaseColorPalette


@dataclass
class MonokaiColorPalette(BaseColorPalette):
    name: str = "monokai"

    background: str = "#272822"
    current_line: str = "#3e3d32"
    selection: str = "#414339"
    foreground: str = "#f8f8f2"
    comment: str = "#88846f"
