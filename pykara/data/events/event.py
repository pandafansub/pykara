"""Core event models."""

from __future__ import annotations

from dataclasses import dataclass

from pykara.data.styles import Style


@dataclass(slots=True)
class Event:
    """Persistent event data independent from any subtitle adapter."""

    text: str
    effect: str
    style: str
    layer: int
    start_time: int
    end_time: int
    comment: bool
    actor: str
    margin_l: int
    margin_r: int
    margin_t: int
    margin_b: int


@dataclass(slots=True)
class RuntimeLine:
    """Execution-time view of one event with resolved style information."""

    event: Event
    styleref: Style
    duration: int
