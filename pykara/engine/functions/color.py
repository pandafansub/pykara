"""Color helper functions exposed to the execution namespace."""

from __future__ import annotations

import math
from typing import ClassVar

from pykara.support.interpolate import clamp, interpolate_color


def _clamp_byte(value: int) -> int:
    return int(clamp(value, 0, 255))


class AssColorFunction:
    """Return an ASS override color string in ``&HBBGGRR&`` format."""

    name: ClassVar[str] = "color.rgb_to_ass"
    aliases: ClassVar[tuple[str, ...]] = ()
    applicable_to: ClassVar[frozenset[str]] = frozenset({"template", "code"})

    def __call__(
        self,
        env: object,
        red: int,
        green: int,
        blue: int,
    ) -> str:
        del env
        red_component = _clamp_byte(red)
        green_component = _clamp_byte(green)
        blue_component = _clamp_byte(blue)
        return (
            f"&H{blue_component:02X}{green_component:02X}{red_component:02X}&"
        )


class AssAlphaFunction:
    """Return an ASS alpha string in ``&HAA&`` format."""

    name: ClassVar[str] = "color.alpha"
    aliases: ClassVar[tuple[str, ...]] = ()
    applicable_to: ClassVar[frozenset[str]] = frozenset({"template", "code"})

    def __call__(self, env: object, alpha: int) -> str:
        del env
        alpha_component = _clamp_byte(alpha)
        return f"&H{alpha_component:02X}&"


class InterpolateColorFunction:
    """Return a color string interpolated between two ASS colors."""

    name: ClassVar[str] = "color.interpolate"
    aliases: ClassVar[tuple[str, ...]] = ()
    applicable_to: ClassVar[frozenset[str]] = frozenset({"template", "code"})

    def __call__(
        self,
        env: object,
        progress: float,
        start_color: str,
        end_color: str,
    ) -> str:
        del env
        return interpolate_color(progress, start_color, end_color)


class HsvToRgbFunction:
    """Convert HSV components to RGB components."""

    name: ClassVar[str] = "color.hsv_to_rgb"
    aliases: ClassVar[tuple[str, ...]] = ("color.HSV_to_RGB",)
    applicable_to: ClassVar[frozenset[str]] = frozenset({"template", "code"})

    def __call__(
        self,
        env: object,
        hue: float,
        saturation: float,
        value: float,
    ) -> tuple[float, float, float]:
        del env
        if saturation == 0:
            component = clamp(value * 255, 0, 255)
            return component, component, component

        hue = math.fabs(hue) % 360
        hue_index = math.floor(hue / 60)
        fraction = hue / 60.0 - hue_index
        p = value * (1 - saturation)
        q = value * (1 - fraction * saturation)
        t = value * (1 - (1 - fraction) * saturation)

        if hue_index == 0:
            red, green, blue = value, t, p
        elif hue_index == 1:
            red, green, blue = q, value, p
        elif hue_index == 2:
            red, green, blue = p, value, t
        elif hue_index == 3:
            red, green, blue = p, q, value
        elif hue_index == 4:
            red, green, blue = t, p, value
        elif hue_index == 5:
            red, green, blue = value, p, q
        else:  # pragma: no cover - kept as a guard against math surprises.
            raise ValueError(
                f"math.floor(hue % 360 / 60) should be [0, 6), is {hue_index}"
            )
        return red * 255.0, green * 255.0, blue * 255.0


class HslToRgbFunction:
    """Convert HSL components to RGB byte components."""

    name: ClassVar[str] = "color.hsl_to_rgb"
    aliases: ClassVar[tuple[str, ...]] = ("color.HSL_to_RGB",)
    applicable_to: ClassVar[frozenset[str]] = frozenset({"template", "code"})

    def __call__(
        self,
        env: object,
        hue: float,
        saturation: float,
        luminance: float,
    ) -> tuple[int, int, int]:
        del env
        hue = math.fabs(hue) % 360
        saturation = clamp(saturation, 0, 1)
        luminance = clamp(luminance, 0, 1)

        if saturation == 0:
            red = green = blue = luminance
        else:
            if luminance < 0.5:
                q = luminance * (1.0 + saturation)
            else:
                q = luminance + saturation - luminance * saturation
            p = 2.0 * luminance - q
            hue_fraction = hue / 360

            if hue_fraction < 1 / 3:
                tr = hue_fraction + 1 / 3
                tg = hue_fraction
                tb = hue_fraction + 2 / 3
            elif hue_fraction > 2 / 3:
                tr = hue_fraction - 2 / 3
                tg = hue_fraction
                tb = hue_fraction - 1 / 3
            else:
                tr = hue_fraction + 1 / 3
                tg = hue_fraction
                tb = hue_fraction - 1 / 3

            red = _hsl_component(tr, p, q)
            green = _hsl_component(tg, p, q)
            blue = _hsl_component(tb, p, q)

        return (
            math.floor(red * 255 + 0.5),
            math.floor(green * 255 + 0.5),
            math.floor(blue * 255 + 0.5),
        )


def _hsl_component(component: float, p: float, q: float) -> float:
    if component < 1 / 6:
        return p + (q - p) * 6.0 * component
    if 1 / 6 <= component < 1 / 2:
        return q
    if 1 / 2 <= component < 2 / 3:
        return p + (q - p) * (2 / 3 - component) * 6.0
    return p
