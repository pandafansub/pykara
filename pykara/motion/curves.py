"""Pure curve helpers shared by motion backends."""

from __future__ import annotations

import math
from collections.abc import Callable

from pykara.errors import EngineError

RawSegment = tuple[float, float, float, float, float, float]


def lerp(t: float, start: float, end: float) -> float:
    """Return the linear interpolation between ``start`` and ``end``."""
    return start + t * (end - start)


def sample_curve(
    curve_fn: Callable[[float], tuple[float, float]],
    n_segments: int,
    window_start: float,
    window_end: float,
) -> list[RawSegment]:
    """Sample one curve into timed linear segments."""
    result: list[RawSegment] = []
    for index in range(n_segments):
        start_t = index / n_segments
        end_t = (index + 1) / n_segments
        start_ms = window_start + start_t * (window_end - window_start)
        end_ms = window_start + end_t * (window_end - window_start)
        x0, y0 = curve_fn(start_t)
        x1, y1 = curve_fn(end_t)
        result.append((start_ms, end_ms, x0, y0, x1, y1))
    return result


def resolve_window(
    t1: float | None,
    t2: float | None,
    duration_ms: int,
) -> tuple[float, float]:
    """Resolve the active animation window from optional t1/t2 bounds."""
    if t1 is None or t2 is None:
        return 0.0, float(duration_ms)
    if t1 <= 0 and t2 <= 0:
        return 0.0, float(duration_ms)
    if t2 < t1:
        t1, t2 = t2, t1
    return float(t1), float(t2)


def progress(ms: float, window_start: float, window_end: float) -> float:
    """Return normalized progress in ``[0, 1]`` inside one time window."""
    if ms <= window_start:
        return 0.0
    if ms >= window_end:
        return 1.0
    return (ms - window_start) / (window_end - window_start)


def arc_xy(
    t: float,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    a1_rad: float,
    a2_rad: float,
    r1: float,
    r2: float,
) -> tuple[float, float]:
    """Return the arc position at normalized progress ``t``."""
    origin_x = lerp(t, x1, x2)
    origin_y = lerp(t, y1, y2)
    angle = lerp(t, a1_rad, a2_rad)
    radius = lerp(t, r1, r2)
    return (
        origin_x + math.cos(angle) * radius,
        origin_y - math.sin(angle) * radius,
    )


def bezier_xy(
    t: float,
    points: tuple[tuple[float, float], ...],
) -> tuple[float, float]:
    """Return the quadratic or cubic Bezier position at progress ``t``."""
    if len(points) == 3:
        (x1, y1), (x2, y2), (x3, y3) = points
        mt = 1 - t
        return (
            mt * mt * x1 + 2 * t * mt * x2 + t * t * x3,
            mt * mt * y1 + 2 * t * mt * y2 + t * t * y3,
        )
    if len(points) == 4:
        (x1, y1), (x2, y2), (x3, y3), (x4, y4) = points
        mt = 1 - t
        return (
            mt**3 * x1 + 3 * t * mt**2 * x2 + 3 * t**2 * mt * x3 + t**3 * x4,
            mt**3 * y1 + 3 * t * mt**2 * y2 + 3 * t**2 * mt * y3 + t**3 * y4,
        )
    raise EngineError(
        f"motion.bezier() requires 3 or 4 control points, got {len(points)}"
    )


def spring_xy(
    t: float,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    amplitude: float = 1.0,
    damping: float = 3.0,
    freq: float = 6.0,
) -> tuple[float, float]:
    """Return the spring position at normalized progress ``t``."""
    dx = x0 - x1
    dy = y0 - y1
    envelope = math.exp(-damping * t * 4) * amplitude
    oscillation = math.cos(freq * math.pi * 2 * t)
    return x1 + dx * envelope * oscillation, y1 + dy * envelope * oscillation


def wave_xy(
    t: float,
    x0: float,
    x1: float,
    y_base: float,
    amplitude: float = 150.0,
    frequency: float = 2.0,
    phase_rad: float = 0.0,
) -> tuple[float, float]:
    """Return the sinusoidal wave position at normalized progress ``t``."""
    x = lerp(t, x0, x1)
    y = y_base + amplitude * math.sin(frequency * 2 * math.pi * t + phase_rad)
    return x, y
