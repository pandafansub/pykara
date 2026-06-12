"""Motion namespace implementation."""

from __future__ import annotations

import math
import re
from types import SimpleNamespace
from typing import ClassVar, Protocol, cast

from pykara.data import Metadata
from pykara.engine.functions._base import BoundNamespaceFunction
from pykara.errors import EngineError
from pykara.fbf.expansion import (
    FBF_FRAMERATE_REQUIRED_MESSAGE,
    resolve_metadata_framerate,
)
from pykara.fbf.timeline import FrameRateSource
from pykara.motion import (
    SHAD_AUTO_MARKER,
    ArcFbfRequest,
    BezierFbfRequest,
    JitterFbfRequest,
    MotionAnchor,
    SpringFbfRequest,
    WaveFbfRequest,
    build_shad_arc,
    build_shad_bezier,
    build_shad_jitter,
    build_shad_spring,
    build_shad_wave,
    validate_jitter_spec,
)
from pykara.motion.common import (
    EventExpander,
    QueuedEventExpansion,
    queue_event_expansion,
    queued_expansion_for_phase,
)
from pykara.motion.curves import arc_xy, bezier_xy, wave_xy


class _GeneratedLine(Protocol):
    text: str
    start_time: int
    end_time: int
    duration: int
    styleref: object
    expansion_requests: list[QueuedEventExpansion]
    motion_auto_shad: bool
    motion_shad_anchor_x: float | None
    motion_shad_anchor_y: float | None
    motion_shad_allow_position_tags: bool


class _TimedElement(Protocol):
    center: float
    middle: float
    x: float
    y: float


class _MotionEnvironment(Protocol):
    metadata: Metadata | None
    fbf_framerate: FrameRateSource | None
    line: _GeneratedLine | None
    vars: object
    word: _TimedElement | None
    syl: _TimedElement | None
    char: _TimedElement | None
    rendering_mixin: bool


class _VarsLike(Protocol):
    line_x: int | None
    line_y: int | None


class _UnavailableMotionNamespace:
    def __getattr__(self, name: str) -> object:
        del name
        raise EngineError("motion.* can only be used in template bodies")


def _require_output_line(env: _MotionEnvironment, label: str) -> _GeneratedLine:
    if env.line is None:
        raise EngineError(f"{label} requires line runtime")
    return env.line


def _require_fbf_runtime(env: _MotionEnvironment, label: str) -> _GeneratedLine:
    line = _require_output_line(env, label)
    if (
        env.fbf_framerate is None
        and resolve_metadata_framerate(env.metadata) is None
    ):
        raise EngineError(
            f"{label} requires FPS information. "
            f"{FBF_FRAMERATE_REQUIRED_MESSAGE}"
        )
    return line


_POSITION_TAG_RE = re.compile(r"\\(?:pos|move)\s*\(")
_MOVE_TAG_RE = re.compile(r"\\move\s*\(")


def _motion_anchor(env: _MotionEnvironment) -> MotionAnchor:
    if env.char is not None:
        return MotionAnchor(float(env.char.center), float(env.char.middle))
    if env.word is not None:
        return MotionAnchor(float(env.word.center), float(env.word.middle))
    if env.syl is not None:
        return MotionAnchor(float(env.syl.center), float(env.syl.middle))
    line_x = cast(_VarsLike, env.vars).line_x
    line_y = cast(_VarsLike, env.vars).line_y
    if line_x is None or line_y is None:
        _require_output_line(env, "motion")
        raise EngineError("motion requires line positioning geometry")
    return MotionAnchor(float(line_x), float(line_y))


def _queue_expansion(
    line: _GeneratedLine,
    *,
    label: str,
    request: EventExpander,
) -> None:
    if line.motion_auto_shad:
        raise EngineError(f"{label} cannot be combined with motion.shad.*")
    _validate_no_position_tags(line.text, label)
    queued_expansion = queued_expansion_for_phase(line, "motion_fbf")
    if queued_expansion is not None:
        active_label = queued_expansion.label or "another expansion"
        raise EngineError(f"{label} cannot be combined with {active_label}")
    queue_event_expansion(
        line,
        QueuedEventExpansion(
            label=label,
            phase="motion_fbf",
            expander=request,
        ),
    )


def _validate_no_position_tags(text: str, label: str) -> None:
    if _POSITION_TAG_RE.search(text):
        raise EngineError(f"{label} cannot be combined with \\pos or \\move")


def _validate_no_move_tags(text: str, label: str) -> None:
    if _MOVE_TAG_RE.search(text):
        raise EngineError(f"{label} cannot be combined with \\move")


def _validate_no_fbf_expansion(line: _GeneratedLine, label: str) -> None:
    queued_expansion = queued_expansion_for_phase(line, "motion_fbf")
    if queued_expansion is not None:
        active_label = queued_expansion.label or "motion.fbf.*"
        raise EngineError(f"{label} cannot be combined with {active_label}")


def _mark_shad_auto(
    line: _GeneratedLine,
    *,
    label: str,
    anchor: MotionAnchor,
    allow_position_tags: bool = False,
) -> None:
    if line.motion_auto_shad:
        raise EngineError(f"{label} cannot be combined with motion.shad.*")
    _validate_no_fbf_expansion(line, label)
    if not allow_position_tags:
        _validate_no_position_tags(line.text, label)
    else:
        _validate_no_move_tags(line.text, label)
    line.motion_auto_shad = True
    line.motion_shad_anchor_x = anchor.x
    line.motion_shad_anchor_y = anchor.y
    line.motion_shad_allow_position_tags = allow_position_tags


class _ShadMotionNamespace:
    def __init__(self, env: _MotionEnvironment) -> None:
        self._env = env

    def jitter(
        self,
        left: object,
        right: object,
        up: object,
        down: object,
        period: object,
        seed: object = 0,
    ) -> str:
        label = "motion.shad.jitter()"
        line = _require_output_line(self._env, label)
        anchor = _motion_anchor(self._env)
        spec = validate_jitter_spec(
            left,
            right,
            up,
            down,
            period,
            seed,
            label=label,
        )
        _mark_shad_auto(
            line,
            label=label,
            anchor=anchor,
            allow_position_tags=True,
        )
        return SHAD_AUTO_MARKER + build_shad_jitter(
            line.duration,
            anchor,
            left=spec.left,
            right=spec.right,
            up=spec.up,
            down=spec.down,
            period=spec.period,
            seed=spec.seed,
        )

    def arc(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        a1: float = 0.0,
        a2: float = 360.0,
        r1: float = 100.0,
        r2: float = 100.0,
        t1: float | None = None,
        t2: float | None = None,
        segments: int = 16,
    ) -> str:
        label = "motion.shad.arc()"
        line = _require_output_line(self._env, label)
        anchor_x, anchor_y = arc_xy(
            0.0,
            x1,
            y1,
            x2,
            y2,
            math.radians(a1),
            math.radians(a2),
            r1,
            r2,
        )
        anchor = MotionAnchor(anchor_x, anchor_y)
        _mark_shad_auto(line, label=label, anchor=anchor)
        return SHAD_AUTO_MARKER + build_shad_arc(
            line.duration,
            anchor,
            x1=x1,
            y1=y1,
            x2=x2,
            y2=y2,
            a1=a1,
            a2=a2,
            r1=r1,
            r2=r2,
            t1=t1,
            t2=t2,
            segments=segments,
        )

    def bezier(
        self,
        *points: tuple[float, float],
        t1: float | None = None,
        t2: float | None = None,
        segments: int | None = None,
    ) -> str:
        label = "motion.shad.bezier()"
        line = _require_output_line(self._env, label)
        anchor_x, anchor_y = bezier_xy(0.0, tuple(points))
        anchor = MotionAnchor(anchor_x, anchor_y)
        _mark_shad_auto(line, label=label, anchor=anchor)
        return SHAD_AUTO_MARKER + build_shad_bezier(
            line.duration,
            anchor,
            points=tuple(points),
            t1=t1,
            t2=t2,
            segments=segments,
        )

    def spring(
        self,
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
        label = "motion.shad.spring()"
        line = _require_output_line(self._env, label)
        anchor = MotionAnchor(x0, y0)
        _mark_shad_auto(line, label=label, anchor=anchor)
        return SHAD_AUTO_MARKER + build_shad_spring(
            line.duration,
            anchor,
            x0=x0,
            y0=y0,
            x1=x1,
            y1=y1,
            amplitude=amplitude,
            damping=damping,
            freq=freq,
            t1=t1,
            t2=t2,
            segments=segments,
        )

    def wave(
        self,
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
        label = "motion.shad.wave()"
        line = _require_output_line(self._env, label)
        anchor_x, anchor_y = wave_xy(
            0.0,
            x0,
            x1,
            y_base,
            amplitude,
            frequency,
            math.radians(phase),
        )
        anchor = MotionAnchor(anchor_x, anchor_y)
        _mark_shad_auto(line, label=label, anchor=anchor)
        return SHAD_AUTO_MARKER + build_shad_wave(
            line.duration,
            anchor,
            x0=x0,
            x1=x1,
            y_base=y_base,
            amplitude=amplitude,
            frequency=frequency,
            phase=phase,
            t1=t1,
            t2=t2,
            segments=segments,
        )


class _FbfMotionNamespace:
    def __init__(self, env: _MotionEnvironment) -> None:
        self._env = env

    def jitter(
        self,
        left: object,
        right: object,
        up: object,
        down: object,
        period: object,
        seed: object = 0,
    ) -> str:
        label = "motion.fbf.jitter()"
        line = _require_fbf_runtime(self._env, label)
        spec = validate_jitter_spec(
            left,
            right,
            up,
            down,
            period,
            seed,
            label=label,
        )
        anchor = _motion_anchor(self._env)
        _queue_expansion(
            line,
            label=label,
            request=JitterFbfRequest(
                x=anchor.x,
                y=anchor.y,
                left=spec.left,
                right=spec.right,
                up=spec.up,
                down=spec.down,
                period=spec.period,
                seed=spec.seed,
            ),
        )
        return ""

    def arc(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        a1: float = 0.0,
        a2: float = 360.0,
        r1: float = 100.0,
        r2: float = 100.0,
        t1: float | None = None,
        t2: float | None = None,
    ) -> str:
        label = "motion.fbf.arc()"
        line = _require_fbf_runtime(self._env, label)
        _queue_expansion(
            line,
            label=label,
            request=ArcFbfRequest(x1, y1, x2, y2, a1, a2, r1, r2, t1, t2),
        )
        return ""

    def bezier(
        self,
        *points: tuple[float, float],
        t1: float | None = None,
        t2: float | None = None,
    ) -> str:
        label = "motion.fbf.bezier()"
        line = _require_fbf_runtime(self._env, label)
        _queue_expansion(
            line,
            label=label,
            request=BezierFbfRequest(tuple(points), t1, t2),
        )
        return ""

    def spring(
        self,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        amplitude: float = 1.0,
        damping: float = 3.0,
        freq: float = 6.0,
        t1: float | None = None,
        t2: float | None = None,
    ) -> str:
        label = "motion.fbf.spring()"
        line = _require_fbf_runtime(self._env, label)
        _queue_expansion(
            line,
            label=label,
            request=SpringFbfRequest(
                x0,
                y0,
                x1,
                y1,
                amplitude,
                damping,
                freq,
                t1,
                t2,
            ),
        )
        return ""

    def wave(
        self,
        x0: float,
        x1: float,
        y_base: float,
        amplitude: float = 150.0,
        frequency: float = 2.0,
        phase: float = 0.0,
        t1: float | None = None,
        t2: float | None = None,
    ) -> str:
        label = "motion.fbf.wave()"
        line = _require_fbf_runtime(self._env, label)
        _queue_expansion(
            line,
            label=label,
            request=WaveFbfRequest(
                x0,
                x1,
                y_base,
                amplitude,
                frequency,
                phase,
                t1,
                t2,
            ),
        )
        return ""


class MotionFunction(BoundNamespaceFunction):
    """Expose ``motion`` as a bound namespace."""

    name: ClassVar[str] = "motion"
    applicable_to: ClassVar[frozenset[str]] = frozenset({"template"})

    def build_bound(self, env: object) -> object:
        motion_env = cast(_MotionEnvironment, env)
        if getattr(motion_env, "rendering_mixin", False):
            return _UnavailableMotionNamespace()
        return SimpleNamespace(
            shad=_ShadMotionNamespace(motion_env),
            fbf=_FbfMotionNamespace(motion_env),
        )
