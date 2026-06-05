"""Format-agnostic document metadata."""

from __future__ import annotations

from dataclasses import dataclass, field


def _empty_raw_metadata() -> dict[str, str]:
    return {}


@dataclass(frozen=True, slots=True)
class Metadata:
    """Script-level metadata used across the processing pipeline."""

    res_x: int
    res_y: int
    video_x_correct_factor: float = 1.0
    raw: dict[str, str] = field(default_factory=_empty_raw_metadata)
