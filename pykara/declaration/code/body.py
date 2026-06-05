"""Code declaration body models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CodeBody:
    """Pure data object that stores raw code source."""

    source: str
