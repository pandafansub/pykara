"""SSA/ASS output adapter."""

from __future__ import annotations

import math
from pathlib import Path

from pykara.adapters import SubtitleDocument
from pykara.data import Event, Style
from pykara.errors import DocumentWriteError

_STYLE_FORMAT = (
    "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
    "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
    "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
    "Alignment, MarginL, MarginR, MarginV, Encoding"
)
_EVENT_FORMAT = (
    "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, "
    "Effect, Text"
)


class SubStationAlphaWriter:
    """Write normalized subtitle documents as ASS/SSA files."""

    def write(self, document: SubtitleDocument, path: str | Path) -> None:
        """Serialize a subtitle document to disk.

        Args:
            document: Normalized subtitle document to serialize.
            path: Destination ASS or SSA file path.

        Raises:
            DocumentWriteError: If the subtitle file cannot be written.
        """

        path_obj = Path(path)
        payload = self._serialize(document)
        try:
            path_obj.write_text(payload, encoding="utf-8")
        except Exception as error:
            raise DocumentWriteError(path_obj, message=str(error)) from error

    def _serialize(self, document: SubtitleDocument) -> str:
        lines: list[str] = ["[Script Info]"]
        info = dict(document.metadata.raw)
        info["PlayResX"] = str(document.metadata.res_x)
        info["PlayResY"] = str(document.metadata.res_y)
        lines.extend(f"{key}: {value}" for key, value in info.items())

        lines.extend(("", "[V4+ Styles]", _STYLE_FORMAT))
        lines.extend(
            f"Style: {self._serialize_style(style)}"
            for style in document.styles.values()
        )

        lines.extend(("", "[Events]", _EVENT_FORMAT))
        lines.extend(self._serialize_event(event) for event in document.events)
        return "\n".join(lines) + "\n"

    def _serialize_style(self, style: Style) -> str:
        return ",".join(
            [
                style.name,
                style.fontname,
                _format_decimal(style.fontsize),
                _normalize_style_color(style.primary_colour),
                _normalize_style_color(style.secondary_colour),
                _normalize_style_color(style.outline_colour),
                _normalize_style_color(style.back_colour),
                _format_bool(style.bold),
                _format_bool(style.italic),
                _format_bool(style.underline),
                _format_bool(style.strike_out),
                _format_decimal(style.scale_x),
                _format_decimal(style.scale_y),
                _format_decimal(style.spacing),
                _format_decimal(style.angle),
                str(style.border_style),
                _format_decimal(style.outline),
                _format_decimal(style.shadow),
                str(style.alignment),
                str(style.margin_l),
                str(style.margin_r),
                str(style.margin_t),
                str(style.encoding),
            ]
        )

    def _serialize_event(self, event: Event) -> str:
        prefix = "Comment" if event.comment else "Dialogue"
        return ",".join(
            [
                prefix + f": {event.layer}",
                _format_timestamp(event.start_time),
                _format_timestamp(event.end_time),
                event.style,
                event.actor,
                str(event.margin_l),
                str(event.margin_r),
                str(event.margin_t),
                event.effect,
                event.text,
            ]
        )


def _format_bool(value: bool) -> str:
    return "-1" if value else "0"


def _normalize_style_color(value: str) -> str:
    normalized = value.strip().upper()
    if not normalized.startswith("&H"):
        normalized = "&H" + normalized.removeprefix("&")
    return normalized.removesuffix("&")


def _format_decimal(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return f"{value:.6f}".rstrip("0").rstrip(".")


def _format_timestamp(milliseconds: int) -> str:
    total_centiseconds = math.floor(max(0, milliseconds) / 10 + 0.5)
    hours, remainder = divmod(total_centiseconds, 360000)
    minutes, remainder = divmod(remainder, 6000)
    seconds, centiseconds = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{seconds:02d}.{centiseconds:02d}"
