#!/usr/bin/env python
"""Render all assets.shapes entries as PNG files for documentation."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path
from shutil import which

sys.path.insert(0, str(Path(__file__).parent.parent))
from pykara.engine.assets.shapes import SHAPES

OUTPUT_DIR = Path(__file__).parent.parent / "docs" / "tools" / "shapes"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SIZE = 128
PADDING_RATIO = 0.12
FILL_COLOR = "#000000"
INKSCAPE_BIN = which("inkscape")


def ass_to_svg_path(path_str: str) -> str:
    tokens = path_str.split()
    parts: list[str] = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t in ("m", "n"):
            parts.append(f"M {tokens[i + 1]} {tokens[i + 2]}")
            i += 3
        elif t == "l":
            parts.append(f"L {tokens[i + 1]} {tokens[i + 2]}")
            i += 3
        elif t == "b":
            parts.append(
                f"C {tokens[i + 1]} {tokens[i + 2]}"
                f" {tokens[i + 3]} {tokens[i + 4]}"
                f" {tokens[i + 5]} {tokens[i + 6]}"
            )
            i += 7
        elif t == "c":
            parts.append("Z")
            i += 1
        else:
            i += 1
    return " ".join(parts)


def shape_coords(path_str: str) -> tuple[float, float, float, float]:
    """Return (min_x, min_y, max_x, max_y) from all path coordinates."""
    tokens = path_str.split()
    xs: list[float] = []
    ys: list[float] = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t in ("m", "n", "l"):
            xs.append(float(tokens[i + 1]))
            ys.append(float(tokens[i + 2]))
            i += 3
        elif t == "b":
            for off in (1, 3, 5):
                xs.append(float(tokens[i + off]))
                ys.append(float(tokens[i + off + 1]))
            i += 7
        elif t == "c":
            i += 1
        else:
            i += 1
    if not xs:
        return 0.0, 0.0, 100.0, 100.0
    return min(xs), min(ys), max(xs), max(ys)


def square_viewbox(path_str: str) -> str:
    """Compute a square viewBox that fits the shape with padding."""
    min_x, min_y, max_x, max_y = shape_coords(path_str)
    w = max_x - min_x
    h = max_y - min_y
    side = max(w, h)
    pad = side * PADDING_RATIO
    side_padded = side + 2 * pad
    cx = (min_x + max_x) / 2
    cy = (min_y + max_y) / 2
    vx = cx - side_padded / 2
    vy = cy - side_padded / 2
    return f"{vx:.4f} {vy:.4f} {side_padded:.4f} {side_padded:.4f}"


def make_svg(path_str: str) -> str:
    svg_path = ass_to_svg_path(path_str)
    viewbox = square_viewbox(path_str)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg"'
        f' width="{SIZE}" height="{SIZE}"'
        f' viewBox="{viewbox}">'
        f'<path d="{svg_path}" fill="{FILL_COLOR}" fill-rule="evenodd"/>'
        f"</svg>"
    )


def render_shape(name: str, path_str: str) -> None:
    if INKSCAPE_BIN is None:
        msg = "inkscape executable not found in PATH"
        raise RuntimeError(msg)

    out_png = OUTPUT_DIR / f"{name}.png"
    svg_content = make_svg(path_str)
    with tempfile.NamedTemporaryFile(
        suffix=".svg", mode="w", delete=False
    ) as f:
        f.write(svg_content)
        svg_path = f.name

    subprocess.run(  # noqa: S603
        [
            INKSCAPE_BIN,
            svg_path,
            f"--export-filename={out_png}",
            f"--export-width={SIZE}",
            f"--export-height={SIZE}",
            "--export-background-opacity=0",
        ],
        check=True,
        capture_output=True,
    )
    Path(svg_path).unlink()
    print(f"  rendered {name}.png")


def main() -> None:
    print(f"Rendering {len(SHAPES)} shapes to {OUTPUT_DIR} ...")
    for name, path_str in SHAPES.items():
        render_shape(name, path_str)
    print("Done.")


if __name__ == "__main__":
    main()
