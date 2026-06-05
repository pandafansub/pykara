"""Mixin declaration body models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MixinBody:
    """Pure data object that stores raw mixin text."""

    text: str
