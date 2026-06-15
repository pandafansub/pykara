"""Unit tests for engine namespace functions."""

# pyright: reportPrivateUsage=false

from __future__ import annotations

import math
import random
from collections.abc import Callable
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import ClassVar, cast

import pytest

from pykara.data import Style
from pykara.declaration import Scope
from pykara.engine.functions import (
    FUNCTION_REGISTRY,
    AssAlphaFunction,
    AssColorFunction,
    CircularSpreadFunction,
    FunctionRegistry,
    GetFunction,
    GetStyleFunction,
    HslToRgbFunction,
    HsvToRgbFunction,
    InterpolateColorFunction,
    LayerSetFunction,
    LockFunction,
    PolarFunction,
    PutFunction,
    RandomSpreadFunction,
    RetimeFunction,
    ShapeCenterAtFunction,
    ShapeDisplaceFunction,
    ShapeRotateFunction,
    ShapeSplitClipFunction,
    StyleInfo,
)
from pykara.engine.functions.retime import (
    _implicit_collection,
    _RetimeEnvironment,
    _validate_target_scope,
)
from pykara.errors import (
    EngineError,
    LockedStoreKeyError,
    UnknownStyleLookupError,
)


@dataclass(slots=True)
class DummyTimedLine:
    start_time: int
    end_time: int


@dataclass(slots=True)
class DummySyllable:
    start_time: int
    end_time: int
    duration: int
    index: int = 0
    center: float = 0.0
    x: float = 0.0


@dataclass(slots=True)
class DummyGeneratedLine:
    start_time: int = 0
    end_time: int = 0
    duration: int = 0
    layer: int = 0
    style: str = "Default"
    styleref: Style | None = None


@dataclass(slots=True)
class DummyEnvironment:
    source_line: DummyTimedLine = field(
        default_factory=lambda: DummyTimedLine(start_time=1000, end_time=5000)
    )
    line: DummyGeneratedLine = field(default_factory=DummyGeneratedLine)
    syl: DummySyllable | None = field(
        default_factory=lambda: DummySyllable(
            start_time=500,
            end_time=900,
            duration=400,
        )
    )
    word: DummySyllable | None = None
    char: DummySyllable | None = None
    char_index: int | None = None
    line_char_count: int | None = None
    active_template_scope: Scope | None = Scope.SYL
    retime_used: bool = False
    retime_line_words: tuple[DummySyllable, ...] = ()
    retime_line_syls: tuple[DummySyllable, ...] = field(
        default_factory=lambda: (
            DummySyllable(
                start_time=500,
                end_time=900,
                duration=400,
                index=0,
                center=10.0,
                x=10.0,
            ),
            DummySyllable(
                start_time=1000,
                end_time=1300,
                duration=300,
                index=1,
                center=30.0,
                x=30.0,
            ),
        )
    )
    retime_line_chars: tuple[DummySyllable, ...] = ()
    retime_syl_chars: tuple[DummySyllable, ...] = ()
    styles: dict[str, Style] = field(default_factory=lambda: _empty_styles())
    store: dict[str, object] = field(default_factory=lambda: _empty_store())
    locked_store_keys: set[str] = field(
        default_factory=lambda: _empty_locked_store_keys()
    )
    rng: random.Random = field(default_factory=lambda: random.Random(1))  # noqa: S311


def _empty_styles() -> dict[str, Style]:
    return {}


def _empty_store() -> dict[str, object]:
    return {}


def _empty_locked_store_keys() -> set[str]:
    return set()


def as_retime_env(env: DummyEnvironment) -> _RetimeEnvironment:
    return cast(_RetimeEnvironment, env)


def make_style(name: str = "Default") -> Style:
    return Style(
        name=name,
        fontname="Arial",
        fontsize=36.0,
        primary_colour="&H00FFFFFF",
        secondary_colour="&H000000FF",
        outline_colour="&H00000000",
        back_colour="&H00000000",
        bold=False,
        italic=False,
        underline=False,
        strike_out=False,
        scale_x=100.0,
        scale_y=100.0,
        spacing=0.0,
        angle=0.0,
        border_style=1,
        outline=2.0,
        shadow=0.0,
        alignment=2,
        margin_l=10,
        margin_r=10,
        margin_t=10,
        margin_b=10,
        encoding=1,
    )


def make_retime_elements() -> tuple[DummySyllable, ...]:
    return (
        DummySyllable(
            start_time=500,
            end_time=900,
            duration=400,
            index=0,
            center=10.0,
            x=10.0,
        ),
        DummySyllable(
            start_time=1000,
            end_time=1300,
            duration=300,
            index=1,
            center=30.0,
            x=30.0,
        ),
        DummySyllable(
            start_time=1600,
            end_time=1900,
            duration=300,
            index=2,
            center=50.0,
            x=50.0,
        ),
    )


class TestRetimeFunction:
    @pytest.mark.parametrize(
        ("target", "start_offset", "end_offset", "expected"),
        [
            ("syl", 10, 20, (1510, 1920)),
            ("presyl", 10, 20, (1510, 1520)),
            ("postsyl", 10, 20, (1910, 1920)),
            ("line", 10, 20, (1010, 5020)),
            ("preline", 10, 20, (1010, 1020)),
            ("postline", 10, 20, (5010, 5020)),
            ("start2syl", 10, 20, (1010, 1520)),
            ("syl2end", 10, 20, (1910, 5020)),
        ],
    )
    def test_applies_target_and_updates_duration(
        self,
        target: str,
        start_offset: int,
        end_offset: int,
        expected: tuple[int, int],
    ) -> None:
        env = DummyEnvironment()

        retime = RetimeFunction().build_bound(env)
        result = getattr(retime, target)(start_offset, end_offset)

        assert result is None
        assert (env.line.start_time, env.line.end_time) == expected
        assert env.line.duration == expected[1] - expected[0]

    def test_direct_call_is_not_supported(self) -> None:
        with pytest.raises(EngineError):
            RetimeFunction()(DummyEnvironment(), "syl")

    def test_rejects_second_retime_call_in_same_evaluation(self) -> None:
        env = DummyEnvironment()
        retime = RetimeFunction().build_bound(env)

        retime.line()

        with pytest.raises(EngineError):
            retime.syl()

    def test_rejects_syllable_target_in_line_scope(self) -> None:
        env = DummyEnvironment(active_template_scope=Scope.LINE)
        retime = RetimeFunction().build_bound(env)

        with pytest.raises(EngineError):
            retime.syl()

    def test_applies_line_preset_to_syllable_collection(self) -> None:
        env = DummyEnvironment(
            syl=DummySyllable(
                start_time=500,
                end_time=900,
                duration=400,
                index=1,
                center=30.0,
                x=30.0,
            )
        )
        retime = RetimeFunction().build_bound(env)

        retime.line.ltr(-300, 200)

        assert (env.line.start_time, env.line.end_time) == (1000, 5200)

    @pytest.mark.parametrize(
        ("preset", "factor"),
        [
            ("rtl", 0.5),
            ("from_center", 0.0),
            ("from_edges", 1.0),
            ("odd_first", 1.0),
            ("even_first", 0.0),
            ("spatial_ltr", 0.5),
            ("spatial_rtl", 0.5),
            ("random", abs(math.sin(2 * 127.1 + 311.7))),
        ],
    )
    def test_applies_line_preset_factor_variants(
        self,
        preset: str,
        factor: float,
    ) -> None:
        env = DummyEnvironment(
            syl=DummySyllable(
                start_time=1000,
                end_time=1300,
                duration=300,
                index=1,
                center=30.0,
                x=30.0,
            ),
            retime_line_syls=make_retime_elements(),
        )
        retime = RetimeFunction().build_bound(env)

        getattr(retime.line, preset)(-300, 200)

        expected_start = 1000 + round(-300 * (1 - factor))
        expected_end = 5000 + round(200 * factor)
        assert env.line is not None
        assert (env.line.start_time, env.line.end_time) == (
            expected_start,
            expected_end,
        )

    def test_applies_line_preset_to_word_collection(self) -> None:
        words = make_retime_elements()
        env = DummyEnvironment(
            active_template_scope=Scope.WORD,
            word=words[2],
            retime_line_words=words,
        )
        retime = RetimeFunction().build_bound(env)

        retime.line.ltr(-300, 200)

        assert env.line is not None
        assert (env.line.start_time, env.line.end_time) == (1000, 5200)

    def test_applies_line_preset_to_line_char_collection(self) -> None:
        chars = make_retime_elements()
        env = DummyEnvironment(
            active_template_scope=Scope.CHAR,
            char_index=1,
            retime_line_chars=chars,
        )
        retime = RetimeFunction().build_bound(env)

        retime.line.ltr(-300, 200)

        assert env.line is not None
        assert (env.line.start_time, env.line.end_time) == (850, 5100)

    def test_applies_syllable_preset_to_syllable_char_collection(self) -> None:
        chars = make_retime_elements()
        env = DummyEnvironment(
            active_template_scope=Scope.CHAR,
            syl=DummySyllable(
                start_time=500,
                end_time=900,
                duration=400,
            ),
            char=chars[1],
            retime_syl_chars=chars,
        )
        retime = RetimeFunction().build_bound(env)

        retime.syl.ltr(-300, 200)

        assert env.line is not None
        assert (env.line.start_time, env.line.end_time) == (1350, 2000)

    def test_applies_start_to_syllable_preset_to_syllable_collection(
        self,
    ) -> None:
        syllables = make_retime_elements()
        env = DummyEnvironment(
            syl=syllables[1],
            retime_line_syls=syllables,
        )
        retime = RetimeFunction().build_bound(env)

        retime.start2syl.ltr(-300, 200)

        assert env.line is not None
        assert (env.line.start_time, env.line.end_time) == (850, 2100)

    def test_applies_start_to_syllable_preset_to_char_collection(
        self,
    ) -> None:
        chars = make_retime_elements()
        env = DummyEnvironment(
            active_template_scope=Scope.CHAR,
            char=chars[1],
            char_index=1,
            retime_line_chars=chars,
        )
        retime = RetimeFunction().build_bound(env)

        retime.start2syl.ltr(-300, 200)

        assert env.line is not None
        assert (env.line.start_time, env.line.end_time) == (850, 1600)

    def test_applies_syllable_to_end_preset_to_char_collection(
        self,
    ) -> None:
        chars = make_retime_elements()
        env = DummyEnvironment(
            active_template_scope=Scope.CHAR,
            char=chars[1],
            char_index=1,
            retime_line_chars=chars,
        )
        retime = RetimeFunction().build_bound(env)

        retime.syl2end.ltr(-300, 200)

        assert env.line is not None
        assert (env.line.start_time, env.line.end_time) == (1750, 5100)

    def test_unknown_preset_attribute_raises_attribute_error(self) -> None:
        retime = RetimeFunction().build_bound(DummyEnvironment())

        with pytest.raises(AttributeError, match="missing"):
            _ = retime.line.missing

    def test_rejects_retime_without_template_scope(self) -> None:
        env = DummyEnvironment(active_template_scope=None)
        retime = RetimeFunction().build_bound(env)

        with pytest.raises(EngineError, match="only valid"):
            retime.line()

    def test_rejects_retime_without_source_line(self) -> None:
        env = DummyEnvironment(source_line=cast(DummyTimedLine, None))
        retime = RetimeFunction().build_bound(env)

        with pytest.raises(EngineError, match="line context"):
            retime.line()

    def test_rejects_retime_without_output_line(self) -> None:
        env = DummyEnvironment(line=cast(DummyGeneratedLine, None))
        retime = RetimeFunction().build_bound(env)

        with pytest.raises(EngineError, match="active generated line"):
            retime.line()

    def test_rejects_retime_without_syllable_context(self) -> None:
        env = DummyEnvironment(syl=None)
        retime = RetimeFunction().build_bound(env)

        with pytest.raises(EngineError, match="requires syllable context"):
            retime.syl()

    def test_rejects_line_preset_in_line_scope(self) -> None:
        env = DummyEnvironment(active_template_scope=Scope.LINE)
        retime = RetimeFunction().build_bound(env)

        with pytest.raises(EngineError, match="invalid in line"):
            retime.line.ltr()

    def test_rejects_syllable_preset_outside_char_scope(self) -> None:
        env = DummyEnvironment(active_template_scope=Scope.SYL)
        retime = RetimeFunction().build_bound(env)

        with pytest.raises(EngineError, match="invalid in syl"):
            retime.syl.ltr()

    def test_rejects_start_to_syllable_preset_outside_syllable_or_char_scope(
        self,
    ) -> None:
        env = DummyEnvironment(active_template_scope=Scope.WORD)
        retime = RetimeFunction().build_bound(env)

        with pytest.raises(EngineError, match="invalid in word"):
            retime.start2syl.ltr()

    def test_rejects_line_preset_without_char_index(self) -> None:
        env = DummyEnvironment(active_template_scope=Scope.CHAR)
        retime = RetimeFunction().build_bound(env)

        with pytest.raises(EngineError, match="requires char context"):
            retime.line.ltr()

    def test_rejects_syllable_preset_without_char_context(self) -> None:
        env = DummyEnvironment(
            active_template_scope=Scope.CHAR,
            retime_syl_chars=make_retime_elements(),
        )
        retime = RetimeFunction().build_bound(env)

        with pytest.raises(EngineError, match="requires char context"):
            retime.syl.ltr()

    def test_rejects_spatial_preset_without_distinct_x_positions(self) -> None:
        env = DummyEnvironment(
            syl=DummySyllable(
                start_time=1000,
                end_time=1300,
                duration=300,
                index=1,
                x=10.0,
            ),
            retime_line_syls=(
                DummySyllable(0, 100, 100, index=0, x=10.0),
                DummySyllable(100, 200, 100, index=1, x=10.0),
            ),
        )
        retime = RetimeFunction().build_bound(env)

        with pytest.raises(EngineError, match="distinct x positions"):
            retime.line.spatial_ltr()

    def test_rejects_degenerate_preset_collection(self) -> None:
        env = DummyEnvironment(retime_line_syls=(DummySyllable(0, 100, 100),))
        retime = RetimeFunction().build_bound(env)

        with pytest.raises(EngineError):
            retime.line.ltr(-300, 0)

    def test_rejects_unknown_target_in_scope_validation(self) -> None:
        env = DummyEnvironment()

        with pytest.raises(EngineError, match="unknown retime target"):
            _validate_target_scope(as_retime_env(env), "missing", preset=None)

    def test_rejects_unknown_preset_in_scope_validation(self) -> None:
        env = DummyEnvironment()

        with pytest.raises(EngineError, match="unknown retime preset"):
            _validate_target_scope(as_retime_env(env), "line", preset="missing")

    def test_rejects_syllable_target_without_preset_in_word_scope(self) -> None:
        env = DummyEnvironment(active_template_scope=Scope.WORD)
        retime = RetimeFunction().build_bound(env)

        with pytest.raises(
            EngineError,
            match=r"retime\.syl is invalid in word",
        ):
            retime.syl()

    def test_rejects_line_target_in_setup_scope(self) -> None:
        env = DummyEnvironment(active_template_scope=Scope.SETUP)
        retime = RetimeFunction().build_bound(env)

        with pytest.raises(
            EngineError,
            match=r"retime\.line is invalid in setup",
        ):
            retime.line()

    def test_rejects_preset_without_implicit_collection(self) -> None:
        env = DummyEnvironment(active_template_scope=Scope.WORD)

        with pytest.raises(
            EngineError,
            match=r"retime\.start2syl has no preset collection here",
        ):
            _implicit_collection(as_retime_env(env), "start2syl")


class TestLayerSetFunction:
    def test_sets_layer(self) -> None:
        env = DummyEnvironment()

        result = LayerSetFunction()(env, 7)

        assert result is None
        assert env.line.layer == 7


class TestStoreFunctions:
    def test_get_returns_default(self) -> None:
        env = DummyEnvironment()

        result = GetFunction()(env, "missing", "fallback")

        assert result == "fallback"

    def test_put_stores_and_returns_value(self) -> None:
        env = DummyEnvironment()

        result = PutFunction()(env, "color", "blue")

        assert result == "blue"
        assert env.store["color"] == "blue"

    def test_lock_stores_locks_and_returns_value(self) -> None:
        env = DummyEnvironment()

        result = LockFunction()(env, "color", "blue")

        assert result == "blue"
        assert env.store["color"] == "blue"
        assert env.locked_store_keys == {"color"}

    def test_lock_keeps_first_locked_value(self) -> None:
        env = DummyEnvironment()

        first = LockFunction()(env, "color", "blue")
        second = LockFunction()(env, "color", "red")

        assert first == "blue"
        assert second == "blue"
        assert env.store["color"] == "blue"

    def test_lock_can_lock_existing_store_value(self) -> None:
        env = DummyEnvironment()
        env.store["color"] = "blue"

        result = LockFunction()(env, "color", "red")

        assert result == "blue"
        assert env.store["color"] == "blue"
        assert env.locked_store_keys == {"color"}

    def test_put_rejects_locked_key(self) -> None:
        env = DummyEnvironment()
        LockFunction()(env, "color", "blue")

        with pytest.raises(LockedStoreKeyError):
            PutFunction()(env, "color", "red")


class TestColorFunctions:
    def test_ass_color_formats_ass_string(self) -> None:
        result = AssColorFunction()(object(), 255, 128, 0)

        assert result == "&H0080FF&"

    def test_ass_alpha_formats_ass_string(self) -> None:
        result = AssAlphaFunction()(object(), 255)

        assert result == "&HFF&"

    def test_interpolate_color_supports_style_and_override_formats(
        self,
    ) -> None:
        result = InterpolateColorFunction()(
            object(),
            0.5,
            "&H00000000",
            "&HFFFFFF&",
        )

        assert result == "&H808080&"

    @pytest.mark.parametrize(
        ("hue", "saturation", "value", "expected"),
        [
            (0, 1, 1, (255.0, 0.0, 0.0)),
            (60, 1, 1, (255.0, 255.0, 0.0)),
            (180, 1, 0.5, (0.0, 127.5, 127.5)),
            (-300, 1, 1, (255.0, 0.0, 255.0)),
            (120, 0, 2, (255, 255, 255)),
        ],
    )
    def test_hsv_to_rgb_matches_aegisub_util(
        self,
        hue: float,
        saturation: float,
        value: float,
        expected: tuple[float, float, float],
    ) -> None:
        assert HsvToRgbFunction()(object(), hue, saturation, value) == expected

    @pytest.mark.parametrize(
        ("hue", "saturation", "luminance", "expected"),
        [
            (0, 1, 0.5, (255, 0, 0)),
            (120, 1, 0.5, (0, 255, 0)),
            (240, 1, 0.5, (0, 0, 255)),
            (-60, 1, 0.25, (127, 128, 0)),
            (180, 0, 2, (255, 255, 255)),
        ],
    )
    def test_hsl_to_rgb_matches_aegisub_util(
        self,
        hue: float,
        saturation: float,
        luminance: float,
        expected: tuple[int, int, int],
    ) -> None:
        assert (
            HslToRgbFunction()(object(), hue, saturation, luminance) == expected
        )


class TestGeometryFunctions:
    def test_polar_uses_screen_space_y_axis(self) -> None:
        polar = PolarFunction()

        assert polar(object(), 0, 30, "x") == 30
        assert polar(object(), 90, 30, "y") == -30
        assert polar(object(), 180, 30) == (-30, -0.0)

    def test_circular_spread_returns_unit_points_in_spread_order(self) -> None:
        spread = CircularSpreadFunction()
        env = DummyEnvironment(rng=random.Random(1))  # noqa: S311

        assert spread(env, 6) == [
            (0.0, 1.0),
            (0.0, -1.0),
            (0.866, 0.5),
            (-0.866, -0.5),
            (0.866, -0.5),
            (-0.866, 0.5),
        ]

    def test_circular_spread_supports_position_rotation(self) -> None:
        spread = CircularSpreadFunction()
        env = DummyEnvironment(rng=random.Random(1))  # noqa: S311

        assert spread(env, 4, rotate=1) == [
            (-1.0, 0.0),
            (1.0, 0.0),
            (0.0, 1.0),
            (0.0, -1.0),
        ]

    def test_circular_spread_requires_at_least_two_points(self) -> None:
        spread = CircularSpreadFunction()
        env = DummyEnvironment(rng=random.Random(1))  # noqa: S311

        with pytest.raises(ValueError, match="n must be >= 2"):
            spread(env, 1)

    def test_random_spread_returns_points_with_spacing_constraints(
        self,
    ) -> None:
        random_spread = RandomSpreadFunction()
        env = DummyEnvironment(rng=random.Random(1))  # noqa: S311

        points = random_spread(env, 6, spread=30, min_dist=14, min_radius=8)

        assert points == [
            (-22, 6),
            (24, 21),
            (18, -26),
            (-14, -23),
            (1, 18),
            (11, -6),
        ]
        assert all(math.hypot(x, y) >= 8 for x, y in points)
        assert all(
            math.hypot(x - other_x, y - other_y) >= 14
            for index, (x, y) in enumerate(points)
            for other_x, other_y in points[index + 1 :]
        )

    def test_random_spread_reports_impossible_constraints(self) -> None:
        random_spread = RandomSpreadFunction()
        env = DummyEnvironment(rng=random.Random(1))  # noqa: S311

        with pytest.raises(ValueError, match="could not place enough points"):
            random_spread(
                env,
                2,
                spread=0,
                min_dist=1,
                min_radius=0,
                attempts=5,
            )

    def test_shape_rotate_center_at_and_displace(self) -> None:
        shape = "m 0 0 l 10 0 l 10 20"

        rotated = ShapeRotateFunction()(object(), shape, 90)
        centered = ShapeCenterAtFunction()(object(), rotated)
        displaced = ShapeDisplaceFunction()(object(), centered, 50, 60)

        assert rotated == "m 0 0 l 0 -10 l 20 -10"
        assert centered == "m -10 5 l -10 -5 l 10 -5"
        assert displaced == "m 40 65 l 40 55 l 60 55"

    def test_shape_split_clip_builds_centered_split_clip(self) -> None:
        result = ShapeSplitClipFunction()(object(), 20, 0, 50, 60)

        assert result == "m 40 60 l 60 60 l 60 50 l 40 50 m 40 70 l 60 70"


class CodeOnlyFunction:
    name: ClassVar[str] = "code_only"
    aliases: ClassVar[tuple[str, ...]] = ("code_alias",)
    applicable_to: ClassVar[frozenset[str]] = frozenset({"code"})

    def __call__(self, env: object, value: str) -> str:
        del env
        return value.upper()


class TestFunctionRegistry:
    def test_build_namespace_binds_environment(self) -> None:
        env = DummyEnvironment()
        registry = FunctionRegistry()
        registry.register(LayerSetFunction())

        namespace = registry.build_namespace(env, "template")
        assert isinstance(namespace["layer"], SimpleNamespace)
        layer_set = cast(Callable[[int], object], namespace["layer"].set)
        assert isinstance(layer_set, Callable)
        result = layer_set(4)

        assert result is None
        assert env.line.layer == 4

    def test_filters_by_declaration(self) -> None:
        registry = FunctionRegistry()
        registry.register(CodeOnlyFunction())

        template_namespace = registry.build_namespace(object(), "template")
        code_namespace = registry.build_namespace(object(), "code")

        assert "code_only" not in template_namespace
        assert "code_alias" not in template_namespace
        code_only = code_namespace["code_only"]
        code_alias = code_namespace["code_alias"]
        assert isinstance(code_only, Callable)
        assert isinstance(code_alias, Callable)
        assert code_only("hello") == "HELLO"
        assert code_alias("world") == "WORLD"

    def test_build_namespace_groups_dotted_functions(self) -> None:
        registry = FunctionRegistry()
        registry.register(PolarFunction())

        namespace = registry.build_namespace(object(), "template")

        assert "coord.polar" not in namespace
        assert isinstance(namespace["coord"], SimpleNamespace)
        assert namespace["coord"].polar(0, 30, "x") == 30


class TestGetStyleFunction:
    def test_returns_style_information(self) -> None:
        env = DummyEnvironment(styles={"My Style": make_style("My Style")})
        function = GetStyleFunction()

        result = function(env, "My Style")

        assert isinstance(result, StyleInfo)
        assert result.name == "My Style"
        assert result.font_name == "Arial"
        assert result.font_size == 36.0
        assert result.primary_color == "&HFFFFFF&"
        assert result.secondary_color == "&H0000FF&"
        assert result.outline_color == "&H000000&"
        assert result.shadow_color == "&H000000&"
        assert result.outline == 2.0
        assert result.margin_t == 10

    def test_raises_for_unknown_style(self) -> None:
        env = DummyEnvironment(styles={"Default": make_style()})
        function = GetStyleFunction()

        with pytest.raises(UnknownStyleLookupError, match="Missing"):
            function(env, "Missing")


class TestDefaultRegistry:
    def test_default_registry_exposes_core_functions(self) -> None:
        env = DummyEnvironment()
        namespace = FUNCTION_REGISTRY.build_namespace(env, "template")

        assert "retime" in namespace
        assert "motion" in namespace
        assert "gradient" in namespace
        assert isinstance(namespace["layer"], SimpleNamespace)
        assert "get" in namespace
        assert "put" in namespace
        assert "set" not in namespace
        assert "lock" in namespace
        assert "get_style" in namespace
        assert isinstance(namespace["color"], SimpleNamespace)
        assert isinstance(namespace["coord"], SimpleNamespace)
        assert isinstance(namespace["shape"], SimpleNamespace)
        put = cast(Callable[[str, object], object], namespace["put"])
        assert put("color", "blue") == "blue"
        assert env.store["color"] == "blue"
        assert namespace["color"].rgb_to_ass(255, 128, 0) == "&H0080FF&"
        assert (
            namespace["color"].rgb_to_ass(red=255, green=128, blue=0)
            == "&H0080FF&"
        )
        assert namespace["layer"].set(3) is None
        assert env.line.layer == 3
        assert namespace["color"].alpha(255) == "&HFF&"
        assert namespace["color"].alpha(alpha=255) == "&HFF&"
        assert (
            namespace["color"].interpolate(
                0.5,
                "&H00000000",
                "&HFFFFFF&",
            )
            == "&H808080&"
        )
        assert (
            namespace["color"].interpolate(
                progress=0.5,
                start_color="&H00000000",
                end_color="&HFFFFFF&",
            )
            == "&H808080&"
        )
        assert namespace["color"].hsv_to_rgb(0, 1, 1) == (255.0, 0.0, 0.0)
        assert namespace["color"].HSV_to_RGB(0, 1, 1) == (255.0, 0.0, 0.0)
        assert namespace["color"].hsl_to_rgb(120, 1, 0.5) == (0, 255, 0)
        assert namespace["color"].HSL_to_RGB(120, 1, 0.5) == (0, 255, 0)
        assert namespace["coord"].polar(0, 30, "x") == 30
        assert namespace["coord"].circular_spread(4) == [
            (0.0, 1.0),
            (0.0, -1.0),
            (1.0, 0.0),
            (-1.0, -0.0),
        ]
        assert namespace["coord"].random_spread(1) == [(-23, 1)]
        assert namespace["shape"].rotate("m 0 0 l 10 0", 90) == (
            "m 0 0 l 0 -10"
        )
        assert namespace["shape"].center_at("m 0 0 l 10 0") == ("m -5 0 l 5 0")
        assert namespace["shape"].displace("m 0 0", 1, 2) == "m 1 2"
        assert namespace["shape"].split_clip(20, 0, 50, 60) == (
            "m 40 60 l 60 60 l 60 50 l 40 50 m 40 70 l 60 70"
        )

    def test_default_registry_exposes_get_style_to_code(
        self,
    ) -> None:
        env = DummyEnvironment(styles={"Default": make_style()})
        namespace = FUNCTION_REGISTRY.build_namespace(env, "code")

        assert "get" not in namespace
        assert "put" not in namespace
        assert "lock" not in namespace
        assert "get_style" in namespace
        get_style = cast(Callable[[str], StyleInfo], namespace["get_style"])
        assert get_style("Default").name == "Default"
