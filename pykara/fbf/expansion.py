"""Frame-baked expansion utilities built on top of ASS tag utilities."""

from __future__ import annotations

import math

from pykara.adapters import SubtitleDocument
from pykara.data import Event, Metadata
from pykara.errors import PykaraError
from pykara.fbf.ass_tags import (
    LINE_DURATION_KEY,
    collect_initial_data,
    lerp_tag_fade,
    lerp_tag_move,
    lerp_tag_transform,
    split_text_blocks,
)
from pykara.fbf.timeline import FrameRateSource, coerce_framerate

FBF_FRAMERATE_REQUIRED_MESSAGE = (
    "frame-by-frame processing requires FPS information. Pass --fps FPS, "
    "--timecodes PATH, or add PlaybackFPS or Aegisub dummy-video metadata "
    "to the ASS file."
)
_DUMMY_VIDEO_MIN_TOKENS = 3
_FBF_STEP_ERROR = "frame-baked expansion step must be >= 1"


def _dummy_video_fps(raw_metadata: dict[str, str]) -> float | None:
    """Extract FPS from Aegisub dummy-video metadata when present."""
    video_file = raw_metadata.get("Video File")
    if video_file is None or not video_file.startswith("?dummy:"):
        return None
    tokens = video_file.split(":")
    if len(tokens) < _DUMMY_VIDEO_MIN_TOKENS:
        return None
    return parse_fps(tokens[1])


def parse_fps(value: str) -> float | None:
    """Parse decimal or rational FPS text."""
    text = value.strip()
    if not text:
        return None

    numerator_text, separator, denominator_text = text.partition("/")
    if separator:
        numerator = _parse_positive_float(numerator_text)
        denominator = _parse_positive_float(denominator_text)
        if numerator is None or denominator is None:
            return None
        return _validate_fps(numerator / denominator)

    return _parse_positive_float(text)


def _parse_positive_float(value: str) -> float | None:
    try:
        parsed = float(value)
    except ValueError:
        return None
    return _validate_fps(parsed)


def _validate_fps(value: float) -> float | None:
    return value if math.isfinite(value) and value > 0 else None


def _line_with_updates(
    event: Event,
    *,
    start_time: int,
    end_time: int,
    text: str,
) -> Event:
    return Event(
        text=text,
        effect=event.effect,
        style=event.style,
        layer=event.layer,
        start_time=start_time,
        end_time=end_time,
        comment=event.comment,
        actor=event.actor,
        margin_l=event.margin_l,
        margin_r=event.margin_r,
        margin_t=event.margin_t,
        margin_b=event.margin_b,
    )


def _line_duration(event: Event) -> int:
    return event.end_time - event.start_time


def resolve_metadata_framerate(
    metadata: Metadata | None,
) -> FrameRateSource | None:
    """Resolve one frame source from subtitle metadata when available."""
    if metadata is None:
        return None
    raw_fps = metadata.raw.get("PlaybackFPS")
    if raw_fps:
        fps = parse_fps(raw_fps)
        if fps is None:
            error = ValueError(f"invalid FPS: {raw_fps!r}")
            raise PykaraError(FBF_FRAMERATE_REQUIRED_MESSAGE) from error
        return fps

    dummy_fps = _dummy_video_fps(metadata.raw)
    if dummy_fps is not None:
        return dummy_fps
    return None


def _resolve_document_framerate(
    document: SubtitleDocument,
    framerate: FrameRateSource | None,
) -> FrameRateSource:
    """Resolve one frame source from explicit input or document metadata."""
    if framerate is not None:
        return framerate
    resolved = resolve_metadata_framerate(document.metadata)
    if resolved is not None:
        return resolved

    raise PykaraError(FBF_FRAMERATE_REQUIRED_MESSAGE)


def _line_frame_range(
    event: Event,
    framerate: FrameRateSource,
) -> tuple[int, int] | None:
    start_time = event.start_time
    end_time = event.end_time
    if end_time <= start_time:
        return None
    mapping = coerce_framerate(framerate)
    start_frame = mapping.frame_at_time(start_time)
    end_frame_exclusive = mapping.frame_at_time(end_time - 1) + 1
    if start_frame >= end_frame_exclusive:
        return None
    return start_frame, end_frame_exclusive


def line_to_fbf(
    event: Event,
    framerate: FrameRateSource,
    step: int = 1,
) -> list[Event]:
    """Convert one subtitle event into frame-by-frame static events."""
    if step < 1:
        raise PykaraError(_FBF_STEP_ERROR)

    mapping = coerce_framerate(framerate)
    start_time = event.start_time
    end_time = event.end_time
    line_duration = _line_duration(event)
    text_blocks = split_text_blocks(event.text)

    frame_range = _line_frame_range(event, mapping)
    if frame_range is None:
        return [event]
    start_frame, end_frame_exclusive = frame_range

    base_data = collect_initial_data(event.text)
    base_data[LINE_DURATION_KEY] = line_duration
    result_lines: list[Event] = []

    for frame_index in range(start_frame, end_frame_exclusive, step):
        step_start = max(start_time, mapping.time_at_frame(frame_index))
        step_end = min(
            end_time,
            mapping.time_at_frame(min(frame_index + step, end_frame_exclusive)),
        )
        if step_start >= step_end:
            continue
        current_time = math.floor((step_start + step_end) / 2) - start_time
        current_data = base_data.copy()
        rebuilt: list[str] = []
        first_block = True

        for tag_block, text_content in text_blocks:
            current_block = tag_block
            if current_block:
                if first_block:
                    current_block = lerp_tag_move(
                        current_time,
                        step,
                        step_start,
                        step_end,
                        start_time,
                        current_data,
                        current_block,
                    )
                    first_block = False
                current_block = lerp_tag_transform(
                    current_time,
                    step,
                    step_start,
                    step_end,
                    start_time,
                    line_duration,
                    current_data,
                    current_block,
                )
                current_block = lerp_tag_fade(
                    current_time,
                    step,
                    step_start,
                    step_end,
                    start_time,
                    line_duration,
                    current_data,
                    current_block,
                )
            else:
                first_block = False
            rebuilt.append(current_block + text_content)

        result_lines.append(
            _line_with_updates(
                event,
                start_time=step_start,
                end_time=step_end,
                text="".join(rebuilt),
            ),
        )

    return result_lines or [event]


def expand_document_to_fbf(
    document: SubtitleDocument,
    framerate: FrameRateSource | None = None,
    step: int = 1,
    *,
    include_comments: bool = False,
) -> SubtitleDocument:
    """Return a new document with events expanded to FBF output."""
    resolved_framerate = _resolve_document_framerate(document, framerate)

    expanded_events: list[Event] = []
    for event in document.events:
        if event.comment and not include_comments:
            expanded_events.append(event)
            continue
        expanded_events.extend(line_to_fbf(event, resolved_framerate, step))

    return SubtitleDocument(
        metadata=document.metadata,
        styles=document.styles,
        events=expanded_events,
    )
