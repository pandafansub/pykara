"""CLI acceptance tests for saved compatibility fixtures."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pytest

from pykara.data import Event
from pykara.interfaces.cli.pipeline import (
    load_declarations,
    run_engine,
)
from pykara.interfaces.cli.pipeline import (
    load_document as load_cli_document,
)
from tests.acceptance_support import (
    FONT_FIXTURE_DIR,
    build_cli_input_document,
    build_saved_cli_document,
    build_saved_cli_json_document,
    load_document,
    load_json,
    run_cli,
    write_document,
)

TESTS_DIR = Path(__file__).parent
ACCEPTANCE_DIR = TESTS_DIR / "fixtures" / "acceptance"

pytestmark = pytest.mark.unix_only


def _fixture_ids(path: Path) -> str:
    return path.stem


ACCEPTANCE_FIXTURES = tuple(
    sorted(
        (
            *ACCEPTANCE_DIR.glob("basic_*.ass"),
            *ACCEPTANCE_DIR.glob("advanced_*.ass"),
        )
    )
)


@dataclass(frozen=True, slots=True)
class CliAcceptanceScenario:
    name: str
    extra_args: tuple[str, ...] = ()
    expect_json: bool = False


CLI_ACCEPTANCE_SCENARIOS = (
    CliAcceptanceScenario(name="ass", extra_args=("--seed", "1")),
    CliAcceptanceScenario(
        name="ass_json",
        extra_args=("--seed", "1", "--json", "{json_output}"),
        expect_json=True,
    ),
)


def _normalize_ass_time(value: int | float) -> int:
    """Match ASS centisecond quantization used by subtitle serialization."""

    return int(math.floor(value / 10.0 + 0.5) * 10)


def _normalize_event(event: Event) -> Event:
    return Event(
        text=event.text.rstrip(),
        effect=event.effect,
        style=event.style,
        layer=event.layer,
        start_time=_normalize_ass_time(event.start_time),
        end_time=_normalize_ass_time(event.end_time),
        comment=event.comment,
        actor=event.actor,
        margin_l=event.margin_l,
        margin_r=event.margin_r,
        margin_t=event.margin_t,
        margin_b=event.margin_b,
    )


def _normalize_json_payload(payload: dict[str, object]) -> dict[str, object]:
    normalized = dict(payload)
    events = cast(list[dict[str, object]], payload["events"])
    normalized_events: list[dict[str, object]] = []
    for event in events:
        normalized_event = dict(event)
        text = normalized_event.get("text")
        if isinstance(text, str):
            normalized_event["text"] = text.rstrip()
        for key in ("start_time", "end_time"):
            value = normalized_event.get(key)
            if isinstance(value, int | float):
                normalized_event[key] = _normalize_ass_time(value)
        normalized_events.append(normalized_event)
    normalized["events"] = normalized_events
    return normalized


def _scenario_id(scenario: CliAcceptanceScenario) -> str:
    return scenario.name


@pytest.mark.parametrize("fixture_path", ACCEPTANCE_FIXTURES, ids=_fixture_ids)
@pytest.mark.parametrize(
    "scenario",
    CLI_ACCEPTANCE_SCENARIOS,
    ids=_scenario_id,
)
def test_saved_acceptance_fixture_matches_cli_output(
    fixture_path: Path,
    scenario: CliAcceptanceScenario,
    tmp_path: Path,
) -> None:
    expected_document = build_saved_cli_document(fixture_path)
    expected_fx_events = [
        event
        for event in expected_document.events
        if event.effect.lower() == "fx"
    ]
    assert expected_fx_events, "Acceptance fixture must include fx snapshots."

    input_path = tmp_path / f"{fixture_path.stem}_{scenario.name}.input.ass"
    output_path = tmp_path / f"{fixture_path.stem}_{scenario.name}.ass"
    json_path = tmp_path / f"{fixture_path.stem}_{scenario.name}.json"
    extra_args = tuple(
        str(json_path) if value == "{json_output}" else value
        for value in scenario.extra_args
    )
    write_document(build_cli_input_document(fixture_path), input_path)

    result = run_cli(input_path, output_path, *extra_args)

    assert result.returncode == 0, result.stderr
    regenerated_document = load_document(output_path)

    assert regenerated_document.metadata == expected_document.metadata
    assert regenerated_document.styles == expected_document.styles
    assert [
        _normalize_event(event) for event in regenerated_document.events
    ] == [_normalize_event(event) for event in expected_document.events]

    if scenario.expect_json:
        assert _normalize_json_payload(
            load_json(json_path)
        ) == _normalize_json_payload(
            build_saved_cli_json_document(fixture_path)
        )


def test_basic_25_engine_output_is_stable_on_first_run(tmp_path: Path) -> None:
    fixture_path = ACCEPTANCE_DIR / "basic_25_code_line_function2.ass"
    input_path = tmp_path / "basic_25.input.ass"
    write_document(build_cli_input_document(fixture_path), input_path)

    def generate() -> list[Event]:
        document = load_cli_document(input_path)
        declarations = load_declarations(document)
        return run_engine(
            document,
            declarations,
            seed=1,
            font_dirs=(FONT_FIXTURE_DIR.resolve(),),
        )

    first_run = generate()
    second_run = generate()

    assert [_normalize_event(event) for event in first_run] == [
        _normalize_event(event) for event in second_run
    ]
