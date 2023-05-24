from dataclasses import dataclass

from jorun.palette.base import BaseColorPalette


@dataclass
class DarculaColorPalette(BaseColorPalette):
    background: str = "#282a36"
    current_line: str = "#44475a"
    selection: str = "#44475a"
    foreground: str = "#f8f8f2"
    comment: str = "#6272a4"