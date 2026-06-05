"""Template declaration body models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TemplateBody:
    """Pure data object that stores raw template text."""

    text: str
