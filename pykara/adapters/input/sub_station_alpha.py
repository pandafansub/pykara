"""SSA/ASS input adapter."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from pykara.adapters import SubtitleDocument
from pykara.data import Event, Metadata, Style
from pykara.errors import DocumentReadError

_DEFAULT_VIDEO_X_CORRECT_FACTOR = 1.0
_DUMMY_VIDEO_WIDTH_INDEX = 3
_DUMMY_VIDEO_HEIGHT_INDEX = 4
_STYLE_PREFIX = "Style:"
_EVENT_PREFIXES = {"Dialogue:": False, "Comment:": True}
_GENERATED_EFFECT = "fx"


class SubStationAlphaReader:
    """Read ASS/SSA documents into the format-agnostic domain model."""

    def read(
        self,
        path: str | Path,
        *,
        stop_at_generated_fx: bool = False,
    ) -> SubtitleDocument:
        """Load an ASS/SSA file from disk.

        Args:
            path: Path to the subtitle file.
            stop_at_generated_fx: Stop parsing event lines after the first
                event whose ``Effect`` is exactly ``fx``.

        Returns:
            Parsed subtitle document using domain-level data classes.

        Raises:
            DocumentReadError: If the file cannot be read or parsed.
        """

        path_obj = Path(path)
        try:
            text = path_obj.read_text(encoding="utf-8-sig")
            parsed = _AssParser(
                text,
                stop_at_generated_fx=stop_at_generated_fx,
            ).parse()
        except FileNotFoundError as error:
            raise DocumentReadError(path_obj, message=str(error)) from error
        except Exception as error:
            message = str(error)
            if not message:
                message = f"Could not parse subtitle document: {path_obj}"
            raise DocumentReadError(path_obj, message=message) from error

        return SubtitleDocument(
            metadata=self._to_metadata(
                info=parsed.script_info,
                project=parsed.project_garbage,
            ),
            styles={
                name: self._to_style(name=name, raw=raw_style)
                for name, raw_style in parsed.styles.items()
            },
            events=[self._to_event(raw_event) for raw_event in parsed.events],
        )

    def _to_metadata(
        self,
        info: Mapping[str, str],
        project: Mapping[str, str] | None = None,
    ) -> Metadata:
        res_x = self._parse_int(info.get("PlayResX"))
        res_y = self._parse_int(info.get("PlayResY"))
        raw = dict(info)
        if project is not None:
            raw.update(project)

        return Metadata(
            res_x=res_x,
            res_y=res_y,
            video_x_correct_factor=self._to_video_x_correct_factor(
                res_x=res_x,
                res_y=res_y,
                project=project,
            ),
            raw=raw,
        )

    def _to_style(self, name: str, raw: _RawStyle) -> Style:
        return Style(
            name=name,
            fontname=raw.fontname,
            fontsize=raw.fontsize,
            primary_colour=raw.primary_colour,
            secondary_colour=raw.secondary_colour,
            outline_colour=raw.outline_colour,
            back_colour=raw.back_colour,
            bold=raw.bold,
            italic=raw.italic,
            underline=raw.underline,
            strike_out=raw.strike_out,
            scale_x=raw.scale_x,
            scale_y=raw.scale_y,
            spacing=raw.spacing,
            angle=raw.angle,
            border_style=raw.border_style,
            outline=raw.outline,
            shadow=raw.shadow,
            alignment=raw.alignment,
            margin_l=raw.margin_l,
            margin_r=raw.margin_r,
            margin_t=raw.margin_v,
            margin_b=raw.margin_v,
            encoding=raw.encoding,
        )

    def _to_event(self, raw: _RawEvent) -> Event:
        return Event(
            text=raw.text,
            effect=raw.effect,
            style=raw.style,
            layer=raw.layer,
            start_time=raw.start_time,
            end_time=raw.end_time,
            comment=raw.comment,
            actor=raw.actor,
            margin_l=raw.margin_l,
            margin_r=raw.margin_r,
            margin_t=raw.margin_v,
            margin_b=raw.margin_v,
        )

    def _to_video_x_correct_factor(
        self,
        *,
        res_x: int,
        res_y: int,
        project: Mapping[str, str] | None,
    ) -> float:
        if project is None or res_x <= 0 or res_y <= 0:
            return _DEFAULT_VIDEO_X_CORRECT_FACTOR

        video_resolution = self._parse_dummy_video_resolution(project)
        if video_resolution is not None:
            video_x, video_y = video_resolution
            if video_x > 0 and video_y > 0:
                return (video_y / video_x) / (res_y / res_x)

        aspect_ratio = self._parse_float(project.get("Video AR Value"))
        if aspect_ratio is None or aspect_ratio <= 0:
            return _DEFAULT_VIDEO_X_CORRECT_FACTOR

        return (1.0 / aspect_ratio) / (res_y / res_x)

    def _parse_dummy_video_resolution(
        self, project: Mapping[str, str]
    ) -> tuple[int, int] | None:
        video_file = project.get("Video File")
        if video_file is None or not video_file.startswith("?dummy:"):
            return None

        tokens = video_file.split(":")
        if len(tokens) <= _DUMMY_VIDEO_HEIGHT_INDEX:
            return None

        width = self._parse_int(tokens[_DUMMY_VIDEO_WIDTH_INDEX])
        height = self._parse_int(tokens[_DUMMY_VIDEO_HEIGHT_INDEX])
        if width <= 0 or height <= 0:
            return None
        return width, height

    def _parse_int(self, value: str | None) -> int:
        if value is None:
            return 0
        try:
            return int(value)
        except ValueError:
            return 0

    def _parse_float(self, value: str | None) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except ValueError:
            return None


class _ParsedAss:
    def __init__(
        self,
        *,
        script_info: dict[str, str],
        project_garbage: dict[str, str],
        styles: dict[str, _RawStyle],
        events: list[_RawEvent],
    ) -> None:
        self.script_info = script_info
        self.project_garbage = project_garbage
        self.styles = styles
        self.events = events


class _RawStyle:
    def __init__(
        self,
        *,
        name: str,
        fontname: str,
        fontsize: float,
        primary_colour: str,
        secondary_colour: str,
        outline_colour: str,
        back_colour: str,
        bold: bool,
        italic: bool,
        underline: bool,
        strike_out: bool,
        scale_x: float,
        scale_y: float,
        spacing: float,
        angle: float,
        border_style: int,
        outline: float,
        shadow: float,
        alignment: int,
        margin_l: int,
        margin_r: int,
        margin_v: int,
        encoding: int,
    ) -> None:
        self.name = name
        self.fontname = fontname
        self.fontsize = fontsize
        self.primary_colour = primary_colour
        self.secondary_colour = secondary_colour
        self.outline_colour = outline_colour
        self.back_colour = back_colour
        self.bold = bold
        self.italic = italic
        self.underline = underline
        self.strike_out = strike_out
        self.scale_x = scale_x
        self.scale_y = scale_y
        self.spacing = spacing
        self.angle = angle
        self.border_style = border_style
        self.outline = outline
        self.shadow = shadow
        self.alignment = alignment
        self.margin_l = margin_l
        self.margin_r = margin_r
        self.margin_v = margin_v
        self.encoding = encoding


class _RawEvent:
    def __init__(
        self,
        *,
        layer: int,
        start_time: int,
        end_time: int,
        style: str,
        actor: str,
        margin_l: int,
        margin_r: int,
        margin_v: int,
        effect: str,
        text: str,
        comment: bool,
    ) -> None:
        self.layer = layer
        self.start_time = start_time
        self.end_time = end_time
        self.style = style
        self.actor = actor
        self.margin_l = margin_l
        self.margin_r = margin_r
        self.margin_v = margin_v
        self.effect = effect
        self.text = text
        self.comment = comment


class _AssParser:
    def __init__(self, text: str, *, stop_at_generated_fx: bool) -> None:
        self._lines = text.splitlines()
        self._script_info: dict[str, str] = {}
        self._project_garbage: dict[str, str] = {}
        self._styles: dict[str, _RawStyle] = {}
        self._events: list[_RawEvent] = []
        self._section = ""
        self._style_fields: list[str] = []
        self._event_fields: list[str] = []
        self._stop_at_generated_fx = stop_at_generated_fx
        self._stop_event_parsing = False

    def parse(self) -> _ParsedAss:
        for raw_line in self._lines:
            line = raw_line.strip()
            if not line or line.startswith(";"):
                continue
            if line.startswith("[") and line.endswith("]"):
                self._section = line
                continue
            self._parse_line(line)

        return _ParsedAss(
            script_info=self._script_info,
            project_garbage=self._project_garbage,
            styles=self._styles,
            events=self._events,
        )

    def _parse_line(self, line: str) -> None:
        if self._section == "[Script Info]":
            self._parse_key_value(line, self._script_info)
            return
        if self._section == "[Aegisub Project Garbage]":
            self._parse_key_value(line, self._project_garbage)
            return
        if self._section == "[V4+ Styles]":
            self._parse_style_line(line)
            return
        if self._section == "[Events]":
            if self._stop_event_parsing:
                return
            self._parse_event_line(line)

    def _parse_key_value(self, line: str, target: dict[str, str]) -> None:
        if ":" not in line:
            return
        key, value = line.split(":", 1)
        target[key.strip()] = value.strip()

    def _parse_style_line(self, line: str) -> None:
        if line.startswith("Format:"):
            self._style_fields = _parse_format_fields(line)
            return
        if not line.startswith(_STYLE_PREFIX):
            return
        if not self._style_fields:
            raise ValueError("Style section is missing a Format line")
        values = _split_ass_values(
            line.removeprefix(_STYLE_PREFIX).lstrip(),
            len(self._style_fields),
        )
        raw = dict(zip(self._style_fields, values, strict=True))
        style = _RawStyle(
            name=raw.get("Name", ""),
            fontname=raw.get("Fontname", ""),
            fontsize=_parse_float(raw.get("Fontsize")),
            primary_colour=_normalize_ass_color(raw.get("PrimaryColour")),
            secondary_colour=_normalize_ass_color(raw.get("SecondaryColour")),
            outline_colour=_normalize_ass_color(raw.get("OutlineColour")),
            back_colour=_normalize_ass_color(raw.get("BackColour")),
            bold=_parse_ass_bool(raw.get("Bold")),
            italic=_parse_ass_bool(raw.get("Italic")),
            underline=_parse_ass_bool(raw.get("Underline")),
            strike_out=_parse_ass_bool(raw.get("StrikeOut")),
            scale_x=_parse_float(raw.get("ScaleX")),
            scale_y=_parse_float(raw.get("ScaleY")),
            spacing=_parse_float(raw.get("Spacing")),
            angle=_parse_float(raw.get("Angle")),
            border_style=_parse_int(raw.get("BorderStyle")),
            outline=_parse_float(raw.get("Outline")),
            shadow=_parse_float(raw.get("Shadow")),
            alignment=_parse_int(raw.get("Alignment")),
            margin_l=_parse_int(raw.get("MarginL")),
            margin_r=_parse_int(raw.get("MarginR")),
            margin_v=_parse_int(raw.get("MarginV")),
            encoding=_parse_int(raw.get("Encoding")),
        )
        self._styles[style.name] = style

    def _parse_event_line(self, line: str) -> None:
        for prefix, is_comment in _EVENT_PREFIXES.items():
            if not line.startswith(prefix):
                continue
            if not self._event_fields:
                raise ValueError("Events section is missing a Format line")
            values = _split_ass_values(
                line.removeprefix(prefix).lstrip(),
                len(self._event_fields),
            )
            raw = dict(zip(self._event_fields, values, strict=True))
            effect = raw.get("Effect", "")
            if self._stop_at_generated_fx and effect == _GENERATED_EFFECT:
                self._stop_event_parsing = True
                return
            self._events.append(
                _RawEvent(
                    layer=_parse_int(raw.get("Layer")),
                    start_time=_parse_timestamp(raw.get("Start")),
                    end_time=_parse_timestamp(raw.get("End")),
                    style=raw.get("Style", ""),
                    actor=raw.get("Name", ""),
                    margin_l=_parse_int(raw.get("MarginL")),
                    margin_r=_parse_int(raw.get("MarginR")),
                    margin_v=_parse_int(raw.get("MarginV")),
                    effect=effect,
                    text=raw.get("Text", ""),
                    comment=is_comment,
                )
            )
            return
        if line.startswith("Format:"):
            self._event_fields = _parse_format_fields(line)


def _parse_format_fields(line: str) -> list[str]:
    return [field.strip() for field in line.split(":", 1)[1].split(",")]


def _split_ass_values(payload: str, field_count: int) -> list[str]:
    if field_count <= 1:
        return [payload]
    return [part.strip() for part in payload.split(",", field_count - 1)]


def _parse_ass_bool(value: str | None) -> bool:
    return _parse_int(value) != 0


def _parse_int(value: str | None) -> int:
    if value is None:
        return 0
    try:
        return int(value)
    except ValueError:
        return 0


def _parse_float(value: str | None) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0


def _normalize_ass_color(value: str | None) -> str:
    if not value:
        return "&H00000000"
    normalized = value.strip().upper()
    if normalized.startswith("&H"):
        normalized = normalized[2:]
    normalized = normalized.removesuffix("&")
    payload = normalized.rjust(8, "0")
    return f"&H{payload}"


def _parse_timestamp(value: str | None) -> int:
    if value is None:
        return 0
    try:
        hours_text, minutes_text, seconds_text = value.strip().split(":")
        seconds_whole, centiseconds_text = seconds_text.split(".", 1)
        return (
            int(hours_text) * 3600000
            + int(minutes_text) * 60000
            + int(seconds_whole) * 1000
            + int(centiseconds_text[:2].ljust(2, "0")) * 10
        )
    except ValueError:
        return 0
