"""Geometry helpers for ASS drawing and motion expressions."""

from __future__ import annotations

import math
import random
import re
from collections.abc import Callable
from typing import ClassVar, Protocol

_COORDINATE_PATTERN = re.compile(r"(-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?)")


def _round_coord(value: float) -> int:
    return math.floor(value + 0.5)


def _format_number(value: float) -> str:
    rounded = _round_coord(value)
    if math.isclose(value, rounded, abs_tol=0.0001):
        return str(rounded)
    text = f"{value:.3f}".rstrip("0").rstrip(".")
    return "0" if text == "-0" else text


def _map_shape_points(
    shape: str,
    mapper: Callable[[float, float], tuple[float, float]],
) -> str:
    def replace(match: re.Match[str]) -> str:
        x = float(match.group(1))
        y = float(match.group(2))
        new_x, new_y = mapper(x, y)
        return f"{_format_number(new_x)} {_format_number(new_y)}"

    return _COORDINATE_PATTERN.sub(replace, shape)


def _shape_bounds(shape: str) -> tuple[float, float, float, float]:
    matches = tuple(_COORDINATE_PATTERN.finditer(shape))
    if not matches:
        return (0.0, 0.0, 0.0, 0.0)

    xs = tuple(float(match.group(1)) for match in matches)
    ys = tuple(float(match.group(2)) for match in matches)
    return min(xs), min(ys), max(xs), max(ys)


def _rotate_shape(
    shape: str,
    angle: float,
    origin_x: float = 0.0,
    origin_y: float = 0.0,
) -> str:
    radians = math.radians(angle)
    cos_angle = math.cos(radians)
    sin_angle = math.sin(radians)

    def rotate(x: float, y: float) -> tuple[float, float]:
        rel_x = x - origin_x
        rel_y = y - origin_y
        return (
            origin_x + rel_x * cos_angle + rel_y * sin_angle,
            origin_y - rel_x * sin_angle + rel_y * cos_angle,
        )

    return _map_shape_points(shape, rotate)


def _center_shape(shape: str, x: float = 0.0, y: float = 0.0) -> str:
    min_x, min_y, max_x, max_y = _shape_bounds(shape)
    offset_x = x - min_x - (max_x - min_x) / 2
    offset_y = y - min_y - (max_y - min_y) / 2
    return _map_shape_points(
        shape,
        lambda point_x, point_y: (point_x + offset_x, point_y + offset_y),
    )


def _circular_distance(first: int, second: int, count: int) -> int:
    distance = abs(first - second)
    return min(distance, count - distance)


def _point_distance(
    first: tuple[int, int],
    second: tuple[int, int],
) -> float:
    return math.hypot(first[0] - second[0], first[1] - second[1])


class _RandomEnvironment(Protocol):
    rng: random.Random


class PolarFunction:
    """Return screen-space polar coordinates."""

    name: ClassVar[str] = "coord.polar"
    aliases: ClassVar[tuple[str, ...]] = ()
    applicable_to: ClassVar[frozenset[str]] = frozenset({"template", "code"})

    def __call__(
        self,
        env: object,
        angle: float,
        radius: float,
        axis: str | None = None,
    ) -> float | tuple[float, float]:
        del env
        x = radius * math.cos(math.radians(angle))
        y = -radius * math.sin(math.radians(angle))
        if axis == "x":
            return round(x, 3)
        if axis == "y":
            return round(y, 3)
        return (round(x, 3), round(y, 3))


class CircularSpreadFunction:
    """Return unit-circle points in a spatially spread order."""

    name: ClassVar[str] = "coord.circular_spread"
    aliases: ClassVar[tuple[str, ...]] = ()
    applicable_to: ClassVar[frozenset[str]] = frozenset({"template", "code"})

    def __call__(
        self,
        env: _RandomEnvironment,
        n: int,
        rotate: int = 0,
    ) -> list[tuple[float, float]]:
        if n < 2:
            msg = "n must be >= 2"
            raise ValueError(msg)

        step = 2 * math.pi / n
        base_angle = math.pi / 2 + rotate * step
        points = tuple(
            (
                round(math.cos(base_angle - index * step), 4),
                round(math.sin(base_angle - index * step), 4),
            )
            for index in range(n)
        )

        result: list[tuple[float, float]] = []
        pool = list(range(n))
        current = pool.pop(0)
        result.append(points[current])

        while pool:
            adjacent = {(current + 1) % n, (current - 1) % n}
            candidates = [index for index in pool if index not in adjacent]
            if not candidates:
                candidates = pool[:]

            best_distance = max(
                _circular_distance(current, index, n) for index in candidates
            )
            best_candidates = [
                index
                for index in candidates
                if _circular_distance(current, index, n) == best_distance
            ]
            current = env.rng.choice(best_candidates)
            pool.remove(current)
            result.append(points[current])

        return result


class RandomSpreadFunction:
    """Return random points that are not too close to each other."""

    name: ClassVar[str] = "coord.random_spread"
    aliases: ClassVar[tuple[str, ...]] = ()
    applicable_to: ClassVar[frozenset[str]] = frozenset({"template", "code"})

    def __call__(
        self,
        env: _RandomEnvironment,
        n: int,
        spread: int = 30,
        min_dist: float = 14,
        min_radius: float = 8,
        attempts: int = 300,
    ) -> list[tuple[int, int]]:
        if n < 1:
            msg = "n must be >= 1"
            raise ValueError(msg)
        if spread < 0:
            msg = "spread must be >= 0"
            raise ValueError(msg)
        if min_dist < 0:
            msg = "min_dist must be >= 0"
            raise ValueError(msg)
        if min_radius < 0:
            msg = "min_radius must be >= 0"
            raise ValueError(msg)
        if attempts < 1:
            msg = "attempts must be >= 1"
            raise ValueError(msg)

        points: list[tuple[int, int]] = []
        for _ in range(attempts):
            if len(points) >= n:
                break

            point = (
                env.rng.randint(-spread, spread),
                env.rng.randint(-spread, spread),
            )
            if math.hypot(point[0], point[1]) < min_radius:
                continue
            if any(
                _point_distance(point, other) < min_dist for other in points
            ):
                continue
            points.append(point)

        if len(points) < n:
            msg = (
                "could not place enough points; increase spread or attempts, "
                "or lower min_dist/min_radius"
            )
            raise ValueError(msg)

        return points


class ShapeRotateFunction:
    """Rotate an ASS drawing shape around an origin."""

    name: ClassVar[str] = "shape.rotate"
    aliases: ClassVar[tuple[str, ...]] = ()
    applicable_to: ClassVar[frozenset[str]] = frozenset({"template", "code"})

    def __call__(
        self,
        env: object,
        shape: str,
        angle: float,
        origin_x: float = 0.0,
        origin_y: float = 0.0,
    ) -> str:
        del env
        return _rotate_shape(shape, angle, origin_x, origin_y)


class ShapeDisplaceFunction:
    """Displace every coordinate in an ASS drawing shape."""

    name: ClassVar[str] = "shape.displace"
    aliases: ClassVar[tuple[str, ...]] = ()
    applicable_to: ClassVar[frozenset[str]] = frozenset({"template", "code"})

    def __call__(
        self,
        env: object,
        shape: str,
        offset_x: float,
        offset_y: float,
    ) -> str:
        del env
        return _map_shape_points(
            shape,
            lambda point_x, point_y: (
                point_x + offset_x,
                point_y + offset_y,
            ),
        )


class ShapeCenterAtFunction:
    """Move a shape so its bounding-box center sits at ``x,y``."""

    name: ClassVar[str] = "shape.center_at"
    aliases: ClassVar[tuple[str, ...]] = ()
    applicable_to: ClassVar[frozenset[str]] = frozenset({"template", "code"})

    def __call__(
        self,
        env: object,
        shape: str,
        x: float = 0.0,
        y: float = 0.0,
    ) -> str:
        del env
        return _center_shape(shape, x, y)


class ShapeSplitClipFunction:
    """Build a rotated split clipping shape centered at ``x,y``."""

    name: ClassVar[str] = "shape.split_clip"
    aliases: ClassVar[tuple[str, ...]] = ()
    applicable_to: ClassVar[frozenset[str]] = frozenset({"template", "code"})

    def __call__(
        self,
        env: object,
        width: float,
        angle: float = 0.0,
        x: float = 0.0,
        y: float = 0.0,
        height: float | None = None,
    ) -> str:
        del env
        resolved_height = width if height is None else height
        shape = (
            f"m 0 {resolved_height / 2} "
            f"l {width} {resolved_height / 2} "
            f"l {width} 0 "
            "l 0 0 "
            f"m 0 {resolved_height} "
            f"l {width} {resolved_height}"
        )
        return _center_shape(_rotate_shape(shape, angle), x, y)
