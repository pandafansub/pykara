"""Deterministic jitter helpers shared by motion backends."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from pykara.errors import EngineError


@dataclass(frozen=True, slots=True)
class JitterSpec:
    """Validated jitter parameters shared by multiple backends."""

    left: int
    right: int
    up: int
    down: int
    period: int
    seed: int


def validate_jitter_spec(
    left: object,
    right: object,
    up: object,
    down: object,
    period: object,
    seed: object,
    *,
    label: str,
) -> JitterSpec:
    """Return one validated jitter-parameter bundle."""
    values = (left, right, up, down, period, seed)
    if any(
        not isinstance(value, int) or isinstance(value, bool)
        for value in values
    ):
        raise EngineError(
            f"{label} expects integer left/right/up/down/period/seed values"
        )
    left_i, right_i, up_i, down_i, period_i, seed_i = cast(
        tuple[int, int, int, int, int, int],
        values,
    )
    if period_i < 0:
        raise EngineError(f"{label} period must be >= 0")
    return JitterSpec(left_i, right_i, up_i, down_i, period_i, seed_i)


def msvc_rand_pair(seed: int) -> tuple[int, int]:
    """Return the first two MSVC ``rand()`` values from ``srand(seed)``."""
    state = seed & 0xFFFFFFFF
    state = (state * 214013 + 2531011) & 0xFFFFFFFF
    first = (state >> 16) & 0x7FFF
    state = (state * 214013 + 2531011) & 0xFFFFFFFF
    second = (state >> 16) & 0x7FFF
    return first, second


def truncating_division(dividend: int, divisor: int) -> int:
    """Match C++ integer division semantics for negative values."""
    quotient = abs(dividend) // abs(divisor)
    return -quotient if (dividend < 0) ^ (divisor < 0) else quotient


def jitter_bucket(milliseconds: int, period_ms: int) -> int:
    """Return the deterministic jitter bucket for one timestamp."""
    return truncating_division(milliseconds, period_ms)


def jitter_offsets(
    bucket: int,
    left: int,
    right: int,
    up: int,
    down: int,
    seed: int,
) -> tuple[int, int]:
    """Return one deterministic jitter offset using the legacy formula."""
    random_x, random_y = msvc_rand_pair((seed + bucket) * 100)
    x_amplitude = left + right
    y_amplitude = up + down
    x_offset = (random_x % x_amplitude) - left if x_amplitude else 0
    y_offset = (random_y % y_amplitude) - up if y_amplitude else 0
    return x_offset, y_offset


def jitter_offsets_at(
    milliseconds: int,
    period_ms: int,
    left: int,
    right: int,
    up: int,
    down: int,
    seed: int,
) -> tuple[int, int]:
    """Return the deterministic jitter offsets active at ``milliseconds``."""
    return jitter_offsets(
        jitter_bucket(milliseconds, period_ms),
        left,
        right,
        up,
        down,
        seed,
    )


def iter_jitter_offsets(
    duration_ms: int,
    period_ms: int,
    left: int,
    right: int,
    up: int,
    down: int,
    seed: int,
) -> list[tuple[int, int, int]]:
    """Return ``(time, x, y)`` tuples for each active jitter period."""
    resolved_period = period_ms or 1
    offsets: list[tuple[int, int, int]] = []
    current_ms = 0
    while current_ms < duration_ms:
        x_offset, y_offset = jitter_offsets_at(
            current_ms,
            resolved_period,
            left,
            right,
            up,
            down,
            seed,
        )
        offsets.append((current_ms, x_offset, y_offset))
        current_ms += resolved_period
    return offsets
