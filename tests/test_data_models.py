"""Unit tests for the phase 2 data models."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from pykara.data import (
    Event,
    Highlight,
    Karaoke,
    Metadata,
    RuntimeLine,
    Style,
    Syllable,
)


def make_style() -> Style:
    return Style(
        name="Default",
        fontname="Arial",
        fontsize=42.0,
        primary_colour="&H00FFFFFF",
        secondary_colour="&H0000FFFF",
        outline_colour="&H00000000",
        back_colour="&H64000000",
        bold=True,
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
        margin_l=20,
        margin_r=20,
        margin_t=30,
        margin_b=40,
        encoding=1,
    )


def make_event() -> Event:
    return Event(
        text="{\\k20}ka",
        effect="karaoke",
        style="Default",
        layer=0,
        start_time=1000,
        end_time=2000,
        comment=False,
        actor="Singer",
        margin_l=10,
        margin_r=15,
        margin_t=20,
        margin_b=25,
    )


def make_highlight() -> Highlight:
    return Highlight(start_time=0, end_time=200, duration=200)


def make_syllable() -> Syllable:
    return Syllable(
        index=1,
        raw_text=" ka ",
        text=" ka ",
        trimmed_text="ka",
        prespace=" ",
        postspace=" ",
        start_time=0,
        end_time=200,
        duration=200,
        kdur=20.0,
        tag="\\k20",
        inline_fx="flash",
        highlights=[make_highlight()],
    )


class TestMetadata:
    def test_equality(self) -> None:
        left = Metadata(
            res_x=1920,
            res_y=1080,
            video_x_correct_factor=1.25,
            raw={"Title": "Example"},
        )
        right = Metadata(
            res_x=1920,
            res_y=1080,
            video_x_correct_factor=1.25,
            raw={"Title": "Example"},
        )

        assert left == right

    def test_defaults(self) -> None:
        metadata = Metadata(res_x=1920, res_y=1080)

        assert metadata.video_x_correct_factor == 1.0
        assert metadata.raw == {}

    def test_is_frozen(self) -> None:
        metadata = Metadata(res_x=1920, res_y=1080)
        attribute_name = "res_x"

        with pytest.raises(FrozenInstanceError):
            setattr(metadata, attribute_name, 1280)


class TestStyle:
    def test_equality(self) -> None:
        assert make_style() == make_style()

    def test_margin_v_returns_top_margin(self) -> None:
        style = make_style()

        assert style.margin_v == style.margin_t

    def test_is_frozen(self) -> None:
        style = make_style()
        attribute_name = "fontname"

        with pytest.raises(FrozenInstanceError):
            setattr(style, attribute_name, "Noto Sans")


class TestEvent:
    def test_equality(self) -> None:
        assert make_event() == make_event()

    def test_is_mutable(self) -> None:
        event = make_event()

        event.text = "updated"

        assert event.text == "updated"


class TestRuntimeLine:
    def test_construction(self) -> None:
        runtime_line = RuntimeLine(
            event=make_event(),
            styleref=make_style(),
            duration=1000,
        )

        assert runtime_line.duration == 1000
        assert runtime_line.styleref.name == "Default"

    def test_equality(self) -> None:
        left = RuntimeLine(
            event=make_event(),
            styleref=make_style(),
            duration=1000,
        )
        right = RuntimeLine(
            event=make_event(),
            styleref=make_style(),
            duration=1000,
        )

        assert left == right


class TestHighlight:
    def test_equality(self) -> None:
        assert make_highlight() == make_highlight()

    def test_is_frozen(self) -> None:
        highlight = make_highlight()
        attribute_name = "duration"

        with pytest.raises(FrozenInstanceError):
            setattr(highlight, attribute_name, 50)


class TestSyllable:
    def test_equality(self) -> None:
        assert make_syllable() == make_syllable()

    def test_defaults_cover_preprocessing_fields(self) -> None:
        syllable = make_syllable()

        assert syllable.style is None
        assert syllable.width == 0.0
        assert syllable.height == 0.0
        assert syllable.prespacewidth == 0.0
        assert syllable.postspacewidth == 0.0
        assert syllable.left == 0.0
        assert syllable.center == 0.0
        assert syllable.right == 0.0

    def test_accepts_resolved_style(self) -> None:
        syllable = make_syllable()
        style = make_style()

        syllable.style = style

        assert syllable.style is style


class TestKaraoke:
    def test_equality(self) -> None:
        left = Karaoke(
            syllables=[make_syllable()],
            text="ka",
            trimmed_text="ka",
        )
        right = Karaoke(
            syllables=[make_syllable()],
            text="ka",
            trimmed_text="ka",
        )

        assert left == right

    def test_construction(self) -> None:
        karaoke = Karaoke(
            syllables=[make_syllable()],
            text="ka",
            trimmed_text="ka",
        )

        assert len(karaoke.syllables) == 1
        assert karaoke.text == "ka"
        assert karaoke.trimmed_text == "ka"
