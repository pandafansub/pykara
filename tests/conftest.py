"""Shared test setup."""

# pyright: reportPrivateUsage=false, reportUnknownMemberType=false

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from pykara.processing import font_metrics
from pykara.processing.font_metrics import reset_font_cache

if sys.platform != "win32":
    from matplotlib import font_manager

_FONT_PATH = (
    Path(__file__).parent / "fixtures" / "fonts" / "NotoSans-Regular.ttf"
)


@pytest.fixture(scope="session", autouse=True)
def register_test_fonts(tmp_path_factory: pytest.TempPathFactory) -> None:
    """Register bundled fonts and isolate matplotlib cache writes."""

    os.environ.setdefault(
        "MPLCONFIGDIR",
        str(tmp_path_factory.mktemp("mplconfig")),
    )
    if sys.platform != "win32":
        font_manager.fontManager.addfont(str(_FONT_PATH.resolve()))
    font_metrics._register_font_dirs_win32((_FONT_PATH.parent,))
    reset_font_cache()


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    """Keep Unix-only font shaping coverage off Windows."""

    del config
    if sys.platform != "win32":
        return

    skip_unix_only = pytest.mark.skip(
        reason="requires Unix-only font shaping dependencies",
    )
    unix_only_files = {
        "test_acceptance.py",
        "test_cli_acceptance_matrix.py",
        "test_font_metrics.py",
    }
    for item in items:
        if item.name == "test_measures_known_reference_text":
            item.add_marker(skip_unix_only)
            item.add_marker("unix_only")
            continue
        if item.path.name in unix_only_files:
            item.add_marker(skip_unix_only)
            item.add_marker("unix_only")
