"""Retime namespace implementation."""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from types import SimpleNamespace
from typing import ClassVar, Protocol, cast

from pykara.declaration import Scope
from pykara.errors import EngineError


class _TimedLine(Protocol):
    start_time: int
    end_time: int


class _GeneratedLine(_TimedLine, Protocol):
    duration: int


class _TimedElement(Protocol):
    start_time: int
    end_time: int
    duration: int
    index: int
    center: float
    x: float


class _RetimeEnvironment(Protocol):
    source_line: _TimedLine | None
    line: _GeneratedLine | None
    word: _TimedElement | None
    syl: _TimedElement | None
    char: _TimedElement | None
    char_index: int | None
    line_char_count: int | None
    active_template_scope: Scope | None
    retime_used: bool
    retime_line_words: Sequence[_TimedElement]
    retime_line_syls: Sequence[_TimedElement]
    retime_line_chars: Sequence[_TimedElement]
    retime_syl_chars: Sequence[_TimedElement]


RetimeMode = Callable[[_TimedLine, _TimedElement | None], tuple[int, int]]
PresetFunction = Callable[[int, int, Sequence[_TimedElement]], float]

_SYLLABLE_TARGETS = frozenset(
    {"syl", "presyl", "postsyl", "start2syl", "syl2end"}
)
_LINE_TARGETS = frozenset({"line", "preline", "postline"})
_TARGETS = _LINE_TARGETS | _SYLLABLE_TARGETS
_PRESETS = frozenset(
    {
        "ltr",
        "rtl",
        "from_center",
        "from_edges",
        "odd_first",
        "even_first",
        "spatial_ltr",
        "spatial_rtl",
        "random",
    }
)


def _require_source_line(env: _RetimeEnvironment) -> _TimedLine:
    if env.source_line is None:
        raise EngineError("retime requires line context")
    return env.source_line


def _require_output_line(env: _RetimeEnvironment) -> _GeneratedLine:
    if env.line is None:
        raise EngineError("retime requires an active generated line")
    return env.line


def _require_syllable(
    syllable: _TimedElement | None,
    target: str,
) -> _TimedElement:
    if syllable is None:
        raise EngineError(f"retime.{target} requires syllable context")
    return syllable


def _mode_syl(
    source_line: _TimedLine,
    syllable: _TimedElement | None,
) -> tuple[int, int]:
    current_syllable = _require_syllable(syllable, "syl")
    return (
        source_line.start_time + current_syllable.start_time,
        source_line.start_time + current_syllable.end_time,
    )


def _mode_presyl(
    source_line: _TimedLine,
    syllable: _TimedElement | None,
) -> tuple[int, int]:
    current_syllable = _require_syllable(syllable, "presyl")
    base = source_line.start_time + current_syllable.start_time
    return base, base


def _mode_postsyl(
    source_line: _TimedLine,
    syllable: _TimedElement | None,
) -> tuple[int, int]:
    current_syllable = _require_syllable(syllable, "postsyl")
    base = source_line.start_time + current_syllable.end_time
    return base, base


def _mode_line(
    source_line: _TimedLine,
    syllable: _TimedElement | None,
) -> tuple[int, int]:
    del syllable
    return source_line.start_time, source_line.end_time


def _mode_preline(
    source_line: _TimedLine,
    syllable: _TimedElement | None,
) -> tuple[int, int]:
    del syllable
    return source_line.start_time, source_line.start_time


def _mode_postline(
    source_line: _TimedLine,
    syllable: _TimedElement | None,
) -> tuple[int, int]:
    del syllable
    return source_line.end_time, source_line.end_time


def _mode_start2syl(
    source_line: _TimedLine,
    syllable: _TimedElement | None,
) -> tuple[int, int]:
    current_syllable = _require_syllable(syllable, "start2syl")
    return (
        source_line.start_time,
        source_line.start_time + current_syllable.start_time,
    )


def _mode_syl2end(
    source_line: _TimedLine,
    syllable: _TimedElement | None,
) -> tuple[int, int]:
    current_syllable = _require_syllable(syllable, "syl2end")
    return (
        source_line.start_time + current_syllable.end_time,
        source_line.end_time,
    )


RETIME_MODES: dict[str, RetimeMode] = {
    "syl": _mode_syl,
    "presyl": _mode_presyl,
    "postsyl": _mode_postsyl,
    "line": _mode_line,
    "preline": _mode_preline,
    "postline": _mode_postline,
    "start2syl": _mode_start2syl,
    "syl2end": _mode_syl2end,
}


def _round_time(value: float) -> int:
    return round(value)


def _factor_ltr(
    index: int,
    total: int,
    collection: Sequence[_TimedElement],
) -> float:
    del collection
    return (index - 1) / (total - 1)


def _factor_rtl(
    index: int,
    total: int,
    collection: Sequence[_TimedElement],
) -> float:
    del collection
    return (total - index) / (total - 1)


def _factor_from_center(
    index: int,
    total: int,
    collection: Sequence[_TimedElement],
) -> float:
    del collection
    return abs(index - (total + 1) / 2) / ((total - 1) / 2)


def _factor_from_edges(
    index: int,
    total: int,
    collection: Sequence[_TimedElement],
) -> float:
    return 1 - _factor_from_center(index, total, collection)


def _factor_odd_first(
    index: int,
    total: int,
    collection: Sequence[_TimedElement],
) -> float:
    del total, collection
    return float((index - 1) % 2)


def _factor_even_first(
    index: int,
    total: int,
    collection: Sequence[_TimedElement],
) -> float:
    del total, collection
    return float(index % 2)


def _factor_spatial_ltr(
    index: int,
    total: int,
    collection: Sequence[_TimedElement],
) -> float:
    del total
    xs = [element.x for element in collection]
    left = min(xs)
    right = max(xs)
    if left == right:
        raise EngineError("retime spatial preset requires distinct x positions")
    current = collection[index - 1].x
    return (current - left) / (right - left)


def _factor_spatial_rtl(
    index: int,
    total: int,
    collection: Sequence[_TimedElement],
) -> float:
    return 1 - _factor_spatial_ltr(index, total, collection)


def _factor_random(
    index: int,
    total: int,
    collection: Sequence[_TimedElement],
) -> float:
    del total, collection
    return abs(math.sin(index * 127.1 + 311.7))


PRESET_FACTORS: dict[str, PresetFunction] = {
    "ltr": _factor_ltr,
    "rtl": _factor_rtl,
    "from_center": _factor_from_center,
    "from_edges": _factor_from_edges,
    "odd_first": _factor_odd_first,
    "even_first": _factor_even_first,
    "spatial_ltr": _factor_spatial_ltr,
    "spatial_rtl": _factor_spatial_rtl,
    "random": _factor_random,
}


class _RetimeTarget:
    """One callable retime target with preset methods attached."""

    __slots__ = ("_env", "_target")

    def __init__(self, env: _RetimeEnvironment, target: str) -> None:
        self._env = env
        self._target = target

    def __call__(
        self,
        start_offset: int = 0,
        end_offset: int = 0,
    ) -> None:
        self._apply(start_offset, end_offset, preset=None)
        return None

    def __getattr__(self, name: str) -> Callable[[int, int], None]:
        if name not in _PRESETS:
            raise AttributeError(name)
        return self._build_preset(name)

    def _build_preset(
        self,
        preset: str,
    ) -> Callable[[int, int], None]:
        def call(start_offset: int = 0, end_offset: int = 0) -> None:
            self._apply(start_offset, end_offset, preset=preset)
            return None

        return call

    def _apply(
        self,
        start_offset: int,
        end_offset: int,
        *,
        preset: str | None,
    ) -> None:
        _validate_target_scope(self._env, self._target, preset)
        if self._env.retime_used:
            raise EngineError("only one retime call is allowed per template")
        self._env.retime_used = True

        source_line = _require_source_line(self._env)
        output_line = _require_output_line(self._env)
        start, end = RETIME_MODES[self._target](source_line, self._env.syl)

        if preset is None:
            resolved_start = start + start_offset
            resolved_end = end + end_offset
        else:
            factor = _resolve_preset_factor(self._env, self._target, preset)
            resolved_start = start + _round_time(start_offset * (1 - factor))
            resolved_end = end + _round_time(end_offset * factor)

        output_line.start_time = resolved_start
        output_line.end_time = resolved_end
        output_line.duration = output_line.end_time - output_line.start_time


class RetimeNamespace(SimpleNamespace):
    """Public ``retime`` namespace exposed to templates."""


class RetimeFunction:
    """Build the public retime namespace for one execution environment."""

    name: ClassVar[str] = "retime"
    aliases: ClassVar[tuple[str, ...]] = ()
    applicable_to: ClassVar[frozenset[str]] = frozenset({"template"})

    def build_bound(self, env: object) -> RetimeNamespace:
        typed_env = cast(_RetimeEnvironment, env)
        return RetimeNamespace(
            **{
                target: _RetimeTarget(typed_env, target)
                for target in sorted(_TARGETS)
            }
        )

    def __call__(self, env: object, *args: object, **kwargs: object) -> None:
        del env, args, kwargs
        raise EngineError("use retime.<target>(start_offset, end_offset)")


def _validate_target_scope(
    env: _RetimeEnvironment,
    target: str,
    preset: str | None,
) -> None:
    scope = env.active_template_scope
    if scope is None:
        raise EngineError("retime is only valid while rendering a template")
    if target not in _TARGETS:
        raise EngineError(f"unknown retime target: {target!r}")

    if preset is None:
        if target in _LINE_TARGETS:
            if scope not in {Scope.LINE, Scope.WORD, Scope.SYL, Scope.CHAR}:
                raise EngineError(f"retime.{target} is invalid in {scope}")
            return
        if scope not in {Scope.SYL, Scope.CHAR}:
            raise EngineError(f"retime.{target} is invalid in {scope}")
        return

    if preset not in _PRESETS:
        raise EngineError(f"unknown retime preset: {preset!r}")
    if scope is Scope.LINE:
        raise EngineError(f"retime.{target}.{preset} is invalid in line")
    if target in _LINE_TARGETS:
        if scope in {Scope.WORD, Scope.SYL, Scope.CHAR}:
            return
        raise EngineError(f"retime.{target}.{preset} is invalid in {scope}")
    if target in {"syl", "presyl", "postsyl"}:
        if scope is Scope.CHAR:
            return
        raise EngineError(f"retime.{target}.{preset} is invalid in {scope}")
    if target in {"start2syl", "syl2end"}:
        if scope in {Scope.SYL, Scope.CHAR}:
            return
        raise EngineError(f"retime.{target}.{preset} is invalid in {scope}")


def _resolve_preset_factor(
    env: _RetimeEnvironment,
    target: str,
    preset: str,
) -> float:
    collection, zero_based_index = _implicit_collection(env, target)
    total = len(collection)
    if total <= 1:
        raise EngineError("retime preset requires at least two elements")
    one_based_index = zero_based_index + 1
    return PRESET_FACTORS[preset](one_based_index, total, collection)


def _implicit_collection(
    env: _RetimeEnvironment,
    target: str,
) -> tuple[Sequence[_TimedElement], int]:
    scope = env.active_template_scope
    if target in _LINE_TARGETS:
        if scope is Scope.WORD:
            current = _require_element_index(env.word, "word")
            return env.retime_line_words, current
        if scope is Scope.SYL:
            current = _require_element_index(env.syl, "syl")
            return env.retime_line_syls, current
        if scope is Scope.CHAR:
            return env.retime_line_chars, _require_char_index(env)

    if target in {"syl", "presyl", "postsyl"} and scope is Scope.CHAR:
        current = _require_element_index(env.char, "char")
        return env.retime_syl_chars, current

    if target in {"start2syl", "syl2end"}:
        if scope is Scope.SYL:
            current = _require_element_index(env.syl, "syl")
            return env.retime_line_syls, current
        if scope is Scope.CHAR:
            return env.retime_line_chars, _require_char_index(env)

    raise EngineError(f"retime.{target} has no preset collection here")


def _require_element_index(
    element: _TimedElement | None,
    name: str,
) -> int:
    if element is None:
        raise EngineError(f"retime preset requires {name} context")
    return element.index


def _require_char_index(env: _RetimeEnvironment) -> int:
    if env.char_index is None:
        raise EngineError("retime line preset requires char context")
    return env.char_index
