"""Keep blurred gradient halos intact without adding empty slices."""

from __future__ import annotations

import math
import re
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from pykara.adapters import SubtitleDocument
from pykara.adapters.output import SubStationAlphaWriter
from pykara.data import Metadata
from pykara.fbf.expansion import line_to_fbf
from pykara.motion import (
    GradientBox,
    GradientPlacement,
    GradientRequest,
    GradientStyleDefaults,
    MultiGradientRequest,
)
from pykara.processing.font_metrics import FontMetricsProvider
from tests.effect_support import make_event, make_style


def make_request(direction: str, step: float) -> GradientRequest:
    return GradientRequest(
        placeholder="GRADIENT",
        colors=("&H0000FF&", "&HFF0000&"),
        step=step,
        direction=direction,
        box=GradientBox(180, 80, 220, 120, 200, 100),
        style_defaults=GradientStyleDefaults(75, 100, 100, 0, 0, 0),
        placement=GradientPlacement(400, 200, 5, 0, 0, 0, 0, False),
    )


@pytest.mark.parametrize(
    "direction",
    ["top-bottom", "bottom-top", "left-right", "right-left"],
)
@pytest.mark.parametrize("step", [2, 1000])
@pytest.mark.parametrize("multiple", [False, True])
@pytest.mark.parametrize("blur_tag,pad", [(r"\blur5", 6), (r"\be3", 4)])
def test_blurred_slices_cover_viewport_without_extra_lines(
    direction: str,
    step: float,
    multiple: bool,
    blur_tag: str,
    pad: int,
) -> None:
    request = make_request(direction, step)
    event = replace(
        make_event(),
        text=rf"{{\an5\pos(200,100){blur_tag}\1cGRADIENT}}star",
    )
    if multiple:
        second = replace(request, placeholder="SECOND", step=step * 2)
        event.text = event.text.replace("}", r"\3cSECOND}")
        result = MultiGradientRequest((request, second)).expand(event, 24)
    else:
        result = request.expand(event, 24)
    assert len(result) == math.ceil((40 + 2 * pad) / step)
    clips: list[tuple[float, ...]] = []
    for line in result:
        match = re.search(r"\\clip\(([^)]+)\)", line.text)
        assert match is not None
        clips.append(tuple(float(value) for value in match[1].split(",")))
    if direction in {"top-bottom", "bottom-top"}:
        assert all(clip[0] == 0 and clip[2] == 400 for clip in clips)
        assert clips[0][1] == 0
        assert clips[-1][3] == 200
        if len(clips) > 1:
            assert clips[0][3] == 80 - pad + step + 1
    else:
        assert all(clip[1] == 0 and clip[3] == 200 for clip in clips)
        assert clips[0][0] == 0
        assert clips[-1][2] == 400
        if len(clips) > 1:
            assert clips[0][2] == 180 - pad + step + 1


@pytest.mark.parametrize("direction", ["top-bottom", "left-right"])
@pytest.mark.parametrize("blur", [1, 5, 12])
def test_animated_blur_matches_unclipped_libass_rendering(
    tmp_path: Path,
    direction: str,
    blur: int,
) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        pytest.skip("requires FFmpeg with the libass filter")
    filters = subprocess.run(  # noqa: S603
        [ffmpeg, "-hide_banner", "-filters"],
        capture_output=True,
        check=True,
        text=True,
        timeout=30,
    ).stdout
    if " ass " not in filters:
        pytest.skip("requires FFmpeg with the libass filter")
    font_dir = Path(__file__).parent / "fixtures" / "fonts"
    target_fonts = tmp_path / "fonts"
    target_fonts.mkdir()
    shutil.copyfile(
        font_dir / "NotoSans-Regular.ttf",
        target_fonts / "NotoSans-Regular.ttf",
    )
    provider = FontMetricsProvider((font_dir,))
    style = replace(make_style(), fontname="Noto Sans", fontsize=75, shadow=0)
    request = replace(
        make_request(direction, 1000),
        colors=("&HFFFFFF&", "&HFFFFFF&"),
        style=style,
        measure_ink=provider.measure_ink,
        style_defaults=GradientStyleDefaults(75, 100, 100, 0, 2, 0),
    )
    event = replace(
        make_event(),
        start_time=0,
        end_time=250,
        text=(
            r"{\an5\pos(200,100)\1cGRADIENT\3c&HFFFFFF&"
            rf"\fscx150\fscy150\blur{blur}"
            r"\t(0,250,\fscx100\fscy100\blur0.6)}star"
        ),
    )
    rendered: list[bytes] = []
    for name, events in (
        ("gradient", request.expand(event, 24)),
        (
            "reference",
            line_to_fbf(
                replace(
                    event, text=event.text.replace("GRADIENT", "&HFFFFFF&")
                ),
                24,
            ),
        ),
    ):
        SubStationAlphaWriter().write(
            SubtitleDocument(
                metadata=Metadata(
                    400,
                    200,
                    raw={
                        "ScriptType": "v4.00+",
                        "ScaledBorderAndShadow": "yes",
                    },
                ),
                styles={style.name: style},
                events=events,
            ),
            tmp_path / f"{name}.ass",
        )
        rendered.append(
            subprocess.run(  # noqa: S603
                [
                    ffmpeg,
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=c=black:s=400x200:r=24",
                    "-vf",
                    f"ass={name}.ass:fontsdir=fonts,format=gray",
                    "-frames:v",
                    "6",
                    "-f",
                    "rawvideo",
                    "-",
                ],
                cwd=tmp_path,
                capture_output=True,
                check=True,
                timeout=30,
            ).stdout
        )
    assert len(rendered[0]) == 400 * 200 * 6
    assert max(rendered[1]) > 200  # Ensure the reference actually drew text.
    assert rendered[0] == rendered[1]
