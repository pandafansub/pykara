"""Style lookup helpers exposed to the execution namespace."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import ClassVar, Protocol, cast

from pykara.data import Style
from pykara.errors import UnknownStyleLookupError

_STYLE_COLOR_PATTERN = re.compile(r"&H([0-9A-Fa-f]{2})([0-9A-Fa-f]{6})&?")


class _StylesEnvironment(Protocol):
    styles: dict[str, Style]


def _style_color_to_override_color(style_color: str) -> str:
    match = _STYLE_COLOR_PATTERN.fullmatch(style_color)
    if match is None:
        return "&HFFFFFF&"
    return f"&H{match.group(2).upper()}&"


@dataclass(frozen=True, slots=True)
class StyleInfo:
    """Public style information returned by ``get_style``."""

    name: str
    font_name: str
    font_size: float
    primary_color: str
    secondary_color: str
    outline_color: str
    shadow_color: str
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
            font_name=style.fontname,
            font_size=style.fontsize,
            primary_color=_style_color_to_override_color(style.primary_colour),
            secondary_color=_style_color_to_override_color(
                style.secondary_colour
            ),
            outline_color=_style_color_to_override_color(style.outline_colour),
            shadow_color=_style_color_to_override_color(style.back_colour),
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
