"""Tests for CLI pipeline and exit codes."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, cast

from _pytest.capture import CaptureFixture
from _pytest.monkeypatch import MonkeyPatch

from pykara.adapters.input.sub_station_alpha import SubStationAlphaReader
from pykara.errors import PykaraError, ValidationError
from pykara.interfaces.cli.main import main
from pykara.interfaces.cli.pipeline import write_output
from pykara.validation.reports import Severity, ValidationReport, Violation

cli_main = sys.modules["pykara.interfaces.cli.main"]


def confirm_yes(_prompt: str) -> str:
    return "y"


def confirm_no(_prompt: str) -> str:
    return "n"


def write_ass(
    path: Path,
    *,
    invalid_template: bool = False,
    invalid_event_time: bool = False,
) -> None:
    effect = "template" if invalid_template else "template syl no_text"
    dialogue_end = "0:00:01.00" if invalid_event_time else "0:00:01.50"
    path.write_text(
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
                (f"Comment: 0,0:00:00.00,0:00:00.01,Default,,0,0,0,{effect},X"),
                (
                    f"Dialogue: 0,0:00:01.00,{dialogue_end},Default,,0,0,0,"
                    r"karaoke,{\k20}go"
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def add_stale_fx_line(path: Path) -> None:
    """Append an old generated line to simulate a previously rendered ASS."""

    with path.open("a", encoding="utf-8") as file:
        file.write(
            "Dialogue: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,"
            "fx,stale generated line\n"
        )


class TestCli:
    def test_returns_zero_on_success(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
    ) -> None:
        input_path = tmp_path / "input.ass"
        output_path = tmp_path / "output.ass"
        write_ass(input_path)

        monkeypatch.setattr(
            "sys.argv",
            ["pykara", str(input_path), str(output_path)],
        )

        result = main()

        assert result == 0
        assert output_path.exists()

    def test_same_input_output_prompts_before_overwrite(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
    ) -> None:
        input_path = tmp_path / "same.ass"
        write_ass(input_path)
        monkeypatch.setattr("builtins.input", confirm_yes)
        monkeypatch.setattr(
            "sys.argv",
            ["pykara", str(input_path), str(input_path)],
        )

        result = main()

        assert result == 0

    def test_same_input_output_can_be_cancelled(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
        capsys: CaptureFixture[str],
    ) -> None:
        input_path = tmp_path / "same.ass"
        write_ass(input_path)
        monkeypatch.setattr("builtins.input", confirm_no)
        monkeypatch.setattr(
            "sys.argv",
            ["pykara", str(input_path), str(input_path)],
        )

        result = main()
        captured = capsys.readouterr()

        assert result == 1
        assert "operation cancelled by user" in captured.err

    def test_same_input_output_generated_only_is_rejected(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
        capsys: CaptureFixture[str],
    ) -> None:
        input_path = tmp_path / "same.ass"
        write_ass(input_path)
        monkeypatch.setattr(
            "sys.argv",
            [
                "pykara",
                str(input_path),
                str(input_path),
                "--generated-only",
            ],
        )

        result = main()
        captured = capsys.readouterr()

        assert result == 1
        assert (
            "templates and source karaoke lines would be lost" in captured.err
        )

    def test_comments_karaoke_source_lines_in_output(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
    ) -> None:
        input_path = tmp_path / "input.ass"
        output_path = tmp_path / "output.ass"
        write_ass(input_path)

        monkeypatch.setattr(
            "sys.argv",
            ["pykara", str(input_path), str(output_path)],
        )

        result = main()
        document = SubStationAlphaReader().read(output_path)
        karaoke_events = [
            event
            for event in document.events
            if event.effect.lower() == "karaoke"
        ]
        fx_events = [
            event for event in document.events if event.effect.lower() == "fx"
        ]

        assert result == 0
        assert len(karaoke_events) == 1
        assert karaoke_events[0].comment is True
        assert fx_events
        assert all(event.comment is False for event in fx_events)

    def test_discards_existing_fx_lines_before_processing(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
    ) -> None:
        input_path = tmp_path / "input.ass"
        output_path = tmp_path / "output.ass"
        write_ass(input_path)
        add_stale_fx_line(input_path)

        monkeypatch.setattr(
            "sys.argv",
            ["pykara", str(input_path), str(output_path)],
        )

        result = main()
        document = SubStationAlphaReader().read(output_path)
        fx_events = [
            event for event in document.events if event.effect.lower() == "fx"
        ]

        assert result == 0
        assert fx_events
        assert all(event.text != "stale generated line" for event in fx_events)

    def test_write_output_never_copies_existing_fx_lines(
        self,
        tmp_path: Path,
    ) -> None:
        input_path = tmp_path / "input.ass"
        output_path = tmp_path / "output.ass"
        write_ass(input_path)
        add_stale_fx_line(input_path)
        document = SubStationAlphaReader().read(input_path)

        write_output(document, [], output_path, None)

        output_document = SubStationAlphaReader().read(output_path)

        assert all(
            event.effect.lower() != "fx" for event in output_document.events
        )

    def test_generated_only_writes_only_fx_lines(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
    ) -> None:
        input_path = tmp_path / "input.ass"
        output_path = tmp_path / "output.ass"
        write_ass(input_path)

        monkeypatch.setattr(
            "sys.argv",
            [
                "pykara",
                str(input_path),
                str(output_path),
                "--generated-only",
            ],
        )

        result = main()
        document = SubStationAlphaReader().read(output_path)

        assert result == 0
        assert document.events
        assert all(event.effect.lower() == "fx" for event in document.events)

    def test_write_output_generated_only_skips_source_events(
        self,
        tmp_path: Path,
    ) -> None:
        input_path = tmp_path / "input.ass"
        output_path = tmp_path / "output.ass"
        write_ass(input_path)
        document = SubStationAlphaReader().read(input_path)

        write_output(document, [], output_path, None, generated_only=True)

        output_document = SubStationAlphaReader().read(output_path)

        assert output_document.events == []

    def test_returns_one_on_read_error(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
    ) -> None:
        output_path = tmp_path / "output.ass"
        missing_path = tmp_path / "missing.ass"

        monkeypatch.setattr(
            "sys.argv",
            ["pykara", str(missing_path), str(output_path)],
        )

        result = main()

        assert result == 1

    def test_returns_two_on_validation_error(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
    ) -> None:
        input_path = tmp_path / "invalid.ass"
        output_path = tmp_path / "output.ass"
        write_ass(input_path, invalid_event_time=True)

        monkeypatch.setattr(
            "sys.argv",
            ["pykara", str(input_path), str(output_path)],
        )

        result = main()

        assert result == 2
        assert not output_path.exists()

    def test_returns_one_on_parse_error(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
    ) -> None:
        input_path = tmp_path / "invalid_parse.ass"
        output_path = tmp_path / "output.ass"
        write_ass(input_path, invalid_template=True)

        monkeypatch.setattr(
            "sys.argv",
            ["pykara", str(input_path), str(output_path)],
        )

        result = main()

        assert result == 1

    def test_warn_only_continues_pipeline(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
    ) -> None:
        input_path = tmp_path / "warn_only.ass"
        output_path = tmp_path / "output.ass"
        write_ass(input_path, invalid_event_time=True)

        monkeypatch.setattr(
            "sys.argv",
            [
                "pykara",
                str(input_path),
                str(output_path),
                "--warn-only",
            ],
        )

        result = main()

        assert result == 0
        assert output_path.exists()

    def test_prints_warnings_from_validation_report(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
        capsys: CaptureFixture[str],
    ) -> None:
        input_path = tmp_path / "warn.ass"
        output_path = tmp_path / "warn_output.ass"
        write_ass(input_path)

        warning_report = ValidationReport(
            violations=(
                Violation(
                    severity=Severity.WARNING,
                    code="W001",
                    message="a harmless warning",
                    context="unit test",
                ),
            ),
        )

        def fake_run_validation(
            *_args: object,
            **_kwargs: object,
        ) -> ValidationReport:
            return warning_report

        monkeypatch.setattr(cli_main, "run_validation", fake_run_validation)
        monkeypatch.setattr(
            "sys.argv",
            ["pykara", str(input_path), str(output_path)],
        )

        result = main()
        captured = capsys.readouterr()

        assert result == 0
        assert "warning [W001]: a harmless warning" in captured.err

    def test_prints_unused_code_name_in_warning(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
        capsys: CaptureFixture[str],
    ) -> None:
        input_path = tmp_path / "unused_code_var.ass"
        output_path = tmp_path / "unused_code_var_output.ass"
        write_ass(input_path)

        warning_report = ValidationReport(
            violations=(
                Violation(
                    severity=Severity.WARNING,
                    code="cross.unused_code_declaration",
                    message=(
                        "Code variable 'accent' is declared but never used."
                    ),
                    context="name='accent', kind=variable, scope=setup",
                ),
            ),
        )

        def fake_run_validation(
            *_args: object,
            **_kwargs: object,
        ) -> ValidationReport:
            return warning_report

        monkeypatch.setattr(cli_main, "run_validation", fake_run_validation)
        monkeypatch.setattr(
            "sys.argv",
            ["pykara", str(input_path), str(output_path)],
        )

        result = main()
        captured = capsys.readouterr()

        assert result == 0
        assert (
            "warning [cross.unused_code_declaration]: Code variable 'accent' "
            "is declared but never used."
        ) in captured.err

    def test_returns_two_on_validation_error_during_engine(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
        capsys: CaptureFixture[str],
    ) -> None:
        input_path = tmp_path / "engine_err.ass"
        output_path = tmp_path / "engine_err_output.ass"
        write_ass(input_path)

        error_report = ValidationReport(
            violations=(
                Violation(
                    severity=Severity.ERROR,
                    code="E777",
                    message="engine refused to run",
                    context="unit test",
                ),
            ),
        )

        def boom(*_args: object, **_kwargs: object) -> None:
            raise ValidationError(error_report)

        monkeypatch.setattr(cli_main, "run_engine", boom)
        monkeypatch.setattr(
            "sys.argv",
            ["pykara", str(input_path), str(output_path)],
        )

        result = main()
        captured = capsys.readouterr()

        assert result == 2
        assert "[E777] engine refused to run" in captured.err
        assert not output_path.exists()

    def test_returns_one_on_pykara_error_during_engine(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
        capsys: CaptureFixture[str],
    ) -> None:
        input_path = tmp_path / "pykara_err.ass"
        output_path = tmp_path / "pykara_err_output.ass"
        write_ass(input_path)

        def boom(*_args: object, **_kwargs: object) -> None:
            raise PykaraError("catastrophic failure")

        monkeypatch.setattr(cli_main, "run_engine", boom)
        monkeypatch.setattr(
            "sys.argv",
            ["pykara", str(input_path), str(output_path)],
        )

        result = main()
        captured = capsys.readouterr()

        assert result == 1
        assert "error: catastrophic failure" in captured.err

    def test_json_option_writes_json_output(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
    ) -> None:
        input_path = tmp_path / "input.ass"
        output_path = tmp_path / "output.ass"
        json_path = tmp_path / "output.json"
        write_ass(input_path)

        monkeypatch.setattr(
            "sys.argv",
            [
                "pykara",
                str(input_path),
                str(output_path),
                "--json",
                str(json_path),
            ],
        )

        result = main()

        assert result == 0
        payload = cast(
            dict[str, Any],
            json.loads(json_path.read_text(encoding="utf-8")),
        )
        assert payload["events"]

    def test_generated_only_applies_to_json_output(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
    ) -> None:
        input_path = tmp_path / "input.ass"
        output_path = tmp_path / "output.ass"
        json_path = tmp_path / "output.json"
        write_ass(input_path)

        monkeypatch.setattr(
            "sys.argv",
            [
                "pykara",
                str(input_path),
                str(output_path),
                "--generated-only",
                "--json",
                str(json_path),
            ],
        )

        result = main()
        ass_document = SubStationAlphaReader().read(output_path)
        payload = cast(
            dict[str, Any],
            json.loads(json_path.read_text(encoding="utf-8")),
        )

        assert result == 0
        assert ass_document.events
        assert all(
            event.effect.lower() == "fx" for event in ass_document.events
        )
        assert payload["events"]
        assert all(
            str(event["effect"]).lower() == "fx" for event in payload["events"]
        )

    def test_font_dir_option_is_passed_to_engine(
        self,
        tmp_path: Path,
        monkeypatch: MonkeyPatch,
    ) -> None:
        input_path = tmp_path / "input.ass"
        output_path = tmp_path / "output.ass"
        font_dir = tmp_path / "fonts"
        font_dir.mkdir()
        write_ass(input_path)
        captured_font_dirs: tuple[Path, ...] | None = None

        def fake_run_engine(
            *_args: object,
            font_dirs: tuple[Path, ...],
            **_kwargs: object,
        ) -> list[object]:
            nonlocal captured_font_dirs
            captured_font_dirs = font_dirs
            return []

        monkeypatch.setattr(cli_main, "run_engine", fake_run_engine)
        monkeypatch.setattr(
            "sys.argv",
            [
                "pykara",
                str(input_path),
                str(output_path),
                "--font-dir",
                str(font_dir),
            ],
        )

        result = main()

        assert result == 0
        assert captured_font_dirs == (font_dir.resolve(),)
