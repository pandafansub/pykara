"""Karaoke parser for ASS-style timing tags."""

from __future__ import annotations

import re
from dataclasses import dataclass

from pykara.data import Event, Highlight, Karaoke, Syllable

_OVERRIDE_BLOCK_PATTERN = re.compile(r"(\{[^}]*\})")
_KARAOKE_TAG_PATTERN = re.compile(r"\\(ko|kf|k|K)(\d+)")
_INLINE_FX_PATTERN = re.compile(r"\\-([^}\\]+)")
_STRIP_OVERRIDE_PATTERN = re.compile(r"\{[^}]*\}")
_SPACE_SPLIT_PATTERN = re.compile(r"^([ \t]*)(.*?)([ \t]*)$")
_MULTI_HIGHLIGHT_PREFIXES = ("#", "\uff03")
_MILLISECONDS_PER_CENTISECOND = 10


@dataclass(frozen=True, slots=True)
class _RawSyllable:
    """Intermediate parsed karaoke segment before highlight merging."""

    text: str
    tag: str
    duration: int


class KaraokeParser:
    """Parse karaoke timing tags from an event text payload."""

    def parse(self, event: Event) -> Karaoke:
        """Extract ASS karaoke syllables from one event.

        Args:
            event: Event containing ASS karaoke tags in ``text``.

        Returns:
            Parsed karaoke data in source order.
        """

        return self.parse_text(event.text)

    def parse_text(self, text: str) -> Karaoke:
        """Extract ASS karaoke syllables from raw text.

        Args:
            text: Raw event text containing ASS karaoke tags.

        Returns:
            Parsed karaoke data in source order.
        """

        raw_syllables = self._extract_raw_syllables(text)
        return self._build_karaoke(raw_syllables)

    def _extract_raw_syllables(self, text: str) -> list[_RawSyllable]:
        """Split text into raw syllables delimited by karaoke tags."""

        raw_syllables: list[_RawSyllable] = []
        current_tag = ""
        current_duration = 0
        current_parts: list[str] = []

        def append_current() -> None:
            if (
                not raw_syllables
                and current_tag == ""
                and current_duration == 0
                and not current_parts
            ):
                return
            raw_syllables.append(
                _RawSyllable(
                    text="".join(current_parts),
                    tag=current_tag,
                    duration=current_duration,
                )
            )

        for token in _OVERRIDE_BLOCK_PATTERN.split(text):
            if token == "":
                continue

            if not self._is_override_block(token):
                current_parts.append(token)
                continue

            karaoke_matches = list(_KARAOKE_TAG_PATTERN.finditer(token))
            if not karaoke_matches:
                current_parts.append(token)
                continue

            for _ in karaoke_matches:
                append_current()
                current_parts = []

            cleaned_block = _KARAOKE_TAG_PATTERN.sub("", token)
            if cleaned_block != "{}":
                current_parts.append(cleaned_block)

            last_match = karaoke_matches[-1]
            current_tag = last_match.group(0)
            current_duration = (
                int(last_match.group(2)) * _MILLISECONDS_PER_CENTISECOND
            )

        append_current()
        return raw_syllables

    def _build_karaoke(self, raw_syllables: list[_RawSyllable]) -> Karaoke:
        """Build domain karaoke data, merging multi-highlight segments."""

        syllables: list[Syllable] = []
        visible_text_parts: list[str] = []
        current_inline_fx = ""
        current_time = 0

        for raw_syllable in raw_syllables:
            visible_text = self._strip_override_tags(raw_syllable.text)
            prespace, trimmed_text, postspace = self._split_spaces(visible_text)

            inline_fx = self._find_inline_fx(raw_syllable.text)
            if inline_fx != "":
                current_inline_fx = inline_fx

            if syllables and self._is_multi_highlight(trimmed_text):
                previous = syllables[-1]
                highlight = Highlight(
                    start_time=current_time,
                    end_time=current_time + raw_syllable.duration,
                    duration=raw_syllable.duration,
                )
                previous.highlights.append(highlight)
                previous.duration += raw_syllable.duration
                previous.kdur += (
                    raw_syllable.duration / _MILLISECONDS_PER_CENTISECOND
                )
                previous.end_time += raw_syllable.duration
                current_time += raw_syllable.duration
                continue

            syllable = Syllable(
                index=len(syllables),
                raw_text=raw_syllable.text,
                text=visible_text,
                trimmed_text=trimmed_text,
                prespace=prespace,
                postspace=postspace,
                start_time=current_time,
                end_time=current_time + raw_syllable.duration,
                duration=raw_syllable.duration,
                kdur=raw_syllable.duration / _MILLISECONDS_PER_CENTISECOND,
                tag=raw_syllable.tag,
                inline_fx=current_inline_fx,
                highlights=self._build_highlights(
                    start_time=current_time,
                    duration=raw_syllable.duration,
                ),
            )
            syllables.append(syllable)
            visible_text_parts.append(visible_text)
            current_time += raw_syllable.duration

        visible_text = "".join(visible_text_parts)
        return Karaoke(
            syllables=syllables,
            text=visible_text,
            trimmed_text=visible_text.strip(),
        )

    def _build_highlights(
        self, *, start_time: int, duration: int
    ) -> list[Highlight]:
        """Create the default highlight list for one timed syllable."""

        if duration <= 0:
            return []

        return [
            Highlight(
                start_time=start_time,
                end_time=start_time + duration,
                duration=duration,
            )
        ]

    def _find_inline_fx(self, text: str) -> str:
        """Return the inline-fx marker found in a syllable text chunk."""

        match = _INLINE_FX_PATTERN.search(text)
        if match is None:
            return ""
        return match.group(1)

    def _strip_override_tags(self, text: str) -> str:
        """Remove ASS override blocks while preserving visible text."""

        return _STRIP_OVERRIDE_PATTERN.sub("", text)

    def _split_spaces(self, text: str) -> tuple[str, str, str]:
        """Split leading and trailing spaces from a syllable payload."""

        match = _SPACE_SPLIT_PATTERN.fullmatch(text)
        if match is None:
            return "", text, ""
        return match.group(1), match.group(2), match.group(3)

    def _is_multi_highlight(self, text: str) -> bool:
        """Detect whether a syllable extends the previous highlight group."""

        return text.startswith(_MULTI_HIGHLIGHT_PREFIXES)

    def _is_override_block(self, token: str) -> bool:
        """Return whether a token is an ASS override block."""

        return token.startswith("{") and token.endswith("}")
