"""Tests for expression-facing variable context objects."""

# pyright: reportPrivateUsage=false

from __future__ import annotations

import pytest

from pykara.data import Event, Metadata, Style
from pykara.data.events.karaoke import Karaoke
from pykara.data.events.karaoke.syllable import Syllable, Word
from pykara.engine.variable_context import (
    Environment,
    GeneratedLine,
    VarContext,
    _ExpressionCharObject,
    _ExpressionLineObject,
    _ExpressionMetadataObject,
    _ExpressionStyleObject,
    _ExpressionSyllableObject,
    _ExpressionWordObject,
    _raise_unavailable_attribute,
)
from pykara.errors import ExecutionAttributeUnavailableError


def make_style(name: str = "Default") -> Style:
    return Style(
        name=name,
        fontname="Arial",
        fontsize=40.0,
        primary_colour="&H00FFFFFF",
        secondary_colour="&H0000FFFF",
        outline_colour="&H00112233",
        back_colour="&H64000000",
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
        shadow=1.0,
        alignment=2,
        margin_l=10,
        margin_r=10,
        margin_t=10,
        margin_b=10,
        encoding=1,
    )


def make_event() -> Event:
    return Event(
        text="hello",
        effect="karaoke",
        style="Default",
        layer=3,
        start_time=1000,
        end_time=4000,
        comment=False,
        actor="singer",
        margin_l=0,
        margin_r=0,
        margin_t=0,
        margin_b=0,
    )


def make_syllable(index: int = 0, text: str = "hi") -> Syllable:
    return Syllable(
        index=index,
        raw_text=text,
        text=text,
        trimmed_text=text,
        prespace="",
        postspace="",
        start_time=0,
        end_time=400,
        duration=400,
        kdur=40.0,
        tag=r"\k",
        inline_fx="sparkle",
        highlights=[],
        left=1.0,
        center=10.0,
        right=20.0,
        width=19.0,
        top=5.0,
        middle=15.0,
        bottom=25.0,
        height=20.0,
        x=11.0,
        y=16.0,
    )


def make_word() -> Word:
    syllable = make_syllable(0, "hi")
    return Word(
        index=0,
        syllables=(syllable,),
        raw_text="hi",
        text="hi",
        trimmed_text="hi",
        prespace="",
        postspace="",
        start_time=0,
        end_time=400,
        duration=400,
        kdur=40.0,
        style=make_style(),
        left=1.0,
        center=10.0,
        right=20.0,
        width=19.0,
        top=5.0,
        middle=15.0,
        bottom=25.0,
        height=20.0,
        x=11.0,
        y=16.0,
    )


def make_populated_environment() -> Environment:
    styles = {"Default": make_style()}
    event = make_event()
    karaoke = Karaoke(
        syllables=[make_syllable(0, "hi"), make_syllable(1, "yo")],
        text="hi yo",
        trimmed_text="hi yo",
    )
    env = Environment(
        styles=styles,
        declaration="template",
        metadata=Metadata(res_x=1920, res_y=1080),
        source_line=event,
        karaoke=karaoke,
        line=GeneratedLine.from_event(event, styles["Default"]),
    )
    env.vars.set_line(
        index=0,
        start_time=event.start_time,
        end_time=event.end_time,
        width=100.0,
        height=25.0,
        left=5.0,
        center=55.0,
        right=105.0,
        top=10.0,
        middle=22.0,
        bottom=35.0,
        x=50.0,
        y=30.0,
        syllable_count=len(karaoke.syllables),
        word_count=1,
    )
    word = make_word()
    env.vars.set_word(word)
    first_syl = karaoke.syllables[0]
    env.vars.set_syl(first_syl)
    env.vars.set_char(first_syl, char_count=2, char_index=0)
    env.word = word
    env.syl = first_syl
    env.char = first_syl
    env.char_index = 0
    env.line_char_count = 2
    return env


class TestRaiseUnavailableAttribute:
    def test_raises_execution_attribute_unavailable_error(self) -> None:
        with pytest.raises(ExecutionAttributeUnavailableError):
            _raise_unavailable_attribute("line_mid")


class TestVarContext:
    def test_snapshot_and_restore_word_scope_round_trips_nested_state(
        self,
    ) -> None:
        context = VarContext()
        context.set_line(
            index=0,
            start_time=1000,
            end_time=4000,
            width=100.0,
            height=25.0,
            left=5.0,
            center=55.0,
            right=105.0,
            top=10.0,
            middle=22.0,
            bottom=35.0,
            x=50.0,
            y=30.0,
            syllable_count=2,
            word_count=1,
        )
        word = make_word()
        syllable = make_syllable()
        context.set_word(word)
        context.set_syl(syllable)
        context.set_char(syllable, char_count=2, char_index=1)

        snapshot = context.snapshot_word_scope()

        context.clear_word()
        context.restore_word_scope(snapshot)

        assert context.word_start == word.start_time
        assert context.word_n == 1
        assert context.word_right == 20
        assert context.syl_start == syllable.start_time
        assert context.syl_n == 2
        assert context.syl_middle == 15
        assert context.char_i == 1
        assert context.char_n == 2
        assert context.char_y == 16


class TestExpressionStyleObject:
    def test_reads_style_properties_from_generated_line(self) -> None:
        env = make_populated_environment()
        style_object = _ExpressionStyleObject(env)

        assert style_object.name == "Default"
        assert style_object.primary_color == "&H00FFFFFF"
        assert style_object.secondary_color == "&H0000FFFF"
        assert style_object.outline_color == "&H00112233"
        assert style_object.shadow_color == "&H64000000"
        assert style_object.outline == 2.0

    def test_reads_style_via_source_line_when_no_generated_line(
        self,
    ) -> None:
        env = make_populated_environment()
        env.line = None
        style_object = _ExpressionStyleObject(env)

        assert style_object.primary_color == "&H00FFFFFF"

    def test_raises_when_no_style_context_is_available(self) -> None:
        env = Environment(
            styles={"Default": make_style()},
            declaration="template",
        )
        style_object = _ExpressionStyleObject(env)

        with pytest.raises(ExecutionAttributeUnavailableError):
            _ = style_object.primary_color


class TestExpressionMetadataObject:
    def test_reads_metadata_resolution(self) -> None:
        env = make_populated_environment()
        metadata_object = _ExpressionMetadataObject(env)

        assert metadata_object.res_x == 1920
        assert metadata_object.res_y == 1080

    def test_raises_when_metadata_is_missing(self) -> None:
        env = make_populated_environment()
        env.metadata = None
        metadata_object = _ExpressionMetadataObject(env)

        with pytest.raises(ExecutionAttributeUnavailableError):
            _ = metadata_object.res_x


class TestExpressionLineObject:
    def test_reads_populated_line_attributes(self) -> None:
        env = make_populated_environment()
        line_object = _ExpressionLineObject(env)

        assert line_object.layer == 3
        assert line_object.actor == "singer"
        assert line_object.raw_text == "hello"
        assert line_object.text == "hi yo"
        assert line_object.trimmed_text == "hi yo"
        assert line_object.start == 1000
        assert line_object.end == 4000
        assert line_object.dur == 3000
        assert line_object.mid == 1000 + 3000 / 2
        assert line_object.i == 0
        assert line_object.left == 5
        assert line_object.center == 55
        assert line_object.right == 105
        assert line_object.width == 100
        assert line_object.top == 10
        assert line_object.middle == 22
        assert line_object.bottom == 35
        assert line_object.height == 25
        assert line_object.x == 50
        assert line_object.y == 30
        assert len(line_object.syls) == 2

    def test_falls_back_to_vars_when_generated_line_missing(self) -> None:
        env = make_populated_environment()
        env.line = None
        line_object = _ExpressionLineObject(env)

        assert line_object.start == 1000
        assert line_object.end == 4000
        assert line_object.dur == 3000
        assert line_object.layer == 3
        assert line_object.actor == "singer"

    def test_raises_when_no_context_for_layer_actor_and_times(self) -> None:
        env = Environment(
            styles={"Default": make_style()},
            declaration="template",
        )
        line_object = _ExpressionLineObject(env)

        for name in ("layer", "actor", "raw_text", "text", "trimmed_text"):
            with pytest.raises(ExecutionAttributeUnavailableError):
                getattr(line_object, name)

    def test_raises_for_missing_coordinate_variables(self) -> None:
        env = Environment(
            styles={"Default": make_style()},
            declaration="template",
        )
        line_object = _ExpressionLineObject(env)

        for name in (
            "start",
            "end",
            "dur",
            "mid",
            "i",
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
        ):
            with pytest.raises(ExecutionAttributeUnavailableError):
                getattr(line_object, name)

    def test_syls_raises_when_karaoke_missing(self) -> None:
        env = make_populated_environment()
        env.karaoke = None
        line_object = _ExpressionLineObject(env)

        with pytest.raises(ExecutionAttributeUnavailableError):
            _ = line_object.syls


class TestExpressionSyllableObject:
    def test_reads_populated_syllable_attributes(self) -> None:
        env = make_populated_environment()
        syl_object = _ExpressionSyllableObject(env)

        assert syl_object.start == 0
        assert syl_object.end == 400
        assert syl_object.dur == 400
        assert syl_object.kdur == 40.0
        assert syl_object.mid == 0 + 400 / 2
        assert syl_object.n == 2
        assert syl_object.i == 0
        assert syl_object.left == 1
        assert syl_object.center == 10
        assert syl_object.right == 20
        assert syl_object.width == 19
        assert syl_object.top == 5
        assert syl_object.middle == 15
        assert syl_object.bottom == 25
        assert syl_object.height == 20
        assert syl_object.x == 11
        assert syl_object.y == 16
        assert syl_object.tag == r"\k"
        assert syl_object.inline_fx == "sparkle"
        assert syl_object.text == "hi"
        assert syl_object.trimmed_text == "hi"

    def test_raises_for_each_missing_attribute(self) -> None:
        env = Environment(
            styles={"Default": make_style()},
            declaration="template",
        )
        syl_object = _ExpressionSyllableObject(env)

        for name in (
            "start",
            "end",
            "dur",
            "kdur",
            "mid",
            "n",
            "i",
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
            "tag",
            "inline_fx",
            "text",
            "trimmed_text",
        ):
            with pytest.raises(ExecutionAttributeUnavailableError):
                getattr(syl_object, name)


class TestExpressionWordObject:
    def test_reads_populated_word_attributes(self) -> None:
        env = make_populated_environment()
        word_object = _ExpressionWordObject(env)

        assert word_object.start == 0
        assert word_object.end == 400
        assert word_object.dur == 400
        assert word_object.kdur == 40.0
        assert word_object.mid == 0 + 400 / 2
        assert word_object.n == 1
        assert word_object.i == 0
        assert word_object.left == 1
        assert word_object.center == 10
        assert word_object.right == 20
        assert word_object.width == 19
        assert word_object.top == 5
        assert word_object.middle == 15
        assert word_object.bottom == 25
        assert word_object.height == 20
        assert word_object.x == 11
        assert word_object.y == 16
        assert word_object.text == "hi"
        assert word_object.trimmed_text == "hi"

    def test_raises_for_each_missing_attribute(self) -> None:
        env = Environment(
            styles={"Default": make_style()},
            declaration="template",
        )
        word_object = _ExpressionWordObject(env)

        for name in (
            "start",
            "end",
            "dur",
            "kdur",
            "mid",
            "n",
            "i",
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
            "text",
            "trimmed_text",
        ):
            with pytest.raises(ExecutionAttributeUnavailableError):
                getattr(word_object, name)


class TestExpressionCharObject:
    def test_reads_populated_char_attributes(self) -> None:
        env = make_populated_environment()
        char_object = _ExpressionCharObject(env)

        assert char_object.i == 0
        assert char_object.n == 2
        assert char_object.left == 1
        assert char_object.center == 10
        assert char_object.right == 20
        assert char_object.width == 19
        assert char_object.top == 5
        assert char_object.middle == 15
        assert char_object.bottom == 25
        assert char_object.height == 20
        assert char_object.x == 11
        assert char_object.y == 16
        assert char_object.text == "hi"
        assert char_object.trimmed_text == "hi"

    def test_raises_for_each_missing_attribute(self) -> None:
        env = Environment(
            styles={"Default": make_style()},
            declaration="template",
        )
        char_object = _ExpressionCharObject(env)

        for name in (
            "i",
            "n",
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
            "text",
            "trimmed_text",
        ):
            with pytest.raises(ExecutionAttributeUnavailableError):
                getattr(char_object, name)


class TestExpressionKaraokeSyllableObject:
    def test_exposes_immutable_syllable_view(self) -> None:
        env = make_populated_environment()
        line_object = _ExpressionLineObject(env)
        karaoke_syllables = line_object.syls

        first = karaoke_syllables[0]
        assert first.start_time == 0
        assert first.end_time == 400
        assert first.duration == 400
        assert first.kdur == 40.0
        assert first.left == 1.0
        assert first.center == 10.0
        assert first.right == 20.0
        assert first.width == 19.0
        assert first.top == 5.0
        assert first.middle == 15.0
        assert first.bottom == 25.0
        assert first.height == 20.0
        assert first.x == 11.0
        assert first.y == 16.0


class TestEnvironmentExpressionObjectExposure:
    def test_as_dict_returns_narrowed_namespace_without_line(self) -> None:
        env = Environment(
            styles={"Default": make_style()},
            declaration="template",
        )

        namespace = env.as_dict()

        assert "line" not in namespace
        assert "style" not in namespace
        assert "metadata" not in namespace
        assert "word" not in namespace
        assert "syl" not in namespace
        assert "char" not in namespace

    def test_as_dict_exposes_expression_objects_when_populated(self) -> None:
        env = make_populated_environment()

        namespace = env.as_dict()

        assert isinstance(namespace["line"], _ExpressionLineObject)
        assert isinstance(namespace["style"], _ExpressionStyleObject)
        assert isinstance(namespace["metadata"], _ExpressionMetadataObject)
        assert isinstance(namespace["word"], _ExpressionWordObject)
        assert isinstance(namespace["syl"], _ExpressionSyllableObject)
        assert isinstance(namespace["char"], _ExpressionCharObject)
