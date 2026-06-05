"""Tests for acceptance helper utilities."""

from __future__ import annotations

from pathlib import Path

from tests.acceptance_support import FONT_FIXTURE_DIR, build_cli_command


def test_build_cli_command_adds_default_font_dir() -> None:
    command = build_cli_command(
        Path("input.ass"),
        Path("output.ass"),
        "--seed",
        "1",
        use_font_dir=True,
    )

    assert command[-2:] == ["--font-dir", str(FONT_FIXTURE_DIR)]


def test_build_cli_command_preserves_explicit_font_dir() -> None:
    command = build_cli_command(
        Path("input.ass"),
        Path("output.ass"),
        "--font-dir",
        "tests/fixtures/fonts",
        use_font_dir=True,
    )

    assert command.count("--font-dir") == 1
