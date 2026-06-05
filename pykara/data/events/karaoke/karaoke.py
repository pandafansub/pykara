"""Karaoke data aggregates."""

from __future__ import annotations

from dataclasses import dataclass

from pykara.data.events.karaoke.syllable import Syllable


@dataclass(slots=True)
class Karaoke:
    """Parsed karaoke payload for one event."""

    syllables: list[Syllable]
    text: str
    trimmed_text: str
