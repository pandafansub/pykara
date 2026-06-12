"""Gradient namespace implementation."""

from __future__ import annotations

from collections.abc import Sequence
from typing import ClassVar, Protocol, cast

from pykara.data import Metadata
from pykara.engine.functions._base import BoundNamespaceFunction
from pykara.errors import EngineError
from pykara.fbf.expansion import resolve_metadata_framerate
from pykara.motion import (
    GRADIENT_PLACEHOLDER,
    GradientBox,
    GradientPlacement,
    GradientRequest,
    GradientStyleDefaults,
)
from pykara.motion.common import QueuedEventExpansion, queue_event_expansion

_VALID_DIRECTIONS = frozenset(
    {"top-bottom", "bottom-top", "left-right", "right-left"}
)


class _StyleLike(Protocol):
    fontsize: float
    scale_x: float
    scale_y: float
    spacing: float
    outline: float
    shadow: float
    alignment: int
    margin_l: int
    margin_r: int
    margin_t: int
    margin_b: int


class _GeneratedLine(Protocol):
    styleref: _StyleLike
    text: str
    margin_l: int
    margin_r: int
    margin_t: int
    margin_b: int
    expansion_requests: list[QueuedEventExpansion]
    motion_auto_shad: bool


class _VarsLike(Protocol):
    line_left: int | None
    line_top: int | None
    line_right: int | None
    line_bottom: int | None
    line_center: int | None
    line_y: int | None
    line_x: int | None
    char_left: int | None
    char_top: int | None
    char_right: int | None
    char_bottom: int | None
    char_center: int | None
    char_middle: int | None
    word_left: int | None
    word_top: int | None
    word_right: int | None
    word_bottom: int | None
    word_center: int | None
    word_middle: int | None
    syl_left: int | None
    syl_top: int | None
    syl_right: int | None
    syl_bottom: int | None
    syl_center: int | None
    syl_middle: int | None


class _GradientEnvironment(Protocol):
    metadata: Metadata | None
    line: _GeneratedLine | None
    vars: _VarsLike
    word: object | None
    syl: object | None
    char: object | None


def _require_line(env: _GradientEnvironment) -> _GeneratedLine:
    if env.line is None:
        raise EngineError("gradient.make() requires line runtime")
    return env.line


def _queue_expansion(line: _GeneratedLine, request: GradientRequest) -> None:
    queue_event_expansion(
        line,
        QueuedEventExpansion(
            label="gradient.make()",
            phase="gradient",
            expander=request,
        ),
    )


def _require_box_value(value: int | None, name: str) -> float:
    if value is None:
        raise EngineError(f"gradient.make() requires {name} geometry")
    return float(value)


def _gradient_box(env: _GradientEnvironment) -> GradientBox:
    context_vars = env.vars
    if env.char is not None:
        return GradientBox(
            left=_require_box_value(context_vars.char_left, "char"),
            top=_require_box_value(context_vars.char_top, "char"),
            right=_require_box_value(context_vars.char_right, "char"),
            bottom=_require_box_value(context_vars.char_bottom, "char"),
            anchor_x=_require_box_value(context_vars.char_center, "char"),
            anchor_y=_require_box_value(context_vars.char_middle, "char"),
        )
    if env.word is not None:
        return GradientBox(
            left=_require_box_value(context_vars.word_left, "word"),
            top=_require_box_value(context_vars.word_top, "word"),
            right=_require_box_value(context_vars.word_right, "word"),
            bottom=_require_box_value(context_vars.word_bottom, "word"),
            anchor_x=_require_box_value(context_vars.word_center, "word"),
            anchor_y=_require_box_value(context_vars.word_middle, "word"),
        )
    if env.syl is not None:
        return GradientBox(
            left=_require_box_value(context_vars.syl_left, "syl"),
            top=_require_box_value(context_vars.syl_top, "syl"),
            right=_require_box_value(context_vars.syl_right, "syl"),
            bottom=_require_box_value(context_vars.syl_bottom, "syl"),
            anchor_x=_require_box_value(context_vars.syl_center, "syl"),
            anchor_y=_require_box_value(context_vars.syl_middle, "syl"),
        )
    return GradientBox(
        left=_require_box_value(context_vars.line_left, "line"),
        top=_require_box_value(context_vars.line_top, "line"),
        right=_require_box_value(context_vars.line_right, "line"),
        bottom=_require_box_value(context_vars.line_bottom, "line"),
        anchor_x=_require_box_value(context_vars.line_center, "line"),
        anchor_y=_require_box_value(context_vars.line_y, "line"),
    )


def _gradient_style_defaults(style: _StyleLike) -> GradientStyleDefaults:
    return GradientStyleDefaults(
        font_size=float(style.fontsize),
        scale_x=float(style.scale_x),
        scale_y=float(style.scale_y),
        spacing=float(style.spacing),
        border=float(style.outline),
        shadow=float(style.shadow),
    )


def _resolved_margin(line_margin: int, style_margin: int) -> int:
    return line_margin if line_margin else style_margin


def _gradient_placement(
    env: _GradientEnvironment,
    line: _GeneratedLine,
) -> GradientPlacement:
    metadata = env.metadata
    style = line.styleref
    return GradientPlacement(
        res_x=metadata.res_x if metadata is not None else 0,
        res_y=metadata.res_y if metadata is not None else 0,
        alignment=int(style.alignment),
        margin_l=_resolved_margin(line.margin_l, style.margin_l),
        margin_r=_resolved_margin(line.margin_r, style.margin_r),
        margin_t=_resolved_margin(line.margin_t, style.margin_t),
        margin_b=_resolved_margin(line.margin_b, style.margin_b),
        use_implicit_positioning=(
            env.char is None and env.word is None and env.syl is None
        ),
    )


def _validate_colors(raw_colors: object) -> tuple[str, ...]:
    if isinstance(raw_colors, (str, bytes)) or not isinstance(
        raw_colors,
        Sequence,
    ):
        raise EngineError("gradient.make() expects a sequence of ASS colors")
    colors = tuple(cast(Sequence[object], raw_colors))
    if not all(isinstance(color, str) for color in colors):
        raise EngineError("gradient.make() expects ASS colors as strings")
    if len(colors) < 2:
        raise EngineError("gradient.make() requires at least two ASS colors")
    return cast(tuple[str, ...], colors)


def _validate_step(raw_step: object) -> float:
    if isinstance(raw_step, bool) or not isinstance(raw_step, int | float):
        raise EngineError("gradient.make() step must be a positive number")
    step = float(raw_step)
    if step <= 0:
        raise EngineError("gradient.make() step must be a positive number")
    return step


def _validate_direction(raw_direction: object) -> str:
    if (
        not isinstance(raw_direction, str)
        or raw_direction not in _VALID_DIRECTIONS
    ):
        accepted = ", ".join(sorted(_VALID_DIRECTIONS))
        raise EngineError(
            f"gradient.make() direction must be one of: {accepted}"
        )
    return raw_direction


class _GradientNamespace:
    def __init__(self, env: _GradientEnvironment) -> None:
        self._env = env

    def make(
        self,
        colors: object,
        step: object = 2,
        direction: object = "top-bottom",
        **kwargs: object,
    ) -> str:
        if kwargs:
            unknown_names = ", ".join(sorted(kwargs))
            raise EngineError(
                "gradient.make() got unexpected keyword arguments: "
                f"{unknown_names}"
            )
        line = _require_line(self._env)
        if resolve_metadata_framerate(self._env.metadata) is None:
            raise EngineError(
                "gradient.make() requires explicit timecodes or PlaybackFPS"
            )
        if r"\move" in line.text:
            raise EngineError("gradient.make() cannot be combined with \\move")
        call_index = sum(
            1
            for queued_expansion in line.expansion_requests
            if queued_expansion.phase == "gradient"
        )
        placeholder = f"{GRADIENT_PLACEHOLDER}:{call_index}:"
        request = GradientRequest(
            placeholder=placeholder,
            colors=_validate_colors(colors),
            step=_validate_step(step),
            direction=_validate_direction(direction),
            box=_gradient_box(self._env),
            style_defaults=_gradient_style_defaults(line.styleref),
            placement=_gradient_placement(self._env, line),
        )
        _queue_expansion(line, request)
        return placeholder


class GradientFunction(BoundNamespaceFunction):
    """Expose ``gradient`` as a bound namespace."""

    name: ClassVar[str] = "gradient"
    applicable_to: ClassVar[frozenset[str]] = frozenset({"template"})

    def build_bound(self, env: object) -> object:
        gradient_env = cast(_GradientEnvironment, env)
        return _GradientNamespace(gradient_env)
