from dataclasses import dataclass

from .base import BaseColorPalette


@dataclass
class HackerColorPalette(BaseColorPalette):
    name: str = "hacker"

    background: str = "#000000"
    current_line: str = "#202020"
    selection: str = "#333333"
    foreground: str = "#20c20e"
    comment: str = "#f0f0f0"
