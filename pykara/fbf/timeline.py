"""Timeline utilities for converting between frames and milliseconds."""

from __future__ import annotations

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
