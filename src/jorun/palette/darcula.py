from dataclasses import dataclass

from .base import BaseColorPalette


@dataclass
class DarculaColorPalette(BaseColorPalette):
    name: str = "darcula"

    background: str = "#282a36"
    current_line: str = "#44475a"
    selection: str = "#44475a"
    foreground: str = "#f8f8f2"
    comment: str = "#6272a4"
