"""Format-agnostic subtitle style models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Style:
    """Normalized ASS style data used by the domain and engine layers."""

    name: str
    fontname: str
    fontsize: float
    primary_colour: str
    secondary_colour: str
    outline_colour: str
    back_colour: str
    bold: bool
    italic: bool
    underline: bool
    strike_out: bool
    scale_x: float
    scale_y: float
    spacing: float
    angle: float
    border_style: int
    outline: float
    shadow: float
    alignment: int
    margin_l: int
    margin_r: int
    margin_t: int
    margin_b: int
    encoding: int

    @property
    def margin_v(self) -> int:
        """Return the ASS vertical margin compatibility alias."""
        return self.margin_t
