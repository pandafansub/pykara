"""Unit tests for the SSA input adapter."""

from __future__ import annotations

from pathlib import Path

from _pytest.monkeypatch import MonkeyPatch

from pykara.adapters import SubtitleDocument
from pykara.adapters.input import SubStationAlphaReader
from pykara.data import Event, Metadata, Style
from pykara.errors import DocumentReadError

TESTS_DIR = Path(__file__).parent
FIXTURES_DIR = TESTS_DIR / "fixtures" / "acceptance"
FIXTURE_PATH = FIXTURES_DIR / "basic_01_grow_larger.ass"


class TestSubStationAlphaReader:
    def test_read_returns_domain_document(self) -> None:
        reader = SubStationAlphaReader()

        document = reader.read(FIXTURE_PATH)

        assert isinstance(document, SubtitleDocument)
        assert isinstance(document.metadata, Metadata)
        assert all(
            isinstance(style, Style) for style in document.styles.values()
        )
        assert all(isinstance(event, Event) for event in document.events)

    def test_read_maps_metadata_styles_and_events(self) -> None:
        reader = SubStationAlphaReader()

        document = reader.read(FIXTURE_PATH)
        default_style = document.styles["Default"]
        first_event = document.events[0]
        karaoke_event = document.events[3]

        assert document.metadata.res_x == 1920
        assert document.metadata.res_y == 1080
        assert document.metadata.video_x_correct_factor == 1.0
        assert document.metadata.raw["Title"] == "Default Aegisub file"
        assert (
            document.metadata.raw["Video File"]
            == "?dummy:24000/1001:40000:1920:1080:47:163:254:c"
        )

        assert default_style.name == "Default"
        assert default_style.fontname == "Noto Sans"
        assert default_style.fontsize == 80.0
        assert default_style.primary_colour == "&H00FFFFFF"
        assert default_style.secondary_colour == "&H000000FF"
        assert default_style.outline_colour == "&H00000000"
        assert default_style.back_colour == "&H00000000"
        assert default_style.alignment == 2
        assert default_style.margin_l == 10
        assert default_style.margin_r == 10
        assert default_style.margin_t == 30
        assert default_style.margin_b == 30

        assert first_event.comment is True
        assert first_event.actor == "lead-in"
        assert first_event.effect == "template syl"
        assert first_event.style == "Default"
        assert first_event.text.startswith("!retime.start2syl(-300,0)!")

        assert karaoke_event.comment is True
        assert karaoke_event.effect == "karaoke"
        assert karaoke_event.start_time == 17190
        assert karaoke_event.end_time == 21090
        assert karaoke_event.margin_t == 0
        assert karaoke_event.margin_b == 0
        assert karaoke_event.text.startswith("{\\k36}gol")

    def test_read_raises_document_read_error_for_missing_file(self) -> None:
        reader = SubStationAlphaReader()
        missing_path = FIXTURES_DIR / "does-not-exist.ass"

        try:
            reader.read(missing_path)
        except DocumentReadError as error:
            assert error.path == missing_path
        else:
            message = "Expected DocumentReadError for a missing subtitle file."
            raise AssertionError(message)

    def test_read_uses_fallback_message_for_empty_error(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
    ) -> None:
        reader = SubStationAlphaReader()
        input_path = tmp_path / "broken.ass"
        input_path.write_text("not really an ass file", encoding="utf-8")

        def boom(*_args: object, **_kwargs: object) -> None:
            raise RuntimeError()

        monkeypatch.setattr(
            "pathlib.Path.read_text",
            boom,
        )

        try:
            reader.read(input_path)
        except DocumentReadError as error:
            assert str(input_path) in str(error)
        else:
            message = "Expected DocumentReadError for parse failure."
            raise AssertionError(message)

    def test_video_x_correct_factor_returns_one_without_project(
        self,
        tmp_path: Path,
    ) -> None:
        reader = SubStationAlphaReader()
        input_path = tmp_path / "no_project.ass"
        input_path.write_text(
            "\n".join(
                [
                    "[Script Info]",
                    "ScriptType: v4.00+",
                    "PlayResX: 1920",
                    "PlayResY: 1080",
                    "",
                    "[V4+ Styles]",
                    (
                        "Format: Name, Fontname, Fontsize, PrimaryColour, "
                        "SecondaryColour, OutlineColour, BackColour, Bold, "
                        "Italic, Underline, StrikeOut, ScaleX, ScaleY, "
                        "Spacing, Angle, BorderStyle, Outline, Shadow, "
                        "Alignment, MarginL, MarginR, MarginV, Encoding"
                    ),
                    (
                        "Style: Default,Noto Sans,40,&H00FFFFFF,&H0000FFFF,"
                        "&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,2,1,2,"
                        "10,10,20,1"
                    ),
                    "",
                    "[Events]",
                    (
                        "Format: Layer, Start, End, Style, Name, MarginL, "
                        "MarginR, MarginV, Effect, Text"
                    ),
                    ("Dialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,0,,hi"),
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        document = reader.read(input_path, stop_at_generated_fx=True)

        assert document.metadata.video_x_correct_factor == 1.0

    def test_video_x_correct_factor_uses_aspect_ratio_from_project(
        self,
        tmp_path: Path,
    ) -> None:
        reader = SubStationAlphaReader()
        input_path = tmp_path / "aspect.ass"
        input_path.write_text(
            "\n".join(
                [
                    "[Script Info]",
                    "ScriptType: v4.00+",
                    "PlayResX: 1280",
                    "PlayResY: 720",
                    "",
                    "[Aegisub Project Garbage]",
                    "Video AR Value: 2.0",
                    "",
                    "[V4+ Styles]",
                    (
                        "Format: Name, Fontname, Fontsize, PrimaryColour, "
                        "SecondaryColour, OutlineColour, BackColour, Bold, "
                        "Italic, Underline, StrikeOut, ScaleX, ScaleY, "
                        "Spacing, Angle, BorderStyle, Outline, Shadow, "
                        "Alignment, MarginL, MarginR, MarginV, Encoding"
                    ),
                    (
                        "Style: Default,Noto Sans,40,&H00FFFFFF,&H0000FFFF,"
                        "&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,2,1,2,"
                        "10,10,20,1"
                    ),
                    "",
                    "[Events]",
                    (
                        "Format: Layer, Start, End, Style, Name, MarginL, "
                        "MarginR, MarginV, Effect, Text"
                    ),
                    ("Dialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,0,,hi"),
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        document = reader.read(input_path, stop_at_generated_fx=True)

        expected = (1.0 / 2.0) / (720 / 1280)
        assert document.metadata.video_x_correct_factor == expected

    def test_video_x_correct_factor_falls_back_when_aspect_ratio_invalid(
        self,
        tmp_path: Path,
    ) -> None:
        reader = SubStationAlphaReader()
        input_path = tmp_path / "bad_aspect.ass"
        input_path.write_text(
            "\n".join(
                [
                    "[Script Info]",
                    "ScriptType: v4.00+",
                    "PlayResX: 1920",
                    "PlayResY: 1080",
                    "",
                    "[Aegisub Project Garbage]",
                    "Video AR Value: not-a-number",
                    "",
                    "[V4+ Styles]",
                    (
                        "Format: Name, Fontname, Fontsize, PrimaryColour, "
                        "SecondaryColour, OutlineColour, BackColour, Bold, "
                        "Italic, Underline, StrikeOut, ScaleX, ScaleY, "
                        "Spacing, Angle, BorderStyle, Outline, Shadow, "
                        "Alignment, MarginL, MarginR, MarginV, Encoding"
                    ),
                    (
                        "Style: Default,Noto Sans,40,&H00FFFFFF,&H0000FFFF,"
                        "&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,2,1,2,"
                        "10,10,20,1"
                    ),
                    "",
                    "[Events]",
                    (
                        "Format: Layer, Start, End, Style, Name, MarginL, "
                        "MarginR, MarginV, Effect, Text"
                    ),
                    ("Dialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,0,,hi"),
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        document = reader.read(input_path, stop_at_generated_fx=True)

        assert document.metadata.video_x_correct_factor == 1.0

    def test_dummy_video_token_with_insufficient_fields_is_ignored(
        self,
        tmp_path: Path,
    ) -> None:
        reader = SubStationAlphaReader()
        input_path = tmp_path / "short_dummy.ass"
        input_path.write_text(
            "\n".join(
                [
                    "[Script Info]",
                    "ScriptType: v4.00+",
                    "PlayResX: 1920",
                    "PlayResY: 1080",
                    "",
                    "[Aegisub Project Garbage]",
                    "Video File: ?dummy:24000/1001:40000",
                    "",
                    "[V4+ Styles]",
                    (
                        "Format: Name, Fontname, Fontsize, PrimaryColour, "
                        "SecondaryColour, OutlineColour, BackColour, Bold, "
                        "Italic, Underline, StrikeOut, ScaleX, ScaleY, "
                        "Spacing, Angle, BorderStyle, Outline, Shadow, "
                        "Alignment, MarginL, MarginR, MarginV, Encoding"
                    ),
                    (
                        "Style: Default,Noto Sans,40,&H00FFFFFF,&H0000FFFF,"
                        "&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,2,1,2,"
                        "10,10,20,1"
                    ),
                    "",
                    "[Events]",
                    (
                        "Format: Layer, Start, End, Style, Name, MarginL, "
                        "MarginR, MarginV, Effect, Text"
                    ),
                    ("Dialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,0,,hi"),
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        document = reader.read(input_path, stop_at_generated_fx=True)

        assert document.metadata.video_x_correct_factor == 1.0

    def test_dummy_video_token_with_zero_dimensions_is_ignored(
        self,
        tmp_path: Path,
    ) -> None:
        reader = SubStationAlphaReader()
        input_path = tmp_path / "zero_dummy.ass"
        input_path.write_text(
            "\n".join(
                [
                    "[Script Info]",
                    "ScriptType: v4.00+",
                    "PlayResX: 1920",
                    "PlayResY: 1080",
                    "",
                    "[Aegisub Project Garbage]",
                    "Video File: ?dummy:24000/1001:40000:0:0:47:163:254:c",
                    "",
                    "[V4+ Styles]",
                    (
                        "Format: Name, Fontname, Fontsize, PrimaryColour, "
                        "SecondaryColour, OutlineColour, BackColour, Bold, "
                        "Italic, Underline, StrikeOut, ScaleX, ScaleY, "
                        "Spacing, Angle, BorderStyle, Outline, Shadow, "
                        "Alignment, MarginL, MarginR, MarginV, Encoding"
                    ),
                    (
                        "Style: Default,Noto Sans,40,&H00FFFFFF,&H0000FFFF,"
                        "&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,2,1,2,"
                        "10,10,20,1"
                    ),
                    "",
                    "[Events]",
                    (
                        "Format: Layer, Start, End, Style, Name, MarginL, "
                        "MarginR, MarginV, Effect, Text"
                    ),
                    ("Dialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,0,,hi"),
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        document = reader.read(input_path)

        assert document.metadata.video_x_correct_factor == 1.0

    def test_unparseable_play_res_falls_back_to_zero(
        self,
        tmp_path: Path,
    ) -> None:
        reader = SubStationAlphaReader()
        input_path = tmp_path / "bad_res.ass"
        input_path.write_text(
            "\n".join(
                [
                    "[Script Info]",
                    "ScriptType: v4.00+",
                    "PlayResX: not-a-number",
                    "",
                    "[V4+ Styles]",
                    (
                        "Format: Name, Fontname, Fontsize, PrimaryColour, "
                        "SecondaryColour, OutlineColour, BackColour, Bold, "
                        "Italic, Underline, StrikeOut, ScaleX, ScaleY, "
                        "Spacing, Angle, BorderStyle, Outline, Shadow, "
                        "Alignment, MarginL, MarginR, MarginV, Encoding"
                    ),
                    (
                        "Style: Default,Noto Sans,40,&H00FFFFFF,&H0000FFFF,"
                        "&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,2,1,2,"
                        "10,10,20,1"
                    ),
                    "",
                    "[Events]",
                    (
                        "Format: Layer, Start, End, Style, Name, MarginL, "
                        "MarginR, MarginV, Effect, Text"
                    ),
                    ("Dialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,0,,hi"),
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        document = reader.read(input_path)

        assert document.metadata.res_x == 0

    def test_read_stops_at_first_generated_fx_event(
        self,
        tmp_path: Path,
    ) -> None:
        reader = SubStationAlphaReader()
        input_path = tmp_path / "stops_at_fx.ass"
        input_path.write_text(
            "\n".join(
                [
                    "[Script Info]",
                    "ScriptType: v4.00+",
                    "PlayResX: 1920",
                    "PlayResY: 1080",
                    "",
                    "[V4+ Styles]",
                    (
                        "Format: Name, Fontname, Fontsize, PrimaryColour, "
                        "SecondaryColour, OutlineColour, BackColour, Bold, "
                        "Italic, Underline, StrikeOut, ScaleX, ScaleY, "
                        "Spacing, Angle, BorderStyle, Outline, Shadow, "
                        "Alignment, MarginL, MarginR, MarginV, Encoding"
                    ),
                    (
                        "Style: Default,Noto Sans,40,&H00FFFFFF,&H0000FFFF,"
                        "&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,2,1,2,"
                        "10,10,20,1"
                    ),
                    "",
                    "[Events]",
                    (
                        "Format: Layer, Start, End, Style, Name, MarginL, "
                        "MarginR, MarginV, Effect, Text"
                    ),
                    (
                        "Comment: 0,0:00:00.00,0:00:00.01,Default,,0,0,0,"
                        "template syl no_text,X"
                    ),
                    (
                        "Dialogue: 0,0:00:01.00,0:00:02.00,Default,,0,0,0,"
                        "karaoke,{\\k20}go"
                    ),
                    (
                        "Dialogue: 1,0:00:01.00,0:00:02.00,Default,,0,0,0,"
                        "fx,generated"
                    ),
                    (
                        "Dialogue: 2,0:00:02.00,0:00:03.00,Default,,0,0,0,"
                        "karaoke,{\\k20}after"
                    ),
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        document = reader.read(input_path, stop_at_generated_fx=True)

        assert [event.effect for event in document.events] == [
            "template syl no_text",
            "karaoke",
        ]
