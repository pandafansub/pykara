"""Shared helpers for acceptance fixture regeneration and validation."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from pykara.adapters import SubtitleDocument
from pykara.adapters.input.sub_station_alpha import SubStationAlphaReader
from pykara.adapters.output.json_adapter import JsonWriter
from pykara.adapters.output.sub_station_alpha import SubStationAlphaWriter
from pykara.data import Event

TESTS_DIR = Path(__file__).parent
ROOT_DIR = TESTS_DIR.parent
FIXTURES_DIR = TESTS_DIR / "fixtures"
FONT_FIXTURE_DIR = FIXTURES_DIR / "fonts"
CLI_BIN = ROOT_DIR / ".venv" / "bin" / "pykara"


def _copy_event(
    event: Event,
    *,
    comment: bool | None = None,
) -> Event:
    """Return a shallow event clone with an optional comment override."""

    return Event(
        text=event.text,
        effect=event.effect,
        style=event.style,
        layer=event.layer,
        start_time=event.start_time,
        end_time=event.end_time,
        comment=event.comment if comment is None else comment,
        actor=event.actor,
        margin_l=event.margin_l,
        margin_r=event.margin_r,
        margin_t=event.margin_t,
        margin_b=event.margin_b,
    )


def load_document(path: Path) -> SubtitleDocument:
    """Read one ASS fixture from disk."""

    return SubStationAlphaReader().read(path)


def load_json(path: Path) -> dict[str, object]:
    """Read one JSON fixture from disk."""

    return json.loads(path.read_text(encoding="utf-8"))


def strip_fx_events(document: SubtitleDocument) -> SubtitleDocument:
    """Return a copy of the document without generated ``fx`` events."""

    return SubtitleDocument(
        metadata=document.metadata,
        styles=document.styles,
        events=[
            event for event in document.events if event.effect.lower() != "fx"
        ],
    )


def build_cli_input_document(path: Path) -> SubtitleDocument:
    """Return the saved fixture without generated ``fx`` events."""

    return strip_fx_events(load_document(path))


def build_saved_cli_document(path: Path) -> SubtitleDocument:
    """Return the saved fixture in the document shape written by the CLI."""

    document = load_document(path)
    return SubtitleDocument(
        metadata=document.metadata,
        styles=document.styles,
        events=[
            _copy_event(
                event,
                comment=(True if event.effect.lower() == "karaoke" else None),
            )
            for event in document.events
        ],
    )


def build_saved_cli_json_document(path: Path) -> dict[str, object]:
    """Return the JSON payload expected from the saved fixture."""

    return JsonWriter().to_dict(build_saved_cli_document(path))


def write_document(document: SubtitleDocument, path: Path) -> None:
    """Write one subtitle document as ASS."""

    SubStationAlphaWriter().write(document, path)


def build_cli_command(
    input_path: Path,
    output_path: Path,
    *extra_args: str,
    use_font_dir: bool,
) -> list[str]:
    """Build one CLI command line for fixture-driven subprocess tests."""

    command = [
        str(CLI_BIN),
        str(input_path),
        str(output_path),
        *extra_args,
    ]
    if use_font_dir and "--font-dir" not in extra_args:
        command.extend(["--font-dir", str(FONT_FIXTURE_DIR)])
    return command


def run_cli(
    input_path: Path,
    output_path: Path,
    *extra_args: str,
    use_font_dir: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Execute the real CLI in a subprocess."""

    command = build_cli_command(
        input_path,
        output_path,
        *extra_args,
        use_font_dir=use_font_dir,
    )

    return subprocess.run(  # noqa: S603 - test helper executes repo-owned fixture paths
        command,
        cwd=ROOT_DIR,
        check=False,
        capture_output=True,
        text=True,
    )
