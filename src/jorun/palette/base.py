from dataclasses import dataclass


@dataclass
class BaseColorPalette:
    background: str
    current_line: str
    selection: str
    foreground: str
    comment: str
