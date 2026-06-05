"""String helper utilities."""

from __future__ import annotations

from collections.abc import Iterator


def trim(value: str) -> str:
    """Strip leading and trailing whitespace from ``value``."""
    return value.strip()


def headtail(value: str) -> tuple[str, str]:
    """Split one whitespace-separated string into head and remaining tail."""
    parts = value.split(None, 1)
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[1]


def words(value: str) -> Iterator[str]:
    """Yield whitespace-separated words from ``value`` one by one."""
    remaining = value
    while True:
        head, tail = headtail(remaining)
        if head == "":
            return
        yield head
        remaining = tail
