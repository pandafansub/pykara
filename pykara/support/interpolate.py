"""Numeric interpolation helpers used across the project."""

from __future__ import annotations

import math
import re

from pykara.errors import PykaraError

_STYLE_COLOR_PATTERN = re.compile(r"^&H([0-9A-Fa-f]{8})&?$")
_OVERRIDE_COLOR_PATTERN = re.compile(r"^&H([0-9A-Fa-f]{6})&$")
_ALPHA_PATTERN = re.compile(r"^&H([0-9A-Fa-f]{2})&$")
_HTML_PATTERN = re.compile(
    r"^#([0-9A-Fa-f]{2})([0-9A-Fa-f]{0,2})([0-9A-Fa-f]{0,2})([0-9A-Fa-f]{0,2})$"
)


def clamp[NumberT: (int, float)](
    value: NumberT,
    minimum: NumberT,
    maximum: NumberT,
) -> NumberT:
    """Clamp ``value`` to the inclusive ``[minimum, maximum]`` range."""
    if value < minimum:
        return minimum
    if value > maximum:
        return maximum
    return value


def interpolate(percentage: float, minimum: float, maximum: float) -> float:
    """Interpolate between ``minimum`` and ``maximum`` with saturation."""
    if percentage <= 0:
        return minimum
    if percentage >= 1:
        return maximum
    return percentage * (maximum - minimum) + minimum


def _extract_color_components(value: str) -> tuple[int, int, int, int]:
    normalized = value.strip()

    style_match = _STYLE_COLOR_PATTERN.fullmatch(normalized)
    if style_match is not None:
        payload = style_match.group(1)
        alpha = int(payload[0:2], 16)
        blue = int(payload[2:4], 16)
        green = int(payload[4:6], 16)
        red = int(payload[6:8], 16)
        return red, green, blue, alpha

    override_match = _OVERRIDE_COLOR_PATTERN.fullmatch(normalized)
    if override_match is not None:
        payload = override_match.group(1)
        blue = int(payload[0:2], 16)
        green = int(payload[2:4], 16)
        red = int(payload[4:6], 16)
        return red, green, blue, 0

    alpha_match = _ALPHA_PATTERN.fullmatch(normalized)
    if alpha_match is not None:
        return 0, 0, 0, int(alpha_match.group(1), 16)

    html_match = _HTML_PATTERN.fullmatch(normalized)
    if html_match is not None:
        red = int(html_match.group(1), 16)
        green = int(html_match.group(2) or "00", 16)
        blue = int(html_match.group(3) or "00", 16)
        alpha = int(html_match.group(4) or "00", 16)
        return red, green, blue, alpha

    raise PykaraError(f"Invalid color string: {value!r}")


def _round_byte(value: float) -> int:
    return int(clamp(math.floor(value + 0.5), 0, 255))


def interpolate_color(percentage: float, first: str, last: str) -> str:
    """Interpolate between two ASS-style colors and return override format."""
    r1, g1, b1, _a1 = _extract_color_components(first)
    r2, g2, b2, _a2 = _extract_color_components(last)
    red = _round_byte(interpolate(percentage, float(r1), float(r2)))
    green = _round_byte(interpolate(percentage, float(g1), float(g2)))
    blue = _round_byte(interpolate(percentage, float(b1), float(b2)))
    return f"&H{blue:02X}{green:02X}{red:02X}&"
