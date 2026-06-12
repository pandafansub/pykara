"""Runtime variable context and execution environment."""

from __future__ import annotations

import math
import random
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, fields
from types import SimpleNamespace
from typing import Any, NoReturn, TypeVar

from pykara.data import Karaoke, Metadata, Style
from pykara.data.events.event import Event
from pykara.data.events.karaoke.syllable import Syllable, Word
from pykara.declaration import Scope
from pykara.declaration.template.modifiers import TemplateModifiers
from pykara.engine.assets import assets
from pykara.engine.functions import FUNCTION_REGISTRY
from pykara.engine.safe_builtins import SAFE_BUILTINS
from pykara.errors import ExecutionAttributeUnavailableError
from pykara.fbf.timeline import FrameRateSource
from pykara.motion.common import QueuedEventExpansion
from pykara.specification import (
    EXPOSED_MODULES,
    EXPRESSION_PROPERTY_SPECIFICATIONS,
)


def _round_coordinate(value: float) -> int:
    return math.floor(value + 0.5)


_KARAOKE_TAG_FAMILY_PATTERN = re.compile(r"^(\\[A-Za-z]+)")


def _karaoke_tag_family(tag: str) -> str:
    match = _KARAOKE_TAG_FAMILY_PATTERN.match(tag)
    if match is None:
        return tag
    return match.group(1)


def _raise_unavailable_attribute(attribute_name: str) -> NoReturn:
    raise ExecutionAttributeUnavailableError(attribute_name)


_ChoiceT = TypeVar("_ChoiceT")
_CharSyllableCacheKey = tuple[int, int, str, float]


def _empty_store() -> dict[str, object]:
    return {}


def _empty_locked_store_keys() -> set[str]:
    return set()


def _empty_user_namespace() -> dict[str, object]:
    return {}


def _empty_user_code_names() -> set[str]:
    return set()


def _empty_include_names() -> set[str]:
    return set()


def _empty_loop_stack() -> list[LoopState]:
    return []


def _empty_function_namespace_cache() -> dict[str, dict[str, object]]:
    return {}


def _empty_char_syllable_cache() -> dict[
    _CharSyllableCacheKey,
    tuple[Syllable, ...],
]:
    return {}


def _empty_choice_no_repeat_state() -> dict[object, object]:
    return {}


def _empty_expansion_requests() -> list[QueuedEventExpansion]:
    return []


_BOX_FIELD_NAMES = (
    "left",
    "center",
    "right",
    "width",
    "top",
    "middle",
    "bottom",
    "height",
    "x",
    "y",
)


@dataclass(slots=True)
class _RandomNamespace:
    """Random API exposed to user expressions."""

    rng: random.Random
    _choice_no_repeat_state: dict[object, object] = field(
        default_factory=_empty_choice_no_repeat_state
    )
    _callsite: object = None

    def random(self) -> float:
        return self.rng.random()

    def randint(self, a: int, b: int) -> int:
        return self.rng.randint(a, b)

    def choice(self, seq: Sequence[_ChoiceT]) -> _ChoiceT:
        return self.rng.choice(seq)

    def choice_no_repeat(self, seq: Sequence[_ChoiceT]) -> _ChoiceT:
        values = tuple(seq)
        if not values:
            return self.rng.choice(values)

        callsite = self._callsite
        previous = self._choice_no_repeat_state.get(callsite)
        candidates = tuple(value for value in values if value != previous)
        if not candidates:
            candidates = values

        selected = self.rng.choice(candidates)
        self._choice_no_repeat_state[callsite] = selected
        return selected

    def _set_callsite(self, callsite: object) -> None:
        self._callsite = callsite


def set_random_callsite(
    namespace: Mapping[str, object],
    callsite: object,
) -> None:
    """Route no-repeat random choices to isolated state for this call site."""

    random_namespace = namespace.get("random")
    set_callsite = getattr(random_namespace, "_set_callsite", None)
    if set_callsite is not None:
        set_callsite(callsite)


_WORD_SCOPE_FIELDS = (
    "word_start",
    "word_end",
    "word_dur",
    "word_kdur",
    "word_mid",
    "word_n",
    "word_i",
    "word_left",
    "word_center",
    "word_right",
    "word_width",
    "word_top",
    "word_middle",
    "word_bottom",
    "word_height",
    "word_x",
    "word_y",
)

_SYL_SCOPE_FIELDS = (
    "syl_start",
    "syl_end",
    "syl_dur",
    "syl_kdur",
    "syl_mid",
    "syl_n",
    "syl_i",
    "syl_left",
    "syl_center",
    "syl_right",
    "syl_width",
    "syl_top",
    "syl_middle",
    "syl_bottom",
    "syl_height",
    "syl_x",
    "syl_y",
)

_CHAR_SCOPE_FIELDS = (
    "char_left",
    "char_i",
    "char_n",
    "char_center",
    "char_right",
    "char_width",
    "char_top",
    "char_middle",
    "char_bottom",
    "char_height",
    "char_x",
    "char_y",
)

_CHAR_SNAPSHOT_FIELDS = ("_char_n", *_CHAR_SCOPE_FIELDS)


def _rounded_box_values(prefix: str, item: object) -> dict[str, int]:
    return {
        f"{prefix}_{field_name}": _round_coordinate(
            getattr(item, field_name),
        )
        for field_name in _BOX_FIELD_NAMES
    }


@dataclass(slots=True)
class VarContext:
    """Holds the current line, syllable, and character variables."""

    _syl_n: int | None = None
    _char_n: int | None = None
    _word_n: int | None = None
    line_start: int | None = None
    line_end: int | None = None
    line_dur: int | None = None
    line_mid: float | None = None
    line_i: int | None = None
    line_left: int | None = None
    line_center: int | None = None
    line_right: int | None = None
    line_width: int | None = None
    line_top: int | None = None
    line_middle: int | None = None
    line_bottom: int | None = None
    line_height: int | None = None
    line_x: int | None = None
    line_y: int | None = None
    word_start: int | None = None
    word_end: int | None = None
    word_dur: int | None = None
    word_kdur: float | None = None
    word_mid: float | None = None
    word_n: int | None = None
    word_i: int | None = None
    word_left: int | None = None
    word_center: int | None = None
    word_right: int | None = None
    word_width: int | None = None
    word_top: int | None = None
    word_middle: int | None = None
    word_bottom: int | None = None
    word_height: int | None = None
    word_x: int | None = None
    word_y: int | None = None
    syl_start: int | None = None
    syl_end: int | None = None
    syl_dur: int | None = None
    syl_kdur: float | None = None
    syl_mid: float | None = None
    syl_n: int | None = None
    syl_i: int | None = None
    syl_left: int | None = None
    syl_center: int | None = None
    syl_right: int | None = None
    syl_width: int | None = None
    syl_top: int | None = None
    syl_middle: int | None = None
    syl_bottom: int | None = None
    syl_height: int | None = None
    syl_x: int | None = None
    syl_y: int | None = None
    char_left: int | None = None
    char_i: int | None = None
    char_n: int | None = None
    char_center: int | None = None
    char_right: int | None = None
    char_width: int | None = None
    char_top: int | None = None
    char_middle: int | None = None
    char_bottom: int | None = None
    char_height: int | None = None
    char_x: int | None = None
    char_y: int | None = None

    def _set_values(self, values: Mapping[str, object]) -> None:
        for field_name, value in values.items():
            setattr(self, field_name, value)

    def _clear_values(self, field_names: tuple[str, ...]) -> None:
        for field_name in field_names:
            setattr(self, field_name, None)

    def _snapshot(self, field_names: tuple[str, ...]) -> tuple[Any, ...]:
        return tuple(getattr(self, field_name) for field_name in field_names)

    def _restore(
        self,
        field_names: tuple[str, ...],
        snapshot: tuple[Any, ...],
    ) -> None:
        for field_name, value in zip(field_names, snapshot, strict=True):
            setattr(self, field_name, value)

    def set_line(
        self,
        *,
        index: int,
        start_time: int,
        end_time: int,
        width: float,
        height: float,
        left: float,
        center: float,
        right: float,
        top: float,
        middle: float,
        bottom: float,
        x: float,
        y: float,
        syllable_count: int,
        word_count: int,
    ) -> None:
        """Populate line-level variables."""

        self.line_start = start_time
        self.line_end = end_time
        self.line_dur = end_time - start_time
        self.line_mid = start_time + self.line_dur / 2
        self.line_i = index
        self.line_left = _round_coordinate(left)
        self.line_center = _round_coordinate(center)
        self.line_right = _round_coordinate(right)
        self.line_width = _round_coordinate(width)
        self.line_top = _round_coordinate(top)
        self.line_middle = _round_coordinate(middle)
        self.line_bottom = _round_coordinate(bottom)
        self.line_height = _round_coordinate(height)
        self.line_x = _round_coordinate(x)
        self.line_y = _round_coordinate(y)
        self._syl_n = syllable_count
        self._word_n = word_count
        self.clear_word()

    def set_word(self, word: Word) -> None:
        """Populate word-level variables."""

        self._set_values(
            {
                "word_start": word.start_time,
                "word_end": word.end_time,
                "word_dur": word.duration,
                "word_kdur": word.kdur,
                "word_mid": word.start_time + word.duration / 2,
                "word_n": self._word_n,
                "word_i": word.index,
                **_rounded_box_values("word", word),
            }
        )
        self.clear_syl()

    def set_syl(self, syllable: Syllable) -> None:
        """Populate syllable-level variables."""

        self._set_values(
            {
                "syl_start": syllable.start_time,
                "syl_end": syllable.end_time,
                "syl_dur": syllable.duration,
                "syl_kdur": syllable.kdur,
                "syl_mid": syllable.start_time + syllable.duration / 2,
                "syl_n": self._syl_n,
                "syl_i": syllable.index,
                **_rounded_box_values("syl", syllable),
            }
        )
        self.clear_char()

    def clear_word(self) -> None:
        """Reset word-level variables when leaving word scope."""

        self._clear_values(_WORD_SCOPE_FIELDS)
        self.clear_syl()

    def clear_syl(self) -> None:
        """Reset syllable-level variables when leaving syllable scope."""

        self._clear_values(_SYL_SCOPE_FIELDS)
        self.clear_char()

    def set_char(
        self,
        syllable: Syllable,
        *,
        char_count: int,
        char_index: int,
    ) -> None:
        """Populate character-level variables."""

        self._char_n = char_count
        self._set_values(
            {
                "char_i": char_index,
                "char_n": self._char_n,
                **_rounded_box_values("char", syllable),
            }
        )

    def clear_char(self) -> None:
        """Reset character-level variables when leaving char scope."""

        self._clear_values(_CHAR_SCOPE_FIELDS)

    def snapshot_word_scope(self) -> tuple[Any, ...]:
        """Capture word, syllable, and char variables for restoration."""

        return (
            *self._snapshot(_WORD_SCOPE_FIELDS),
            *self.snapshot_syllable_scope(),
        )

    def restore_word_scope(self, snapshot: tuple[Any, ...]) -> None:
        """Restore word, syllable, and char variables from one snapshot."""

        word_field_count = len(_WORD_SCOPE_FIELDS)
        self._restore(_WORD_SCOPE_FIELDS, snapshot[:word_field_count])
        self.restore_syllable_scope(snapshot[word_field_count:])

    def snapshot_syllable_scope(self) -> tuple[Any, ...]:
        """Capture syllable and char variables for restoration."""

        return (
            *self._snapshot(_SYL_SCOPE_FIELDS),
            *self.snapshot_char_scope(),
        )

    def restore_syllable_scope(self, snapshot: tuple[Any, ...]) -> None:
        """Restore syllable and char variables from one snapshot."""

        syl_field_count = len(_SYL_SCOPE_FIELDS)
        self._restore(_SYL_SCOPE_FIELDS, snapshot[:syl_field_count])
        self.restore_char_scope(snapshot[syl_field_count:])

    def snapshot_char_scope(self) -> tuple[Any, ...]:
        """Capture char variables for restoration."""

        return self._snapshot(_CHAR_SNAPSHOT_FIELDS)

    def restore_char_scope(self, snapshot: tuple[Any, ...]) -> None:
        """Restore char variables from one snapshot."""

        self._restore(_CHAR_SNAPSHOT_FIELDS, snapshot)

    def as_dict(self) -> dict[str, object]:
        """Return the current variable mapping without missing values."""

        return {
            field_name: value
            for field_name in _VAR_CONTEXT_VARIABLE_FIELD_NAMES
            if (value := getattr(self, field_name)) is not None
        }


_VAR_CONTEXT_VARIABLE_FIELD_NAMES = tuple(
    field_info.name
    for field_info in fields(VarContext)
    if not field_info.name.startswith("_")
)

_RESERVED_EXECUTION_NAMES = frozenset(
    {
        *_VAR_CONTEXT_VARIABLE_FIELD_NAMES,
        *EXPOSED_MODULES,
        *SAFE_BUILTINS,
        "actor",
        "char",
        "layer",
        "line",
        "loop",
        "loop_i",
        "loop_n",
        "metadata",
        "assets",
        "retime",
        "style",
        "syl",
        "word",
    }
)


class _MathNamespace:
    """Immutable math helper namespace exposed to execution."""

    __slots__ = ()

    ceil = math.ceil
    cos = math.cos
    fabs = math.fabs
    floor = math.floor
    radians = math.radians
    sin = math.sin
    sqrt = math.sqrt


@dataclass(frozen=True, slots=True)
class _ExpressionLoopStateObject:
    """Read-only loop state exposed to inline expressions."""

    i: int
    n: int


class _ExpressionLoopObject:
    """Public `loop` object exposed to expression evaluation."""

    __slots__ = ("_env",)

    def __init__(self, env: Environment) -> None:
        self._env = env

    @property
    def i(self) -> int:
        return self._only_loop().index

    @property
    def n(self) -> int:
        return self._only_loop().total

    def __getattr__(self, name: str) -> _ExpressionLoopStateObject:
        loop_state = self._named_loop(name)
        return _ExpressionLoopStateObject(
            i=loop_state.index,
            n=loop_state.total,
        )

    def _only_loop(self) -> LoopState:
        if len(self._env.loop_stack) == 1:
            return self._env.loop_stack[0]
        _raise_unavailable_attribute("loop")

    def _named_loop(self, name: str) -> LoopState:
        for loop_state in reversed(self._env.loop_stack):
            if loop_state.name == name:
                return loop_state
        _raise_unavailable_attribute(f"loop.{name}")


def _empty_expression_object_cache() -> dict[str, object]:
    return {}


def _empty_exposed_module_cache() -> dict[str, object]:
    return {
        module_name: _MathNamespace()
        for module_name in EXPOSED_MODULES
        if module_name == "math"
    }


@dataclass(frozen=True, slots=True)
class LoopState:
    """One active loop iteration visible in the current execution context."""

    name: str
    index: int
    total: int
    scope: Scope


@dataclass(slots=True)
class GeneratedLine:
    """Mutable generated line used during template execution."""

    text: str
    effect: str
    style: str
    layer: int
    start_time: int
    end_time: int
    comment: bool
    actor: str
    margin_l: int
    margin_r: int
    margin_t: int
    margin_b: int
    styleref: Style
    duration: int
    expansion_requests: list[QueuedEventExpansion] = field(
        default_factory=_empty_expansion_requests
    )
    motion_auto_shad: bool = False
    motion_shad_anchor_x: float | None = None
    motion_shad_anchor_y: float | None = None
    motion_shad_allow_position_tags: bool = False

    @classmethod
    def from_event(cls, event: Event, styleref: Style) -> GeneratedLine:
        return cls(
            text=event.text,
            effect="fx",
            style=event.style,
            layer=event.layer,
            start_time=event.start_time,
            end_time=event.end_time,
            comment=False,
            actor=event.actor,
            margin_l=event.margin_l,
            margin_r=event.margin_r,
            margin_t=event.margin_t,
            margin_b=event.margin_b,
            styleref=styleref,
            duration=event.end_time - event.start_time,
        )

    def to_event(self) -> Event:
        return Event(
            text=self.text,
            effect=self.effect,
            style=self.style,
            layer=self.layer,
            start_time=self.start_time,
            end_time=self.end_time,
            comment=self.comment,
            actor=self.actor,
            margin_l=self.margin_l,
            margin_r=self.margin_r,
            margin_t=self.margin_t,
            margin_b=self.margin_b,
        )


class _ExpressionStyleObject:
    """Public `style` object exposed to expression evaluation."""

    __slots__ = ("_env",)

    def __init__(self, env: Environment) -> None:
        self._env = env

    @property
    def name(self) -> str:
        return self._style().name

    @property
    def primary_color(self) -> str:
        return self._style().primary_colour

    @property
    def secondary_color(self) -> str:
        return self._style().secondary_colour

    @property
    def outline_color(self) -> str:
        return self._style().outline_colour

    @property
    def shadow_color(self) -> str:
        return self._style().back_colour

    @property
    def outline(self) -> float:
        return self._style().outline

    def _style(self) -> Style:
        if self._env.reference_style is not None:
            return self._env.reference_style
        if self._env.line is not None:
            return self._env.line.styleref
        if self._env.source_line is not None:
            return self._env.styles[self._env.source_line.style]
        _raise_unavailable_attribute("style")


class _ExpressionMetadataObject:
    """Public `metadata` object exposed to expression evaluation."""

    __slots__ = ("_env",)

    def __init__(self, env: Environment) -> None:
        self._env = env

    @property
    def res_x(self) -> int:
        return self._metadata().res_x

    @property
    def res_y(self) -> int:
        return self._metadata().res_y

    def _metadata(self) -> Metadata:
        if self._env.metadata is None:
            _raise_unavailable_attribute("metadata")
        return self._env.metadata


class _ExpressionKaraokeSyllableObject:
    """Read-only karaoke syllable view exposed through ``line.syls``."""

    __slots__ = ("_syllable",)

    def __init__(self, syllable: Syllable) -> None:
        self._syllable = syllable

    @property
    def start_time(self) -> int:
        return self._syllable.start_time

    @property
    def end_time(self) -> int:
        return self._syllable.end_time

    @property
    def duration(self) -> int:
        return self._syllable.duration

    @property
    def kdur(self) -> float:
        return self._syllable.kdur

    @property
    def left(self) -> float:
        return self._syllable.left

    @property
    def center(self) -> float:
        return self._syllable.center

    @property
    def right(self) -> float:
        return self._syllable.right

    @property
    def width(self) -> float:
        return self._syllable.width

    @property
    def top(self) -> float:
        return self._syllable.top

    @property
    def middle(self) -> float:
        return self._syllable.middle

    @property
    def bottom(self) -> float:
        return self._syllable.bottom

    @property
    def height(self) -> float:
        return self._syllable.height

    @property
    def x(self) -> float:
        return self._syllable.x

    @property
    def y(self) -> float:
        return self._syllable.y


class _ExpressionLineObject:
    """Public `line` object exposed to expression evaluation."""

    __slots__ = ("_env",)

    def __init__(self, env: Environment) -> None:
        self._env = env

    @property
    def layer(self) -> int:
        if self._env.line is not None:
            return self._env.line.layer
        if self._env.source_line is not None:
            return self._env.source_line.layer
        _raise_unavailable_attribute("layer")

    @property
    def actor(self) -> str:
        if self._env.line is not None:
            return self._env.line.actor
        if self._env.source_line is not None:
            return self._env.source_line.actor
        _raise_unavailable_attribute("actor")

    @property
    def raw_text(self) -> str:
        if self._env.source_line is None:
            _raise_unavailable_attribute("raw_text")
        return self._env.source_line.text

    @property
    def text(self) -> str:
        if self._env.karaoke is None:
            _raise_unavailable_attribute("text")
        return self._env.karaoke.text

    @property
    def trimmed_text(self) -> str:
        if self._env.karaoke is None:
            _raise_unavailable_attribute("trimmed_text")
        return self._env.karaoke.trimmed_text

    @property
    def start(self) -> int:
        if self._env.line is not None:
            return self._env.line.start_time
        return self._required_int("line_start", self._env.vars.line_start)

    @property
    def end(self) -> int:
        if self._env.line is not None:
            return self._env.line.end_time
        return self._required_int("line_end", self._env.vars.line_end)

    @property
    def dur(self) -> int:
        if self._env.line is not None:
            return self._env.line.duration
        return self._required_int("line_dur", self._env.vars.line_dur)

    @property
    def mid(self) -> float:
        if self._env.line is not None:
            return self._env.line.start_time + self._env.line.duration / 2
        return self._required_float("line_mid", self._env.vars.line_mid)

    @property
    def i(self) -> int:
        return self._required_int("line_i", self._env.vars.line_i)

    @property
    def left(self) -> int:
        return self._required_int("line_left", self._env.vars.line_left)

    @property
    def center(self) -> int:
        return self._required_int("line_center", self._env.vars.line_center)

    @property
    def right(self) -> int:
        return self._required_int("line_right", self._env.vars.line_right)

    @property
    def width(self) -> int:
        return self._required_int("line_width", self._env.vars.line_width)

    @property
    def top(self) -> int:
        return self._required_int("line_top", self._env.vars.line_top)

    @property
    def middle(self) -> int:
        return self._required_int("line_middle", self._env.vars.line_middle)

    @property
    def bottom(self) -> int:
        return self._required_int("line_bottom", self._env.vars.line_bottom)

    @property
    def height(self) -> int:
        return self._required_int("line_height", self._env.vars.line_height)

    @property
    def x(self) -> int:
        return self._required_int("line_x", self._env.vars.line_x)

    @property
    def y(self) -> int:
        return self._required_int("line_y", self._env.vars.line_y)

    @property
    def syls(self) -> tuple[_ExpressionKaraokeSyllableObject, ...]:
        if self._env.active_line_syls is not None:
            syllables = self._env.active_line_syls
        elif self._env.karaoke is not None:
            syllables = self._env.karaoke.syllables
        else:
            _raise_unavailable_attribute("syls")
        return tuple(
            _ExpressionKaraokeSyllableObject(syllable) for syllable in syllables
        )

    def _required_int(self, name: str, value: int | None) -> int:
        if value is None:
            _raise_unavailable_attribute(name)
        return value

    def _required_float(self, name: str, value: float | None) -> float:
        if value is None:
            _raise_unavailable_attribute(name)
        return value


class _ExpressionSyllableObject:
    """Public `syl` object exposed to expression evaluation."""

    __slots__ = ("_env",)

    def __init__(self, env: Environment) -> None:
        self._env = env

    @property
    def start(self) -> int:
        return self._required_int("syl_start", self._env.vars.syl_start)

    @property
    def end(self) -> int:
        return self._required_int("syl_end", self._env.vars.syl_end)

    @property
    def dur(self) -> int:
        return self._required_int("syl_dur", self._env.vars.syl_dur)

    @property
    def kdur(self) -> float:
        return self._required_float("syl_kdur", self._env.vars.syl_kdur)

    @property
    def mid(self) -> float:
        return self._required_float("syl_mid", self._env.vars.syl_mid)

    @property
    def n(self) -> int:
        return self._required_int("syl_n", self._env.vars.syl_n)

    @property
    def i(self) -> int:
        return self._required_int("syl_i", self._env.vars.syl_i)

    @property
    def left(self) -> int:
        return self._required_int("syl_left", self._env.vars.syl_left)

    @property
    def center(self) -> int:
        return self._required_int("syl_center", self._env.vars.syl_center)

    @property
    def right(self) -> int:
        return self._required_int("syl_right", self._env.vars.syl_right)

    @property
    def width(self) -> int:
        return self._required_int("syl_width", self._env.vars.syl_width)

    @property
    def top(self) -> int:
        return self._required_int("syl_top", self._env.vars.syl_top)

    @property
    def middle(self) -> int:
        return self._required_int("syl_middle", self._env.vars.syl_middle)

    @property
    def bottom(self) -> int:
        return self._required_int("syl_bottom", self._env.vars.syl_bottom)

    @property
    def height(self) -> int:
        return self._required_int("syl_height", self._env.vars.syl_height)

    @property
    def x(self) -> int:
        return self._required_int("syl_x", self._env.vars.syl_x)

    @property
    def y(self) -> int:
        return self._required_int("syl_y", self._env.vars.syl_y)

    @property
    def tag(self) -> str:
        if self._env.syl is None:
            _raise_unavailable_attribute("tag")
        return _karaoke_tag_family(self._env.syl.tag)

    @property
    def inline_fx(self) -> str:
        if self._env.syl is None:
            _raise_unavailable_attribute("inline_fx")
        return self._env.syl.inline_fx

    @property
    def text(self) -> str:
        if self._env.syl is None:
            _raise_unavailable_attribute("text")
        return self._env.syl.text

    @property
    def trimmed_text(self) -> str:
        if self._env.syl is None:
            _raise_unavailable_attribute("trimmed_text")
        return self._env.syl.trimmed_text

    def _required_int(self, name: str, value: int | None) -> int:
        if value is None:
            _raise_unavailable_attribute(name)
        return value

    def _required_float(self, name: str, value: float | None) -> float:
        if value is None:
            _raise_unavailable_attribute(name)
        return value


class _ExpressionWordObject:
    """Public `word` object exposed to expression evaluation."""

    __slots__ = ("_env",)

    def __init__(self, env: Environment) -> None:
        self._env = env

    @property
    def start(self) -> int:
        return self._required_int("word_start", self._env.vars.word_start)

    @property
    def end(self) -> int:
        return self._required_int("word_end", self._env.vars.word_end)

    @property
    def dur(self) -> int:
        return self._required_int("word_dur", self._env.vars.word_dur)

    @property
    def kdur(self) -> float:
        return self._required_float("word_kdur", self._env.vars.word_kdur)

    @property
    def mid(self) -> float:
        return self._required_float("word_mid", self._env.vars.word_mid)

    @property
    def n(self) -> int:
        return self._required_int("word_n", self._env.vars.word_n)

    @property
    def i(self) -> int:
        return self._required_int("word_i", self._env.vars.word_i)

    @property
    def left(self) -> int:
        return self._required_int("word_left", self._env.vars.word_left)

    @property
    def center(self) -> int:
        return self._required_int("word_center", self._env.vars.word_center)

    @property
    def right(self) -> int:
        return self._required_int("word_right", self._env.vars.word_right)

    @property
    def width(self) -> int:
        return self._required_int("word_width", self._env.vars.word_width)

    @property
    def top(self) -> int:
        return self._required_int("word_top", self._env.vars.word_top)

    @property
    def middle(self) -> int:
        return self._required_int("word_middle", self._env.vars.word_middle)

    @property
    def bottom(self) -> int:
        return self._required_int("word_bottom", self._env.vars.word_bottom)

    @property
    def height(self) -> int:
        return self._required_int("word_height", self._env.vars.word_height)

    @property
    def x(self) -> int:
        return self._required_int("word_x", self._env.vars.word_x)

    @property
    def y(self) -> int:
        return self._required_int("word_y", self._env.vars.word_y)

    @property
    def text(self) -> str:
        if self._env.word is None:
            _raise_unavailable_attribute("text")
        return self._env.word.text

    @property
    def trimmed_text(self) -> str:
        if self._env.word is None:
            _raise_unavailable_attribute("trimmed_text")
        return self._env.word.trimmed_text

    def _required_int(self, name: str, value: int | None) -> int:
        if value is None:
            _raise_unavailable_attribute(name)
        return value

    def _required_float(self, name: str, value: float | None) -> float:
        if value is None:
            _raise_unavailable_attribute(name)
        return value


class _ExpressionCharObject:
    """Public `char` object exposed to expression evaluation."""

    __slots__ = ("_env",)

    def __init__(self, env: Environment) -> None:
        self._env = env

    @property
    def i(self) -> int:
        if self._env.char_index is None:
            _raise_unavailable_attribute("i")
        return self._env.char_index

    @property
    def n(self) -> int:
        if self._env.line_char_count is None:
            _raise_unavailable_attribute("n")
        return self._env.line_char_count

    @property
    def left(self) -> int:
        return self._required("char_left", self._env.vars.char_left)

    @property
    def center(self) -> int:
        return self._required("char_center", self._env.vars.char_center)

    @property
    def right(self) -> int:
        return self._required("char_right", self._env.vars.char_right)

    @property
    def width(self) -> int:
        return self._required("char_width", self._env.vars.char_width)

    @property
    def top(self) -> int:
        return self._required("char_top", self._env.vars.char_top)

    @property
    def middle(self) -> int:
        return self._required("char_middle", self._env.vars.char_middle)

    @property
    def bottom(self) -> int:
        return self._required("char_bottom", self._env.vars.char_bottom)

    @property
    def height(self) -> int:
        return self._required("char_height", self._env.vars.char_height)

    @property
    def x(self) -> int:
        return self._required("char_x", self._env.vars.char_x)

    @property
    def y(self) -> int:
        return self._required("char_y", self._env.vars.char_y)

    @property
    def text(self) -> str:
        if self._env.char is None:
            _raise_unavailable_attribute("text")
        return self._env.char.text

    @property
    def trimmed_text(self) -> str:
        if self._env.char is None:
            _raise_unavailable_attribute("trimmed_text")
        return self._env.char.trimmed_text

    def _required(self, name: str, value: int | None) -> int:
        if value is None:
            _raise_unavailable_attribute(name)
        return value


@dataclass(slots=True)
class Environment:
    """Closed execution environment for code and template expressions."""

    styles: dict[str, Style]
    declaration: str
    vars: VarContext = field(default_factory=VarContext)
    metadata: Metadata | None = None
    fbf_framerate: FrameRateSource | None = None
    source_line: Event | None = None
    karaoke: Karaoke | None = None
    line: GeneratedLine | None = None
    reference_style: Style | None = None
    word: Word | None = None
    syl: Syllable | None = None
    char: Syllable | None = None
    char_index: int | None = None
    line_char_count: int | None = None
    active_code_scope: Scope | None = None
    active_template_scope: Scope | None = None
    active_template_modifiers: TemplateModifiers | None = None
    rendering_mixin: bool = False
    active_line_syls: tuple[Syllable, ...] | None = None
    retime_used: bool = False
    retime_line_words: tuple[Word, ...] = ()
    retime_line_syls: tuple[Syllable, ...] = ()
    retime_line_chars: tuple[Syllable, ...] = ()
    retime_syl_chars: tuple[Syllable, ...] = ()
    store: dict[str, object] = field(default_factory=_empty_store)
    locked_store_keys: set[str] = field(
        default_factory=_empty_locked_store_keys
    )
    loop_stack: list[LoopState] = field(default_factory=_empty_loop_stack)
    rng: random.Random = field(default_factory=random.Random)
    random_namespace: _RandomNamespace | None = None
    user_namespace: dict[str, object] = field(
        default_factory=_empty_user_namespace
    )
    user_code_names: set[str] = field(default_factory=_empty_user_code_names)
    include_names: set[str] = field(default_factory=_empty_include_names)
    _function_namespace_cache: dict[str, dict[str, object]] = field(
        default_factory=_empty_function_namespace_cache
    )
    _expression_object_cache: dict[str, object] = field(
        default_factory=_empty_expression_object_cache
    )
    _exposed_module_cache: dict[str, object] = field(
        default_factory=_empty_exposed_module_cache
    )
    char_syllable_cache: dict[_CharSyllableCacheKey, tuple[Syllable, ...]] = (
        field(default_factory=_empty_char_syllable_cache)
    )

    def variable_dict(self) -> dict[str, object]:
        """Return variables available through `$name` lookups."""

        variables = dict(self.user_namespace)
        variables.update(self.vars.as_dict())
        if self.declaration == "template":
            variables.update(self._template_variables())
        variables.update(self._alias_variables())
        variables.update(self._loop_variables())
        return variables

    def begin_template_evaluation(
        self,
        scope: Scope,
        modifiers: TemplateModifiers,
    ) -> None:
        """Start one template body evaluation."""

        self.active_template_scope = scope
        self.active_template_modifiers = modifiers
        self.active_line_syls = None
        self.retime_used = False

    def as_dict(self) -> dict[str, object]:
        """Return the closed namespace exposed to execution."""

        namespace = dict(self.user_namespace)
        namespace.update(SAFE_BUILTINS)
        namespace.update(self._exposed_modules())
        self._merge_function_namespace(
            namespace,
            self._function_namespace(),
        )
        namespace.update(self._expression_objects())
        return namespace

    def reserved_names(self) -> frozenset[str]:
        """Return names that user code must not bind."""

        return _RESERVED_EXECUTION_NAMES

    def _function_namespace(self) -> dict[str, object]:
        mixin_key = "mixin" if self.rendering_mixin else "body"
        cache_key = (
            f"{self.declaration}:{self.active_code_scope or ''}:{mixin_key}"
        )
        cached = self._function_namespace_cache.get(cache_key)
        if cached is None:
            cached = FUNCTION_REGISTRY.build_namespace(self, self.declaration)
            self._function_namespace_cache[cache_key] = cached
        return cached

    def _exposed_modules(self) -> dict[str, object]:
        if "random" in EXPOSED_MODULES:
            if self.random_namespace is None:
                self.random_namespace = _RandomNamespace(self.rng)
            self._exposed_module_cache["random"] = self.random_namespace
        return self._exposed_module_cache

    def _merge_function_namespace(
        self,
        namespace: dict[str, object],
        functions: Mapping[str, object],
    ) -> None:
        for name, value in functions.items():
            existing = namespace.get(name)
            if isinstance(existing, SimpleNamespace) and isinstance(
                value,
                SimpleNamespace,
            ):
                for member_name, member_value in vars(value).items():
                    setattr(existing, member_name, member_value)
                continue
            namespace[name] = value

    def _template_variables(self) -> dict[str, object]:
        variables: dict[str, object] = {}
        if self.line is not None:
            variables["layer"] = self.line.layer
            variables["actor"] = self.line.actor
        return variables

    def _alias_variables(self) -> dict[str, object]:
        variables: dict[str, object] = {}
        expression_objects = self._expression_objects()
        for (
            object_name,
            property_name,
        ), spec in EXPRESSION_PROPERTY_SPECIFICATIONS.items():
            if spec.source_variable is None:
                continue
            expression_object = expression_objects.get(object_name)
            if expression_object is None:
                continue
            try:
                variables[spec.source_variable] = getattr(
                    expression_object,
                    property_name,
                )
            except ExecutionAttributeUnavailableError:
                continue
        return variables

    def _expression_objects(self) -> dict[str, object]:
        namespace: dict[str, object] = {"assets": assets}
        if self.vars.line_start is not None:
            namespace["line"] = self._expression_object("line")
        if self.vars.line_start is not None or self.reference_style is not None:
            namespace["style"] = self._expression_object("style")
        if self.vars.line_start is not None:
            if self.metadata is not None:
                namespace["metadata"] = self._expression_object("metadata")
        if self.vars.word_start is not None:
            namespace["word"] = self._expression_object("word")
        if self.vars.syl_start is not None:
            namespace["syl"] = self._expression_object("syl")
        if self.char is not None:
            namespace["char"] = self._expression_object("char")
        if self.loop_stack:
            namespace["loop"] = self._expression_object("loop")
        return namespace

    def _expression_object(self, name: str) -> object:
        cached = self._expression_object_cache.get(name)
        if cached is not None:
            return cached

        if name == "line":
            cached = _ExpressionLineObject(self)
        elif name == "style":
            cached = _ExpressionStyleObject(self)
        elif name == "metadata":
            cached = _ExpressionMetadataObject(self)
        elif name == "word":
            cached = _ExpressionWordObject(self)
        elif name == "syl":
            cached = _ExpressionSyllableObject(self)
        elif name == "char":
            cached = _ExpressionCharObject(self)
        elif name == "loop":
            cached = _ExpressionLoopObject(self)
        else:  # pragma: no cover - internal misuse guard
            raise KeyError(name)

        self._expression_object_cache[name] = cached
        return cached

    def push_loop_states(self, loop_states: list[LoopState]) -> None:
        """Append active loop states for the current render frame."""

        self.loop_stack.extend(loop_states)

    def pop_loop_states(self, count: int) -> None:
        """Remove active loop states previously pushed for one frame."""

        if count:
            del self.loop_stack[-count:]

    def _loop_variables(self) -> dict[str, object]:
        variables: dict[str, object] = {}
        for loop_state in self.loop_stack:
            variables[f"loop_{loop_state.name}_i"] = loop_state.index
            variables[f"loop_{loop_state.name}_n"] = loop_state.total

        if len(self.loop_stack) == 1:
            only_loop = self.loop_stack[0]
            variables["loop_i"] = only_loop.index
            variables["loop_n"] = only_loop.total

        return variables
