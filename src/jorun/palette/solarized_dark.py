from dataclasses import dataclass

from .base import BaseColorPalette


@dataclass
class SolarizedDarkColorPalette(BaseColorPalette):
    name: str = "solarized-dark"

    background: str = "#002B36"
    current_line: str = "#274642"
    selection: str = "#274642"
    foreground: str = "#839496"
    comment: str = "#586E75"
