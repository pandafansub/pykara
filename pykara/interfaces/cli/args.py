"""CLI argument definitions."""

from __future__ import annotations

import argparse
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    """Build the Pykara CLI argument parser.

    Returns:
        Configured ``ArgumentParser`` for the ``pykara`` command-line
        interface.
    """

    parser = argparse.ArgumentParser(
        prog="pykara",
        description="Pykara Templater — apply karaoke template effects.",
    )
    parser.add_argument("input", type=Path, help="Input .ass file.")
    parser.add_argument("output", type=Path, help="Output .ass file.")
    parser.add_argument(
        "--json",
        type=Path,
        default=None,
        metavar="PATH",
        help="Also write output as JSON.",
    )
    parser.add_argument(
        "--warn-only",
        action="store_true",
        help="Print validation errors as warnings and continue.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        metavar="N",
        help=(
            "RNG seed for deterministic output. Without --seed, "
            "uses system entropy."
        ),
    )
    parser.add_argument(
        "--font-dir",
        action="append",
        type=Path,
        default=[],
        metavar="PATH",
        help=(
            "Directory containing fonts to prefer before user/system fonts. "
            "Can be passed more than once."
        ),
    )
    parser.add_argument(
        "--generated-only",
        action="store_true",
        help=(
            "Write only generated fx lines to the ASS output, without "
            "copying template or source karaoke events."
        ),
    )
    return parser
