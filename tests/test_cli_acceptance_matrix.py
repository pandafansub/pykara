"""CLI acceptance matrix for public API coverage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict, cast

import pytest

from pykara.data import Event
from pykara.specification import (
    DECLARATIONS,
    FUNCTION_SPECIFICATIONS,
    MODIFIER_SPECIFICATIONS,
    SCOPE_SPECIFICATIONS,
    VARIABLE_SPECIFICATIONS,
)
from tests.acceptance_support import load_document, load_json, run_cli

TESTS_DIR = Path(__file__).parent
MANIFEST_PATH = TESTS_DIR / "fixtures" / "cli_acceptance" / "manifest.json"

pytestmark = pytest.mark.unix_only


class CaseExpectBase(TypedDict):
    exit_code: int


class CaseExpect(CaseExpectBase, total=False):
    stdout_contains: list[str]
    stderr_contains: list[str]
    fx_texts: list[str]
    fx_layers: list[int]
    fx_styles: list[str]
    fx_times: list[list[int]]
    json_fx_texts: list[str]


class AcceptanceCase(TypedDict):
    id: str
    fixture: str
    args: list[str]
    expect: CaseExpect


class CoverageInventory(TypedDict):
    declarations: dict[str, list[str]]
    modifiers: dict[str, list[str]]
    functions: dict[str, list[str]]
    variable_groups: dict[str, list[str]]
    cli_flags: dict[str, list[str]]


class Manifest(TypedDict):
    cases: list[AcceptanceCase]
    coverage_inventory: CoverageInventory


class JsonEvent(TypedDict):
    effect: str
    text: str


class JsonDocument(TypedDict):
    events: list[JsonEvent]


def _load_manifest() -> Manifest:
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return cast(Manifest, payload)


MANIFEST = _load_manifest()
CASES = tuple(MANIFEST["cases"])


def _fx_events_from_output(path: Path) -> list[Event]:
    """Return generated fx events from one rendered ASS output."""

    document = load_document(path)
    return [event for event in document.events if event.effect.lower() == "fx"]


def _case_id(case: AcceptanceCase) -> str:
    return case["id"]


@pytest.mark.parametrize("case", CASES, ids=_case_id)
def test_cli_acceptance_case(
    case: AcceptanceCase,
    tmp_path: Path,
) -> None:
    fixture_path = Path(case["fixture"])
    output_path = tmp_path / f"{fixture_path.stem}.out.ass"
    json_path = tmp_path / f"{fixture_path.stem}.out.json"
    args = [
        str(json_path) if value == "{json_output}" else str(value)
        for value in case["args"]
    ]
    expect = case["expect"]

    result = run_cli(fixture_path, output_path, *args)

    assert result.returncode == expect["exit_code"]

    for snippet in expect.get("stdout_contains", []):
        assert snippet in result.stdout
    for snippet in expect.get("stderr_contains", []):
        assert snippet in result.stderr

    if "fx_texts" in expect:
        fx_events = _fx_events_from_output(output_path)
        assert [event.text for event in fx_events] == expect["fx_texts"]

        if "fx_layers" in expect:
            assert [event.layer for event in fx_events] == expect["fx_layers"]
        if "fx_styles" in expect:
            assert [event.style for event in fx_events] == expect["fx_styles"]
        if "fx_times" in expect:
            assert [
                [event.start_time, event.end_time] for event in fx_events
            ] == expect["fx_times"]

    if "json_fx_texts" in expect:
        payload = cast(JsonDocument, load_json(json_path))
        fx_events = [
            event
            for event in payload["events"]
            if str(event["effect"]).lower() == "fx"
        ]
        assert [event["text"] for event in fx_events] == expect["json_fx_texts"]


def test_cli_acceptance_inventory_covers_public_spec() -> None:
    manifest = MANIFEST["coverage_inventory"]
    case_ids = {case["id"] for case in CASES}

    expected_declarations = {
        f"{name}:{scope.value}"
        for name, spec in DECLARATIONS.items()
        for scope in spec.allowed_scopes
    }
    expected_modifiers = {
        f"{kind}:{modifier.keyword}"
        for modifier in MODIFIER_SPECIFICATIONS.values()
        for kind in modifier.applicable_to
    }
    expected_functions = set(FUNCTION_SPECIFICATIONS)
    expected_variable_groups = {
        group
        for group in {
            *(spec.variable_groups for spec in SCOPE_SPECIFICATIONS.values()),
            *(spec.group for spec in VARIABLE_SPECIFICATIONS.values()),
        }
        if isinstance(group, str)
    }
    expected_variable_groups.update(
        {
            group
            for scope_spec in SCOPE_SPECIFICATIONS.values()
            for group in scope_spec.variable_groups
        }
    )
    expected_cli_flags = {
        "--seed",
        "--json",
        "--fps",
        "--timecodes",
        "--warn-only",
        "--font-dir",
        "--generated-only",
    }

    assert set(manifest["declarations"]) == expected_declarations
    assert set(manifest["modifiers"]) == expected_modifiers
    assert set(manifest["functions"]) == expected_functions
    assert set(manifest["variable_groups"]) == expected_variable_groups
    assert set(manifest["cli_flags"]) == expected_cli_flags

    for section in (
        manifest["declarations"],
        manifest["modifiers"],
        manifest["functions"],
        manifest["variable_groups"],
        manifest["cli_flags"],
    ):
        for references in section.values():
            for reference in references:
                if reference.startswith("case:"):
                    assert reference.removeprefix("case:") in case_ids
                    continue
                assert Path(reference).exists(), reference
