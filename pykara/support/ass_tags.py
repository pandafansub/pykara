"""Helpers for ASS override tag text."""

from __future__ import annotations

import re

_ADJACENT_OVERRIDE_BLOCK_PATTERN = re.compile(r"\{(\\[^{}]*)\}\{(\\[^{}]*)\}")


def merge_adjacent_override_blocks(text: str) -> str:
    """Merge adjacent ASS override blocks that contain override tags."""

    merged = text
    while True:
        updated = _ADJACENT_OVERRIDE_BLOCK_PATTERN.sub(r"{\1\2}", merged)
        if updated == merged:
            return merged
        merged = updated
