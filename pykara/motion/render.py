"""Render-time helpers for motion and gradient expansion."""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from typing import cast

from pykara.data import Event, Style
from pykara.errors import EngineError
from pykara.fbf.ass_tags import (
    collect_initial_data,
    extract_all_tags_from_block,
    extract_t_tags,
    inject_pos,
    interpolate_color,
    math_round,
    parse_t_tag,
    split_text_blocks,
)
from pykara.fbf.expansion import line_to_fbf
from pykara.fbf.timeline import FrameRateSource
from pykara.motion.common import (
    SHAD_AUTO_MARKER,
    SHAD_SETUP_FRAGMENT,
    EventExpander,
)
from pykara.motion.curves import (
    RawSegment,
    arc_xy,
    bezier_xy,
    progress,
    resolve_window,
    sample_curve,
    spring_xy,
    wave_xy,
)
from pykara.motion.jitter import iter_jitter_offsets, jitter_offsets_at
from pykara.processing.font_metrics import TextMeasurement

_SUPPORTED_BAKED_TRANSFORM_TAGS = frozenset(
    {
        "fs",
        "fscx",
        "fscy",
        "fsp",
        "bord",
        "xbord",
        "ybord",
        "shad",
        "xshad",
        "yshad",
        "blur",
        "be",
    }
)
_ALIGNMENT_TAG_RE = re.compile(r"\\an\s*([1-9])")
_CLIP_TAG_RE = re.compile(r"\\(?:i?clip)\s*\(")
_MOVE_TAG_RE = re.compile(r"\\move\s*\(")
_POS_TAG_RE = re.compile(r"\\pos\s*\(")
_UNSUPPORTED_GEOMETRY_TAG_RE = re.compile(r"\\(?:frz|frx|fry|fax|fay)\b")
_COLOR_CONTROL_TAG_RE = re.compile(r"\\(?:(?:[1-4])?c)\b")
_P_TAG_RE = re.compile(r"\\p(?![A-Za-z])\s*([0-9]+)")
_DRAWING_COORDINATE_RE = re.compile(
    r"(-?(?:\d+(?:\.\d*)?|\.\d+))\s+(-?(?:\d+(?:\.\d*)?|\.\d+))",
)
_POSITION_TAG_COMPONENT_COUNT = 2
_BLEED = 1.0
_SAFE_PAD = 1.0
_OVERRIDE_BLOCK_RE = re.compile(r"\{[^}]*\}")


@dataclass(frozen=True, slots=True)
class GradientBox:
    """Absolute base box and anchor for one gradient request."""

    left: float
    top: float
    right: float
    bottom: float
    anchor_x: float
    anchor_y: float


@dataclass(frozen=True, slots=True)
class GradientStyleDefaults:
    """Default style values used when baked tags omit explicit overrides."""

    font_size: float
    scale_x: float
    scale_y: float
    spacing: float
    border: float
    shadow: float


@dataclass(frozen=True, slots=True)
class GradientPlacement:
    """Positioning metadata required to place one gradient box on screen."""

    res_x: int
    res_y: int
    alignment: int
    margin_l: int
    margin_r: int
    margin_t: int
    margin_b: int
    use_implicit_positioning: bool


GradientColorPlane = str


@dataclass(frozen=True, slots=True)
class MotionAnchor:
    """Base anchor used by motion backends."""

    x: float
    y: float


def _line_with_text(event: Event, text: str) -> Event:
    return Event(
        text=text,
        effect=event.effect,
        style=event.style,
        layer=event.layer,
        start_time=event.start_time,
        end_time=event.end_time,
        comment=event.comment,
        actor=event.actor,
        margin_l=event.margin_l,
        margin_r=event.margin_r,
        margin_t=event.margin_t,
        margin_b=event.margin_b,
    )


def _color_style_to_override(style_color: str) -> str:
    match = re.fullmatch(r"&H([0-9A-Fa-f]{2})([0-9A-Fa-f]{6})", style_color)
    if match is None:
        return "&HFFFFFF&"
    return f"&H{match.group(2).upper()}&"


def _format_ass_number(value: float) -> str:
    rounded = math_round(value, 3)
    if rounded == int(rounded):
        return str(int(rounded))
    text = f"{rounded:.3f}".rstrip("0").rstrip(".")
    return "0" if text == "-0" else text


def finalize_shad_text(
    text: str,
    style: Style,
    anchor: MotionAnchor | None = None,
    *,
    allow_position_tags: bool = False,
) -> str:
    """Resolve auto shadow markers into real setup fragments."""
    if SHAD_AUTO_MARKER not in text:
        return text
    has_position_tag = _POS_TAG_RE.search(text) or _MOVE_TAG_RE.search(text)
    if anchor is not None and not allow_position_tags and has_position_tag:
        raise EngineError(
            "motion.shad.* cannot be combined with \\pos or \\move"
        )

    injected = SHAD_SETUP_FRAGMENT
    if r"\4c" not in text:
        injected += rf"\4c{_color_style_to_override(style.primary_colour)}"
    if anchor is not None and not (allow_position_tags and has_position_tag):
        injected += (
            r"\pos("
            f"{_format_ass_number(anchor.x)},"
            f"{_format_ass_number(anchor.y)})"
        )
    return text.replace(SHAD_AUTO_MARKER, injected, 1).replace(
        SHAD_AUTO_MARKER,
        "",
    )


def fmt_shad_tags(x_shad: float, y_shad: float) -> str:
    """Return ``\\xshad...\\yshad...`` tags for float pixel offsets."""
    x_rounded = math_round(x_shad, 2)
    y_rounded = math_round(y_shad, 2)
    if x_rounded == 0:
        x_text = "0.001"
    elif x_rounded == int(x_rounded):
        x_text = str(int(x_rounded))
    else:
        x_text = str(x_rounded)
    y_text = (
        str(int(y_rounded)) if y_rounded == int(y_rounded) else str(y_rounded)
    )
    return rf"\xshad{x_text}\yshad{y_text}"


def build_shad_transforms(
    raw_segments: list[RawSegment],
    anchor_x: float,
    anchor_y: float,
) -> str:
    """Build concatenated ``\\t(...)`` transforms for shadow-trick motion."""
    if not raw_segments:
        return ""

    fragments: list[str] = []
    _, _, x0, y0, _, _ = raw_segments[0]
    current_tags = fmt_shad_tags(x0 - anchor_x, y0 - anchor_y)
    for ms0, ms1, _x0, _y0, x1, y1 in raw_segments:
        start_ms = int(ms0)
        end_ms = int(ms1)
        fragments.append(rf"\t({start_ms},{start_ms},{current_tags})")
        current_tags = fmt_shad_tags(x1 - anchor_x, y1 - anchor_y)
        fragments.append(rf"\t({start_ms},{end_ms},{current_tags})")
    return "".join(fragments)


def build_shad_jitter(
    duration_ms: int,
    anchor: MotionAnchor,
    *,
    left: int,
    right: int,
    up: int,
    down: int,
    period: int,
    seed: int,
) -> str:
    """Build one shad-trick jitter transform string."""
    del anchor
    fragments: list[str] = []
    for current_ms, x_offset, y_offset in iter_jitter_offsets(
        duration_ms,
        period,
        left,
        right,
        up,
        down,
        seed,
    ):
        fragments.append(
            rf"\t({current_ms},{current_ms},"
            f"{fmt_shad_tags(x_offset, y_offset)})"
        )
    return "".join(fragments)


def apply_curve_fbf(
    event: Event,
    framerate: FrameRateSource,
    curve_fn: Callable[[float], tuple[float, float]],
    window_start: float,
    window_end: float,
    step: int = 1,
) -> list[Event]:
    """Expand one event into FBF output driven by one sampled curve."""
    base_start = event.start_time
    baked_lines = line_to_fbf(event, framerate, step)
    result: list[Event] = []
    for baked in baked_lines:
        current_time = (
            math.floor((baked.start_time + baked.end_time) / 2) - base_start
        )
        curve_progress = progress(current_time, window_start, window_end)
        x, y = curve_fn(curve_progress)
        result.append(inject_pos(baked, math_round(x, 3), math_round(y, 3)))
    return result


@dataclass(frozen=True, slots=True)
class JitterFbfRequest(EventExpander):
    """Queued parameters for one frame-baked jitter expansion."""

    x: float
    y: float
    left: int
    right: int
    up: int
    down: int
    period: int
    seed: int
    step: int = 1

    def expand(self, event: Event, framerate: FrameRateSource) -> list[Event]:
        baked_lines = line_to_fbf(event, framerate, self.step)
        result: list[Event] = []
        for baked in baked_lines:
            current_time = (
                math.floor((baked.start_time + baked.end_time) / 2)
                - event.start_time
            )
            x_offset, y_offset = jitter_offsets_at(
                current_time,
                self.period or 1,
                self.left,
                self.right,
                self.up,
                self.down,
                self.seed,
            )
            result.append(
                inject_pos(baked, self.x + x_offset, self.y + y_offset)
            )
        return result


@dataclass(frozen=True, slots=True)
class ArcFbfRequest(EventExpander):
    """Queued parameters for one frame-baked arc expansion."""

    x1: float
    y1: float
    x2: float
    y2: float
    a1: float
    a2: float
    r1: float
    r2: float
    t1: float | None = None
    t2: float | None = None
    step: int = 1

    def expand(self, event: Event, framerate: FrameRateSource) -> list[Event]:
        window_start, window_end = resolve_window(
            self.t1,
            self.t2,
            event.end_time - event.start_time,
        )
        a1_rad = math.radians(self.a1)
        a2_rad = math.radians(self.a2)
        return apply_curve_fbf(
            event,
            framerate,
            lambda t: arc_xy(
                t,
                self.x1,
                self.y1,
                self.x2,
                self.y2,
                a1_rad,
                a2_rad,
                self.r1,
                self.r2,
            ),
            window_start,
            window_end,
            self.step,
        )


@dataclass(frozen=True, slots=True)
class BezierFbfRequest(EventExpander):
    """Queued parameters for one frame-baked Bezier expansion."""

    points: tuple[tuple[float, float], ...]
    t1: float | None = None
    t2: float | None = None
    step: int = 1

    def expand(self, event: Event, framerate: FrameRateSource) -> list[Event]:
        window_start, window_end = resolve_window(
            self.t1,
            self.t2,
            event.end_time - event.start_time,
        )
        return apply_curve_fbf(
            event,
            framerate,
            lambda t: bezier_xy(t, self.points),
            window_start,
            window_end,
            self.step,
        )


@dataclass(frozen=True, slots=True)
class SpringFbfRequest(EventExpander):
    """Queued parameters for one frame-baked spring expansion."""

    x0: float
    y0: float
    x1: float
    y1: float
    amplitude: float = 1.0
    damping: float = 3.0
    freq: float = 6.0
    t1: float | None = None
    t2: float | None = None
    step: int = 1

    def expand(self, event: Event, framerate: FrameRateSource) -> list[Event]:
        window_start, window_end = resolve_window(
            self.t1,
            self.t2,
            event.end_time - event.start_time,
        )
        return apply_curve_fbf(
            event,
            framerate,
            lambda t: spring_xy(
                t,
                self.x0,
                self.y0,
                self.x1,
                self.y1,
                self.amplitude,
                self.damping,
                self.freq,
            ),
            window_start,
            window_end,
            self.step,
        )


@dataclass(frozen=True, slots=True)
class WaveFbfRequest(EventExpander):
    """Queued parameters for one frame-baked wave expansion."""

    x0: float
    x1: float
    y_base: float
    amplitude: float = 150.0
    frequency: float = 2.0
    phase: float = 0.0
    t1: float | None = None
    t2: float | None = None
    step: int = 1

    def expand(self, event: Event, framerate: FrameRateSource) -> list[Event]:
        window_start, window_end = resolve_window(
            self.t1,
            self.t2,
            event.end_time - event.start_time,
        )
        phase_rad = math.radians(self.phase)
        return apply_curve_fbf(
            event,
            framerate,
            lambda t: wave_xy(
                t,
                self.x0,
                self.x1,
                self.y_base,
                self.amplitude,
                self.frequency,
                phase_rad,
            ),
            window_start,
            window_end,
            self.step,
        )


def build_shad_arc(
    duration_ms: int,
    anchor: MotionAnchor,
    *,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    a1: float,
    a2: float,
    r1: float,
    r2: float,
    t1: float | None = None,
    t2: float | None = None,
    segments: int = 16,
) -> str:
    """Build a shadow-trick arc transform string."""
    window_start, window_end = resolve_window(t1, t2, duration_ms)
    a1_rad = math.radians(a1)
    a2_rad = math.radians(a2)
    return build_shad_transforms(
        sample_curve(
            lambda t: arc_xy(t, x1, y1, x2, y2, a1_rad, a2_rad, r1, r2),
            segments,
            window_start,
            window_end,
        ),
        anchor.x,
        anchor.y,
    )


def build_shad_bezier(
    duration_ms: int,
    anchor: MotionAnchor,
    *,
    points: tuple[tuple[float, float], ...],
    t1: float | None = None,
    t2: float | None = None,
    segments: int | None = None,
) -> str:
    """Build a shadow-trick Bezier transform string."""
    resolved_segments = 32 if len(points) == 4 else 16
    if segments is not None:
        resolved_segments = segments
    window_start, window_end = resolve_window(t1, t2, duration_ms)
    return build_shad_transforms(
        sample_curve(
            lambda t: bezier_xy(t, points),
            resolved_segments,
            window_start,
            window_end,
        ),
        anchor.x,
        anchor.y,
    )


def build_shad_spring(
    duration_ms: int,
    anchor: MotionAnchor,
    *,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    amplitude: float = 1.0,
    damping: float = 3.0,
    freq: float = 6.0,
    t1: float | None = None,
    t2: float | None = None,
    segments: int = 48,
) -> str:
    """Build a shadow-trick spring transform string."""
    window_start, window_end = resolve_window(t1, t2, duration_ms)
    return build_shad_transforms(
        sample_curve(
            lambda t: spring_xy(t, x0, y0, x1, y1, amplitude, damping, freq),
            segments,
            window_start,
            window_end,
        ),
        anchor.x,
        anchor.y,
    )


def build_shad_wave(
    duration_ms: int,
    anchor: MotionAnchor,
    *,
    x0: float,
    x1: float,
    y_base: float,
    amplitude: float = 150.0,
    frequency: float = 2.0,
    phase: float = 0.0,
    t1: float | None = None,
    t2: float | None = None,
    segments: int = 32,
) -> str:
    """Build a shadow-trick wave transform string."""
    window_start, window_end = resolve_window(t1, t2, duration_ms)
    phase_rad = math.radians(phase)
    return build_shad_transforms(
        sample_curve(
            lambda t: wave_xy(
                t,
                x0,
                x1,
                y_base,
                amplitude,
                frequency,
                phase_rad,
            ),
            segments,
            window_start,
            window_end,
        ),
        anchor.x,
        anchor.y,
    )


GRADIENT_PLACEHOLDER = "__PYKARA_GRADIENT__"


def _resolve_numeric(
    state: Mapping[str, object],
    tag_name: str,
    default: float,
) -> float:
    value = state.get(tag_name, default)
    return float(value) if isinstance(value, int | float) else default


def _font_ratio(
    state: Mapping[str, object],
    defaults: GradientStyleDefaults,
) -> float:
    base = defaults.font_size if defaults.font_size else 1.0
    return _resolve_numeric(state, "fs", defaults.font_size) / base


def _scale_ratio(
    state: Mapping[str, object],
    tag_name: str,
    default: float,
) -> float:
    base = default if default else 100.0
    return _resolve_numeric(state, tag_name, default) / base


def _visual_padding(
    state: Mapping[str, object],
    defaults: GradientStyleDefaults,
) -> tuple[float, float, float, float]:
    border = _resolve_numeric(state, "bord", defaults.border)
    xbord = _resolve_numeric(state, "xbord", border)
    ybord = _resolve_numeric(state, "ybord", border)
    blur_pad = math.ceil(
        max(0.0, _resolve_numeric(state, "blur", 0.0))
        + max(0.0, _resolve_numeric(state, "be", 0.0))
    )
    left_pad = xbord + blur_pad + _SAFE_PAD
    right_pad = xbord + blur_pad + _SAFE_PAD
    top_pad = ybord + blur_pad + _SAFE_PAD
    bottom_pad = ybord + blur_pad + _SAFE_PAD
    return left_pad, right_pad, top_pad, bottom_pad


def _shadow_plane_offset(
    state: Mapping[str, object],
    defaults: GradientStyleDefaults,
) -> tuple[float, float]:
    shadow = _resolve_numeric(state, "shad", defaults.shadow)
    xshad = _resolve_numeric(state, "xshad", shadow)
    yshad = _resolve_numeric(state, "yshad", shadow)
    return xshad, yshad


def _gradient_color_plane(
    text: str,
    placeholder: str,
) -> GradientColorPlane:
    placeholder_index = text.find(placeholder)
    if placeholder_index < 0:
        return "fill"
    block_start = text.rfind("{", 0, placeholder_index)
    block_end = text.find("}", placeholder_index)
    if block_start < 0 or block_end < 0:
        return "fill"
    block_prefix = text[block_start:placeholder_index]
    tag_matches = list(_COLOR_CONTROL_TAG_RE.finditer(block_prefix))
    if not tag_matches:
        return "fill"
    return "shadow" if tag_matches[-1].group(0).startswith(r"\4c") else "fill"


def _visible_text_length(text: str) -> int:
    return sum(len(payload) for _block, payload in split_text_blocks(text))


def _resolved_width(
    base_box: GradientBox,
    defaults: GradientStyleDefaults,
    text: str,
    state: Mapping[str, object],
    font_ratio: float,
    scale_ratio_x: float,
) -> float:
    base_width = max(0.0, base_box.right - base_box.left)
    char_count = _visible_text_length(text)
    base_scale_x = defaults.scale_x if defaults.scale_x else 100.0
    default_spacing_width = (
        char_count * defaults.spacing * (base_scale_x / 100.0)
    )
    glyph_width = max(0.0, base_width - default_spacing_width)
    current_scale_x = _resolve_numeric(state, "fscx", defaults.scale_x)
    current_spacing = _resolve_numeric(state, "fsp", defaults.spacing)
    spacing_width = char_count * current_spacing * (current_scale_x / 100.0)
    return max(0.0, glyph_width * font_ratio * scale_ratio_x + spacing_width)


def _position_from_state(
    state: Mapping[str, object],
) -> tuple[float, float] | None:
    raw_pos = state.get("pos")
    if not isinstance(raw_pos, list):
        return None

    pos = cast("list[object]", raw_pos)
    if len(pos) < _POSITION_TAG_COMPONENT_COUNT:
        return None

    raw_x = pos[0]
    raw_y = pos[1]
    if not isinstance(raw_x, int | float) or not isinstance(
        raw_y,
        int | float,
    ):
        return None
    return float(raw_x), float(raw_y)


def _p1_drawing_bounds(text: str) -> tuple[float, float, float, float] | None:
    drawing_scale = 0
    cursor = 0
    xs: list[float] = []
    ys: list[float] = []

    def add_coordinates(payload: str) -> None:
        for match in _DRAWING_COORDINATE_RE.finditer(payload):
            xs.append(float(match.group(1)))
            ys.append(float(match.group(2)))

    for block_match in _OVERRIDE_BLOCK_RE.finditer(text):
        if drawing_scale == 1:
            add_coordinates(text[cursor : block_match.start()])
        for tag_match in _P_TAG_RE.finditer(block_match.group(0)):
            drawing_scale = int(tag_match.group(1))
        cursor = block_match.end()

    if drawing_scale == 1:
        add_coordinates(text[cursor:])
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def _resolved_drawing_box(
    base_box: GradientBox,
    defaults: GradientStyleDefaults,
    placement: GradientPlacement,
    text: str,
    state: Mapping[str, object],
) -> GradientBox | None:
    drawing_bounds = _p1_drawing_bounds(text)
    if drawing_bounds is None:
        return None

    min_x, min_y, max_x, max_y = drawing_bounds
    scale_x = _resolve_numeric(state, "fscx", defaults.scale_x) / 100.0
    scale_y = _resolve_numeric(state, "fscy", defaults.scale_y) / 100.0
    scaled_min_x = min_x * scale_x
    scaled_min_y = min_y * scale_y
    scaled_max_x = max_x * scale_x
    scaled_max_y = max_y * scale_y
    width = max(0.0, scaled_max_x - scaled_min_x)
    height = max(0.0, scaled_max_y - scaled_min_y)
    alignment = _resolved_alignment(text, placement.alignment)
    offset_x, offset_y = _drawing_alignment_offset(
        width,
        height,
        alignment,
    )

    pos = _position_from_state(state)
    if pos is not None:
        anchor_x, anchor_y = pos
    elif (
        placement.use_implicit_positioning
        and placement.res_x > 0
        and placement.res_y > 0
    ):
        left, top, right, bottom = _implicit_box(
            width,
            height,
            placement,
            alignment,
        )
        anchor_x = left - scaled_min_x + offset_x
        anchor_y = top - scaled_min_y + offset_y
    else:
        anchor_x = base_box.anchor_x
        anchor_y = base_box.anchor_y

    left = anchor_x + scaled_min_x - offset_x
    top = anchor_y + scaled_min_y - offset_y
    right = anchor_x + scaled_max_x - offset_x
    bottom = anchor_y + scaled_max_y - offset_y

    return GradientBox(
        left=left,
        top=top,
        right=right,
        bottom=bottom,
        anchor_x=anchor_x,
        anchor_y=anchor_y,
    )


def _is_left_aligned(alignment: int) -> bool:
    return alignment in {1, 4, 7}


def _is_center_aligned(alignment: int) -> bool:
    return alignment in {2, 5, 8}


def _is_top_aligned(alignment: int) -> bool:
    return alignment in {7, 8, 9}


def _is_middle_aligned(alignment: int) -> bool:
    return alignment in {4, 5, 6}


def _resolved_alignment(text: str, default: int) -> int:
    matches = _ALIGNMENT_TAG_RE.findall(text)
    if not matches:
        return default
    return int(matches[-1])


def _box_from_anchor(
    anchor_x: float,
    anchor_y: float,
    width: float,
    height: float,
    alignment: int,
) -> tuple[float, float, float, float]:
    if _is_left_aligned(alignment):
        left = anchor_x
    elif _is_center_aligned(alignment):
        left = anchor_x - width / 2
    else:
        left = anchor_x - width

    if _is_top_aligned(alignment):
        top = anchor_y
    elif _is_middle_aligned(alignment):
        top = anchor_y - height / 2
    else:
        top = anchor_y - height
    return left, top, left + width, top + height


def _implicit_box(
    width: float,
    height: float,
    placement: GradientPlacement,
    alignment: int,
) -> tuple[float, float, float, float]:
    if _is_left_aligned(alignment):
        left = float(placement.margin_l)
    elif _is_center_aligned(alignment):
        left = (
            placement.res_x - placement.margin_l - placement.margin_r - width
        ) / 2 + placement.margin_l
    else:
        left = placement.res_x - placement.margin_r - width

    if _is_top_aligned(alignment):
        top = float(placement.margin_t)
    elif _is_middle_aligned(alignment):
        top = (
            placement.res_y - placement.margin_t - placement.margin_b - height
        ) / 2 + placement.margin_t
    else:
        top = placement.res_y - placement.margin_b - height
    return left, top, left + width, top + height


def _anchor_from_box(
    left: float,
    top: float,
    right: float,
    bottom: float,
    alignment: int,
) -> tuple[float, float]:
    if _is_left_aligned(alignment):
        anchor_x = left
    elif _is_center_aligned(alignment):
        anchor_x = (left + right) / 2
    else:
        anchor_x = right

    if _is_top_aligned(alignment):
        anchor_y = top
    elif _is_middle_aligned(alignment):
        anchor_y = (top + bottom) / 2
    else:
        anchor_y = bottom
    return anchor_x, anchor_y


def _drawing_alignment_offset(
    width: float,
    height: float,
    alignment: int,
) -> tuple[float, float]:
    if _is_left_aligned(alignment):
        x_offset = 0.0
    elif _is_center_aligned(alignment):
        x_offset = width / 2
    else:
        x_offset = width

    if _is_top_aligned(alignment):
        y_offset = 0.0
    elif _is_middle_aligned(alignment):
        y_offset = height / 2
    else:
        y_offset = height
    return x_offset, y_offset


def _gradient_text_measurement(
    text: str,
    state: Mapping[str, object],
    style: Style | None,
    measure_ink: Callable[[Style, str], TextMeasurement] | None,
) -> TextMeasurement | None:
    if style is None or measure_ink is None:
        return None
    # ASS discards ordinary spaces at line edges before aligning the text.
    # Hard spaces stay in the layout and use the font's NBSP glyph metrics.
    plain = _OVERRIDE_BLOCK_RE.sub("", text).strip(" \t")
    plain = plain.replace(r"\h", "\N{NO-BREAK SPACE}")
    # Mixed font runs and wrapping need their own layout, not one font box.
    if r"\N" in plain or r"\n" in plain:
        return None
    blocks = list(split_text_blocks(text))
    has_text = False
    for block, payload in blocks:
        if re.search(r"\\r(?:[^\\}]*)", block) or (
            has_text and re.search(r"\\(?:fn|fs|[bius](?![a-z]))", block)
        ):
            return None
        has_text = has_text or bool(payload)
    font_names = re.findall(r"\\fn([^\\}]+)", text)

    def flag(tag: str, default: bool) -> bool:
        values = re.findall(rf"\\{tag}(-?\d+)", text)
        return bool(int(values[-1])) if values else default

    resolved_style = replace(
        style,
        fontname=font_names[-1] if font_names else style.fontname,
        fontsize=_resolve_numeric(state, "fs", style.fontsize),
        scale_x=_resolve_numeric(state, "fscx", style.scale_x),
        scale_y=_resolve_numeric(state, "fscy", style.scale_y),
        spacing=_resolve_numeric(state, "fsp", style.spacing),
        bold=flag("b", style.bold),
        italic=flag("i", style.italic),
        underline=flag("u", style.underline),
        strike_out=flag("s", style.strike_out),
    )
    if resolved_style.fontsize <= 0:
        return TextMeasurement(0, 0, 0, 0, (0, 0, 0, 0))
    return measure_ink(resolved_style, plain)


def _resolved_text_box(
    base_box: GradientBox,
    style_defaults: GradientStyleDefaults,
    placement: GradientPlacement,
    text: str,
    state: Mapping[str, object],
    measurement: TextMeasurement | None = None,
) -> GradientBox:
    font_ratio = _font_ratio(state, style_defaults)
    scale_x = _scale_ratio(state, "fscx", style_defaults.scale_x)
    scale_y = font_ratio * _scale_ratio(
        state,
        "fscy",
        style_defaults.scale_y,
    )
    width = _resolved_width(
        base_box,
        style_defaults,
        text,
        state,
        font_ratio,
        scale_x,
    )
    height = (base_box.bottom - base_box.top) * scale_y
    if measurement is not None:
        width = measurement.width
        height = measurement.height
    alignment = _resolved_alignment(text, placement.alignment)
    pos = _position_from_state(state)

    if pos is not None:
        anchor_x, anchor_y = pos
        left, top, right, bottom = _box_from_anchor(
            anchor_x,
            anchor_y,
            width,
            height,
            alignment,
        )
    elif (
        placement.use_implicit_positioning
        and placement.res_x > 0
        and placement.res_y > 0
    ):
        left, top, right, bottom = _implicit_box(
            width,
            height,
            placement,
            alignment,
        )
        anchor_x, anchor_y = _anchor_from_box(
            left,
            top,
            right,
            bottom,
            alignment,
        )
    else:
        anchor_x = base_box.anchor_x
        anchor_y = base_box.anchor_y
        if measurement is not None:
            left, top, right, bottom = _box_from_anchor(
                anchor_x,
                anchor_y,
                width,
                height,
                alignment,
            )
        else:
            left = anchor_x + (base_box.left - base_box.anchor_x) * scale_x
            right = anchor_x + (base_box.right - base_box.anchor_x) * scale_x
            top = anchor_y + (base_box.top - base_box.anchor_y) * scale_y
            bottom = anchor_y + (base_box.bottom - base_box.anchor_y) * scale_y

    if measurement is not None and measurement.ink_bounds is not None:
        ink_left, ink_top, ink_right, ink_bottom = measurement.ink_bounds
        right = left + ink_right
        bottom = top + ink_bottom
        left += ink_left
        top += ink_top

    return GradientBox(
        left=left,
        top=top,
        right=right,
        bottom=bottom,
        anchor_x=anchor_x,
        anchor_y=anchor_y,
    )


def _resolved_box(
    base_box: GradientBox,
    style_defaults: GradientStyleDefaults,
    placement: GradientPlacement,
    event: Event,
    *,
    color_plane: GradientColorPlane,
    style: Style | None = None,
    measure_ink: Callable[[Style, str], TextMeasurement] | None = None,
) -> GradientBox:
    state = collect_initial_data(event.text)
    box = _resolved_drawing_box(
        base_box,
        style_defaults,
        placement,
        event.text,
        state,
    )
    if box is None:
        measurement = _gradient_text_measurement(
            event.text,
            state,
            style,
            measure_ink,
        )
        box = _resolved_text_box(
            base_box,
            style_defaults,
            placement,
            event.text,
            state,
            measurement,
        )

    left_pad, right_pad, top_pad, bottom_pad = _visual_padding(
        state,
        style_defaults,
    )
    plane_offset_x = 0.0
    plane_offset_y = 0.0
    if color_plane == "shadow":
        plane_offset_x, plane_offset_y = _shadow_plane_offset(
            state,
            style_defaults,
        )
    else:
        xshad, yshad = _shadow_plane_offset(state, style_defaults)
        left_pad += max(0.0, -xshad)
        right_pad += max(0.0, xshad)
        top_pad += max(0.0, -yshad)
        bottom_pad += max(0.0, yshad)
    return GradientBox(
        left=box.left - left_pad + plane_offset_x,
        top=box.top - top_pad + plane_offset_y,
        right=box.right + right_pad + plane_offset_x,
        bottom=box.bottom + bottom_pad + plane_offset_y,
        anchor_x=box.anchor_x,
        anchor_y=box.anchor_y,
    )


def _format_clip_number(value: float) -> str:
    rounded = math.floor(value * 100 + 0.5) / 100
    if rounded == int(rounded):
        return str(int(rounded))
    text = f"{rounded:.2f}".rstrip("0").rstrip(".")
    return "0" if text == "-0" else text


def _slice_count(box: GradientBox, direction: str, step: float) -> int:
    span = (
        max(0.0, box.bottom - box.top)
        if direction in {"top-bottom", "bottom-top"}
        else max(0.0, box.right - box.left)
    )
    return max(1, math.ceil(span / step))


def _slice_t(direction: str, index: int, count: int) -> float:
    if count <= 1:
        return 0.0
    value = index / (count - 1)
    if direction in {"bottom-top", "right-left"}:
        return 1.0 - value
    return value


def _color_at(colors: tuple[str, ...], t: float) -> str:
    if t <= 0.0:
        return colors[0]
    if t >= 1.0:
        return colors[-1]
    scaled = t * (len(colors) - 1)
    left_index = math.floor(scaled)
    right_index = min(left_index + 1, len(colors) - 1)
    local_t = scaled - left_index
    return interpolate_color(local_t, colors[left_index], colors[right_index])


def _slice_colors(
    colors: tuple[str, ...],
    direction: str,
    count: int,
) -> tuple[str, ...]:
    if count <= 1:
        return (colors[0],)
    return tuple(
        _color_at(colors, _slice_t(direction, index, count))
        for index in range(count)
    )


def _slice_clip(
    box: GradientBox,
    direction: str,
    index: int,
    count: int,
    step: float,
) -> list[float]:
    if direction in {"top-bottom", "bottom-top"}:
        start = box.top + step * index
        end = min(box.top + step * (index + 1), box.bottom)
        if count > 1:
            if index > 0:
                start = max(box.top, start - _BLEED)
            if index < count - 1:
                end = min(box.bottom, end + _BLEED)
        return [box.left, start, box.right, end]

    start = box.left + step * index
    end = min(box.left + step * (index + 1), box.right)
    if count > 1:
        if index > 0:
            start = max(box.left, start - _BLEED)
        if index < count - 1:
            end = min(box.right, end + _BLEED)
    return [start, box.top, end, box.bottom]


def _format_rectangular_clip(clip_rect: list[float]) -> str:
    left, top, right, bottom = clip_rect
    return (
        r"\clip("
        + _format_clip_number(left)
        + ","
        + _format_clip_number(top)
        + ","
        + _format_clip_number(right)
        + ","
        + _format_clip_number(bottom)
        + ")"
    )


def _split_first_block(text: str) -> tuple[str, str, str]:
    match = _OVERRIDE_BLOCK_RE.search(text)
    if match is None:
        return "", "{}", text
    return text[: match.start()], match.group(0), text[match.end() :]


@dataclass(frozen=True, slots=True)
class _GradientTextTemplate:
    before_clip: str
    after_clip: str
    before_head: str
    before_tail: str
    before_has_placeholder: bool
    after_head: str
    after_tail: str
    after_has_placeholder: bool


def _prepare_gradient_text_template(
    text: str,
    placeholder: str,
) -> _GradientTextTemplate:
    prefix, first_block, suffix = _split_first_block(text)
    before_clip = prefix + first_block[:-1]
    after_clip = "}" + suffix
    before_head, before_sep, before_tail = before_clip.partition(placeholder)
    after_head, after_sep, after_tail = after_clip.partition(placeholder)
    return _GradientTextTemplate(
        before_clip=before_clip,
        after_clip=after_clip,
        before_head=before_head,
        before_tail=before_tail,
        before_has_placeholder=bool(before_sep),
        after_head=after_head,
        after_tail=after_tail,
        after_has_placeholder=bool(after_sep),
    )


def _build_gradient_slice_text(
    template: _GradientTextTemplate,
    color: str,
    clip_rect: list[float],
) -> str:
    clip_text = _format_rectangular_clip(clip_rect)
    if template.before_has_placeholder:
        return (
            template.before_head
            + color
            + template.before_tail
            + clip_text
            + template.after_clip
        )
    if template.after_has_placeholder:
        return (
            template.before_clip
            + clip_text
            + template.after_head
            + color
            + template.after_tail
        )
    return template.before_clip + clip_text + template.after_clip


def _baked_gradient_lines(
    event: Event,
    framerate: FrameRateSource,
) -> list[Event]:
    for block_match in _OVERRIDE_BLOCK_RE.finditer(event.text):
        payloads, _text = extract_t_tags(block_match.group(0))
        for payload in payloads:
            _t1, _t2, _accel, transform = parse_t_tag(payload)
            transform_tags = extract_all_tags_from_block(transform)
            if _SUPPORTED_BAKED_TRANSFORM_TAGS & frozenset(transform_tags):
                return line_to_fbf(event, framerate)
    return [event]


def validate_gradient_event(event: Event) -> None:
    """Reject event content that is incompatible with baked gradients."""
    if _MOVE_TAG_RE.search(event.text):
        raise EngineError("gradient.make() cannot be combined with \\move")
    if _CLIP_TAG_RE.search(event.text):
        raise EngineError(
            "gradient.make() cannot be combined with \\clip or \\iclip"
        )
    if _UNSUPPORTED_GEOMETRY_TAG_RE.search(event.text):
        raise EngineError(
            "gradient.make() does not support rotation or shear tags"
        )


@dataclass(frozen=True, slots=True)
class GradientRequest(EventExpander):
    """Queued parameters for one gradient expansion."""

    placeholder: str
    colors: tuple[str, ...]
    step: float
    direction: str
    box: GradientBox
    style_defaults: GradientStyleDefaults
    placement: GradientPlacement
    style: Style | None = None
    measure_ink: Callable[[Style, str], TextMeasurement] | None = None

    def expand(self, event: Event, framerate: FrameRateSource) -> list[Event]:
        validate_gradient_event(event)
        result_lines: list[Event] = []
        for baked_event in _baked_gradient_lines(event, framerate):
            color_plane = _gradient_color_plane(
                baked_event.text,
                self.placeholder,
            )
            box = _resolved_box(
                self.box,
                self.style_defaults,
                self.placement,
                baked_event,
                color_plane=color_plane,
                style=self.style,
                measure_ink=self.measure_ink,
            )
            positioned = inject_pos(baked_event, box.anchor_x, box.anchor_y)
            count = _slice_count(box, self.direction, self.step)
            slice_colors = _slice_colors(self.colors, self.direction, count)
            text_template = _prepare_gradient_text_template(
                positioned.text,
                self.placeholder,
            )
            for index in range(count):
                clip_rect = _slice_clip(
                    box,
                    self.direction,
                    index,
                    count,
                    self.step,
                )
                result_lines.append(
                    _line_with_text(
                        positioned,
                        _build_gradient_slice_text(
                            text_template,
                            slice_colors[index],
                            clip_rect,
                        ),
                    )
                )
        return result_lines


def _replace_gradient_placeholder(
    text: str,
    placeholder: str,
    color: str,
) -> str:
    return text.replace(placeholder, color)


@dataclass(frozen=True, slots=True)
class MultiGradientRequest(EventExpander):
    """Expand multiple queued gradients with one shared clip segmentation."""

    requests: tuple[GradientRequest, ...]

    @property
    def step(self) -> float:
        return min(request.step for request in self.requests)

    def expand(self, event: Event, framerate: FrameRateSource) -> list[Event]:
        validate_gradient_event(event)
        if not self.requests:
            return [event]

        priority = min(
            enumerate(self.requests),
            key=lambda item: (item[1].step, item[0]),
        )[1]
        result_lines: list[Event] = []
        for baked_event in _baked_gradient_lines(event, framerate):
            priority_plane = _gradient_color_plane(
                baked_event.text,
                priority.placeholder,
            )
            priority_box = _resolved_box(
                priority.box,
                priority.style_defaults,
                priority.placement,
                baked_event,
                color_plane=priority_plane,
                style=priority.style,
                measure_ink=priority.measure_ink,
            )
            positioned = inject_pos(
                baked_event,
                priority_box.anchor_x,
                priority_box.anchor_y,
            )
            count = _slice_count(
                priority_box,
                priority.direction,
                priority.step,
            )
            request_colors = {
                request.placeholder: _slice_colors(
                    request.colors,
                    request.direction,
                    count,
                )
                for request in self.requests
            }
            text_template = _prepare_gradient_text_template(
                positioned.text,
                priority.placeholder,
            )
            for index in range(count):
                clip_rect = _slice_clip(
                    priority_box,
                    priority.direction,
                    index,
                    count,
                    priority.step,
                )
                text = positioned.text
                for request in self.requests:
                    if request is priority:
                        continue
                    text = _replace_gradient_placeholder(
                        text,
                        request.placeholder,
                        request_colors[request.placeholder][index],
                    )
                result_lines.append(
                    _line_with_text(
                        positioned,
                        _build_gradient_slice_text(
                            _prepare_gradient_text_template(
                                text,
                                priority.placeholder,
                            )
                            if text != positioned.text
                            else text_template,
                            request_colors[priority.placeholder][index],
                            clip_rect,
                        ),
                    )
                )
        return result_lines
