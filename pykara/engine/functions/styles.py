"""Style lookup helpers exposed to the execution namespace."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Protocol, cast

from pykara.data import Style
from pykara.errors import UnknownStyleLookupError


class _StylesEnvironment(Protocol):
    styles: dict[str, Style]


@dataclass(frozen=True, slots=True)
class StyleInfo:
    """Public style information returned by ``get_style``."""

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

    @classmethod
    def from_style(cls, style: Style) -> StyleInfo:
        """Build public style information from one parsed ASS style."""
        return cls(
            name=style.name,
            fontname=style.fontname,
            fontsize=style.fontsize,
            primary_colour=style.primary_colour,
            secondary_colour=style.secondary_colour,
            outline_colour=style.outline_colour,
            back_colour=style.back_colour,
            bold=style.bold,
            italic=style.italic,
            underline=style.underline,
            strike_out=style.strike_out,
            scale_x=style.scale_x,
            scale_y=style.scale_y,
            spacing=style.spacing,
            angle=style.angle,
            border_style=style.border_style,
            outline=style.outline,
            shadow=style.shadow,
            alignment=style.alignment,
            margin_l=style.margin_l,
            margin_r=style.margin_r,
            margin_t=style.margin_t,
            margin_b=style.margin_b,
            encoding=style.encoding,
        )

    @property
    def primary_color(self) -> str:
        return self.primary_colour

    @property
    def secondary_color(self) -> str:
        return self.secondary_colour

    @property
    def outline_color(self) -> str:
        return self.outline_colour

    @property
    def shadow_color(self) -> str:
        return self.back_colour

    @property
    def margin_v(self) -> int:
        return self.margin_t


class GetStyleFunction:
    """Return public information for one named style."""

    name: ClassVar[str] = "get_style"
    aliases: ClassVar[tuple[str, ...]] = ()
    applicable_to: ClassVar[frozenset[str]] = frozenset({"template", "code"})

    def __call__(self, env: object, style_name: str) -> StyleInfo:
        typed_env = cast(_StylesEnvironment, env)
        style = typed_env.styles.get(style_name)
        if style is None:
            raise UnknownStyleLookupError(style_name)
        return StyleInfo.from_style(style)
