"""Timecodes file parsing for frame-by-frame expansion."""

from __future__ import annotations

from pathlib import Path

from pykara.errors import PykaraError
from pykara.fbf.timeline import TimecodeFrameRate

_INVALID_TIMECODES_PREFIX = (
    "timecodes file must use v2 format with one frame timestamp per line"
)


def read_timecodes(path: Path) -> TimecodeFrameRate:
    """Read an Aegisub-style v2 timecodes file."""
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as error:
        message = f"could not read timecodes file '{path}'"
        raise PykaraError(message) from error

    frame_starts: list[int] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            frame_starts.append(round(float(line)))
        except ValueError as error:
            message = (
                f"{_INVALID_TIMECODES_PREFIX}; invalid value on line "
                f"{line_number}"
            )
            raise PykaraError(message) from error

    return TimecodeFrameRate(tuple(frame_starts))
