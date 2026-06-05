"""Karaoke domain models."""

from __future__ import annotations

from dataclasses import dataclass

from pykara.data.styles import Style


@dataclass(frozen=True, slots=True)
class Highlight:
    """One highlight span inside a syllable."""

    start_time: int
    end_time: int
    duration: int


@dataclass(slots=True)
class Syllable:
    """One karaoke syllable enriched during parsing and preprocessing."""

    index: int
    raw_text: str
    text: str
    trimmed_text: str
    prespace: str
    postspace: str
    start_time: int
    end_time: int
    duration: int
    kdur: float
    tag: str
    inline_fx: str
    highlights: list[Highlight]
    style: Style | None = None
    width: float = 0.0
    height: float = 0.0
    prespacewidth: float = 0.0
    postspacewidth: float = 0.0
    left: float = 0.0
    center: float = 0.0
    right: float = 0.0
    top: float = 0.0
    middle: float = 0.0
    bottom: float = 0.0
    x: float = 0.0
    y: float = 0.0


@dataclass(slots=True)
class Word:
    """One word grouped from positioned karaoke syllables."""

    index: int
    syllables: tuple[Syllable, ...]
    raw_text: str
    text: str
    trimmed_text: str
    prespace: str
    postspace: str
    start_time: int
    end_time: int
    duration: int
    kdur: float
    style: Style | None = None
    width: float = 0.0
    height: float = 0.0
    prespacewidth: float = 0.0
    postspacewidth: float = 0.0
    left: float = 0.0
    center: float = 0.0
    right: float = 0.0
    top: float = 0.0
    middle: float = 0.0
    bottom: float = 0.0
    x: float = 0.0
    y: float = 0.0
