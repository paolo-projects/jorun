from dataclasses import dataclass

from .base import BaseColorPalette


@dataclass
class KimbieDarkColorPalette(BaseColorPalette):
    name: str = "kimbie-dark"

    background: str = "#221a0f"
    current_line: str = "#84613daa"
    selection: str = "#7c502166"
    foreground: str = "#d3af86"
    comment: str = "#a57a4c"
