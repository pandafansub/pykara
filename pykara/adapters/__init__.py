"""Public adapter protocols and shared document container."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from pykara.data import Event, Metadata, Style


@dataclass(frozen=True, slots=True)
class SubtitleDocument:
    """Format-agnostic subtitle document passed through the pipeline."""

    metadata: Metadata
    styles: dict[str, Style]
    events: list[Event]


class SubtitleReader(Protocol):
    """Read subtitle files into the normalized document model."""

    def read(self, path: str | Path) -> SubtitleDocument:
        """Load one subtitle document.

        Args:
            path: Subtitle file path.

        Returns:
            Loaded normalized subtitle document.
        """
        ...


class SubtitleWriter(Protocol):
    """Write normalized documents to a concrete subtitle format."""

    def write(self, document: SubtitleDocument, path: str | Path) -> None:
        """Persist one normalized subtitle document.

        Args:
            document: Normalized subtitle document to serialize.
            path: Destination file path.
        """
        ...


__all__ = ["SubtitleDocument", "SubtitleReader", "SubtitleWriter"]
