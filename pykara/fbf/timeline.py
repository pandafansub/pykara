"""Timeline utilities for converting between frames and milliseconds."""

from __future__ import annotations

import bisect
from dataclasses import dataclass
from typing import Protocol

from pykara.errors import PykaraError


class FrameTimeMapper(Protocol):
    """Mapping between absolute milliseconds and frame indexes."""

    def frame_at_time(self, milliseconds: int) -> int:
        """Return the frame active at ``milliseconds``."""
        ...

    def time_at_frame(self, frame_index: int) -> int:
        """Return the start time of ``frame_index``."""
        ...


FrameRateSource = FrameTimeMapper | float


@dataclass(frozen=True, slots=True)
class ConstantFrameRate:
    """Frame/time conversion for a constant FPS timeline."""

    fps: float

    def __post_init__(self) -> None:
        if self.fps <= 0:
            raise PykaraError("frame-baked timeline fps must be > 0")

    def frame_at_time(self, milliseconds: int) -> int:
        return int(milliseconds * self.fps / 1000.0)

    def time_at_frame(self, frame_index: int) -> int:
        if frame_index < 0:
            raise PykaraError(
                "frame-baked timeline frame index cannot be negative"
            )
        return int(frame_index * 1000.0 / self.fps)


@dataclass(frozen=True, slots=True)
class TimecodeFrameRate:
    """Frame/time conversion backed by v2 timecode frame starts."""

    frame_starts_ms: tuple[int, ...]

    def __post_init__(self) -> None:
        if len(self.frame_starts_ms) < 2:
            raise PykaraError(
                "timecodes file must contain at least two frame timestamps"
            )
        if self.frame_starts_ms[0] != 0:
            raise PykaraError("timecodes file must start at 0 ms")
        previous = self.frame_starts_ms[0]
        for current in self.frame_starts_ms[1:]:
            if current <= previous:
                raise PykaraError(
                    "timecodes file must contain increasing timestamps"
                )
            previous = current

    def frame_at_time(self, milliseconds: int) -> int:
        if milliseconds < 0:
            raise PykaraError("timecodes cannot resolve negative timestamps")
        if milliseconds >= self._last_known_frame_end():
            raise PykaraError(
                "timecodes file does not cover the full subtitle timing"
            )
        return bisect.bisect_right(self.frame_starts_ms, milliseconds) - 1

    def time_at_frame(self, frame_index: int) -> int:
        if frame_index < 0:
            raise PykaraError(
                "frame-baked timeline frame index cannot be negative"
            )
        if frame_index < len(self.frame_starts_ms):
            return self.frame_starts_ms[frame_index]
        if frame_index == len(self.frame_starts_ms):
            return self._last_known_frame_end()
        raise PykaraError(
            "timecodes file does not cover the full subtitle timing"
        )

    def _last_known_frame_end(self) -> int:
        last_duration = self.frame_starts_ms[-1] - self.frame_starts_ms[-2]
        return self.frame_starts_ms[-1] + last_duration


def coerce_framerate(framerate: FrameRateSource) -> FrameTimeMapper:
    """Accept either a mapper object or a raw constant FPS value."""
    if isinstance(framerate, int | float):
        return ConstantFrameRate(float(framerate))
    return framerate


def ms_from_frame(frame: int, framerate: FrameRateSource) -> int:
    """Convert one frame index to milliseconds."""
    return coerce_framerate(framerate).time_at_frame(frame)


def frame_from_ms(milliseconds: int, framerate: FrameRateSource) -> int:
    """Convert milliseconds to the active frame index."""
    return coerce_framerate(framerate).frame_at_time(milliseconds)
