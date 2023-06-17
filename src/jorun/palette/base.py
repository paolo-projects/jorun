from dataclasses import dataclass


@dataclass
class BaseColorPalette:
    name: str

    background: str
    current_line: str
    selection: str
    foreground: str
    comment: str
