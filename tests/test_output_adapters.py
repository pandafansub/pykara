"""Tests for output adapters."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import pytest

from pykara.adapters import SubtitleDocument
from pykara.adapters.input.sub_station_alpha import SubStationAlphaReader
from pykara.adapters.output.json_adapter import JsonWriter
from pykara.adapters.output.sub_station_alpha import SubStationAlphaWriter
from pykara.data import Event, Metadata, Style
from pykara.errors import DocumentWriteError


def make_style() -> Style:
    return Style(
        name="Default",
        fontname="Noto Sans",
        fontsize=40.0,
        primary_colour="&H00FFFFFF",
        secondary_colour="&H0000FFFF",
        outline_colour="&H00000000",
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
        margin_t=20,
        margin_b=20,
        encoding=1,
    )


def make_document() -> SubtitleDocument:
    style = make_style()
    return SubtitleDocument(
        metadata=Metadata(
            res_x=1920,
            res_y=1080,
            raw={"Title": "Example"},
        ),
        styles={style.name: style},
        events=[
            Event(
                text=r"{\k20}go",
                effect="karaoke",
                style="Default",
                layer=0,
                start_time=1000,
                end_time=1200,
                comment=False,
                actor="Singer",
                margin_l=0,
                margin_r=0,
                margin_t=0,
                margin_b=0,
            ),
            Event(
                text=r"{\an5\pos(100,200)}go",
                effect="fx",
                style="Default",
                layer=1,
                start_time=1000,
                end_time=1200,
                comment=False,
                actor="FX",
                margin_l=0,
                margin_r=0,
                margin_t=0,
                margin_b=0,
            ),
        ],
    )


class TestSubStationAlphaWriter:
    def test_round_trip_ass_document(self, tmp_path: Path) -> None:
        document = make_document()
        path = tmp_path / "roundtrip.ass"

        SubStationAlphaWriter().write(document, path)
        loaded = SubStationAlphaReader().read(path)

        assert loaded.metadata.res_x == 1920
        assert loaded.metadata.res_y == 1080
        assert loaded.styles["Default"].fontname == "Noto Sans"
        assert len(loaded.events) == 2
        assert loaded.events[1].effect == "fx"
        assert loaded.events[1].layer == 1

    def test_write_wraps_save_errors(self, tmp_path: Path) -> None:
        document = make_document()
        path = tmp_path / "missing" / "output.ass"

        with pytest.raises(DocumentWriteError) as exc_info:
            SubStationAlphaWriter().write(document, path)

        assert exc_info.value.path == path

    def test_write_accepts_style_colors_with_trailing_ampersand(
        self,
        tmp_path: Path,
    ) -> None:
        style = replace(make_style(), primary_colour="&H11223344&")
        document = replace(make_document(), styles={style.name: style})
        path = tmp_path / "trailing-color.ass"

        SubStationAlphaWriter().write(document, path)

        assert path.exists()


class TestJsonWriter:
    def test_to_dict_matches_expected_schema(self) -> None:
        document = make_document()

        payload = cast(dict[str, Any], JsonWriter().to_dict(document))
        metadata = cast(dict[str, Any], payload["metadata"])
        styles = cast(dict[str, dict[str, Any]], payload["styles"])
        events = cast(list[dict[str, Any]], payload["events"])

        assert set(payload) == {"metadata", "styles", "events"}
        assert metadata["res_x"] == 1920
        assert styles["Default"]["fontname"] == "Noto Sans"
        assert events[0]["effect"] == "karaoke"

    def test_write_serializes_json(self, tmp_path: Path) -> None:
        document = make_document()
        path = tmp_path / "output.json"

        JsonWriter().write(document, path)

        loaded = cast(
            dict[str, Any],
            json.loads(path.read_text(encoding="utf-8")),
        )
        metadata = cast(dict[str, Any], loaded["metadata"])
        events = cast(list[dict[str, Any]], loaded["events"])
        assert metadata["res_y"] == 1080
        assert events[1]["actor"] == "FX"

    def test_write_wraps_file_errors(self, tmp_path: Path) -> None:
        document = make_document()
        path = tmp_path / "missing" / "output.json"

        with pytest.raises(DocumentWriteError) as exc_info:
            JsonWriter().write(document, path)

        assert exc_info.value.path == path
