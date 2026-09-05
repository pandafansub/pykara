"""Regression coverage for visible glyph bounds instead of font cells."""

# pyright: reportPrivateUsage=false

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path

import pytest

from pykara.data import Metadata, Style
from pykara.declaration import Scope
from pykara.declaration.template import TemplateBody, TemplateModifiers
from pykara.engine.engine import Engine
from pykara.motion import (
    GradientBox,
    GradientPlacement,
    GradientRequest,
    GradientStyleDefaults,
)
from pykara.motion.render import _resolved_box
from pykara.parsing import ParsedDeclarations, TemplateDeclaration
from pykara.processing import LinePreprocessor
from pykara.processing.font_metrics import FontMetricsProvider, TextMeasurement
from tests.effect_support import make_event, make_style


def font_provider() -> FontMetricsProvider:
    return FontMetricsProvider((Path(__file__).parent / "fixtures" / "fonts",))


def test_font_ink_excludes_cell_leading_and_trailing_spaces() -> None:
    provider = font_provider()
    style = replace(make_style(), fontname="Noto Sans", fontsize=75)
    capital = provider.measure_ink(style, "B")
    padded = provider.measure_ink(style, "B   ")
    descender = provider.measure_ink(style, "g")
    assert capital.ink_bounds is not None
    assert descender.ink_bounds is not None
    assert 0 < capital.ink_bounds[1] < capital.ink_bounds[3] < capital.height
    assert descender.ink_bounds[3] > capital.ink_bounds[3]
    assert padded.width > capital.width
    assert padded.ink_bounds == capital.ink_bounds
    assert provider.measure_ink(style, "   ").ink_bounds == (0, 0, 0, 0)


def test_font_ink_keeps_bearings_and_scales_with_font_and_spacing() -> None:
    provider = font_provider()
    style = replace(make_style(), fontname="Noto Sans", fontsize=40)
    base = provider.measure_ink(style, "BB")
    scaled = provider.measure_ink(
        replace(style, scale_x=150, scale_y=200),
        "BB",
    )
    spaced = provider.measure_ink(replace(style, spacing=5), "BB")
    assert base.ink_bounds is not None
    assert scaled.ink_bounds is not None
    assert spaced.ink_bounds is not None
    assert scaled.ink_bounds == pytest.approx(
        tuple(
            value * factor
            for value, factor in zip(
                base.ink_bounds, (1.5, 2, 1.5, 2), strict=True
            )
        )
    )
    assert spaced.ink_bounds[2] == pytest.approx(base.ink_bounds[2] + 5)
    # The final spacing advances the layout but adds no visible outline.
    assert spaced.width == pytest.approx(base.width + 10)


def ink_measurement(style: Style, text: str) -> TextMeasurement:
    assert text == "B"
    assert style.fontsize == 75
    return TextMeasurement(45, 75, 12, 0, (4, 17, 43, 62))


@pytest.mark.parametrize("alignment,top", [(8, 100), (5, 62.5), (2, 25)])
@pytest.mark.parametrize("shadow", [-8, 0, 8])
def test_clip_uses_ink_but_position_uses_layout(
    alignment: int,
    top: float,
    shadow: float,
) -> None:
    box = _resolved_box(
        GradientBox(0, 0, 45, 75, 22.5, 37.5),
        GradientStyleDefaults(75, 100, 100, 0, 2.5, shadow),
        GradientPlacement(1920, 1080, 8, 30, 30, 30, 30, False),
        replace(make_event(), text=rf"{{\an{alignment}\pos(200,100)}}B"),
        color_plane="fill",
        style=replace(make_style(), fontsize=75),
        measure_ink=ink_measurement,
    )
    assert (box.anchor_x, box.anchor_y) == (200, 100)
    assert box.top == top + 17 - 3.5 + min(0, shadow)
    assert box.bottom == top + 62 + 3.5 + max(0, shadow)
    assert box.left == 200 - 22.5 + 4 - 3.5 + min(0, shadow)
    assert box.right == 200 - 22.5 + 43 + 3.5 + max(0, shadow)


def test_shadow_gradient_uses_offset_ink_with_axis_overrides() -> None:
    box = _resolved_box(
        GradientBox(0, 0, 45, 75, 22.5, 37.5),
        GradientStyleDefaults(75, 100, 100, 0, 2.5, 0),
        GradientPlacement(1920, 1080, 8, 30, 30, 30, 30, False),
        replace(
            make_event(),
            text=(r"{\an7\pos(200,100)\xshad-8\yshad12\xbord2\ybord4\blur1}B"),
        ),
        color_plane="shadow",
        style=replace(make_style(), fontsize=75),
        measure_ink=ink_measurement,
    )
    assert (box.left, box.top, box.right, box.bottom) == (192, 123, 239, 180)


@pytest.mark.parametrize("scope", [Scope.LINE, Scope.SYL, Scope.CHAR])
def test_engine_gradient_uses_visible_font_extents(scope: Scope) -> None:
    provider = font_provider()
    style = replace(
        make_style(),
        fontname="Noto Sans",
        fontsize=75,
        outline=2.5,
        shadow=0,
    )
    template = TemplateDeclaration(
        body=TemplateBody(
            r"{\an5\pos(200,100)\1c"
            r"!gradient.make(['&H00E2FE&','&H163AE2&'], step=2)!\blur1}"
        ),
        scope=scope,
        modifiers=TemplateModifiers(),
    )
    declarations = ParsedDeclarations()
    getattr(declarations, scope.value).append(template)
    result = Engine(LinePreprocessor(provider)).apply(
        [make_event(r"{\k30}B")],
        declarations,
        Metadata(res_x=1920, res_y=1080, raw={"PlaybackFPS": "24"}),
        {"Default": style},
    )
    # A 75px cell plus padding used to generate 42 slices for every glyph.
    assert 10 < len(result) < 35
    assert all(r"\pos(200,100)" in event.text for event in result)


def test_gradient_measures_final_font_overrides() -> None:
    measured: list[Style] = []

    def measure(style: Style, text: str) -> TextMeasurement:
        measured.append(style)
        assert text == "B"
        return TextMeasurement(90, 150, 24, 0, (8, 34, 86, 124))

    box = _resolved_box(
        GradientBox(0, 0, 45, 75, 22.5, 37.5),
        GradientStyleDefaults(75, 100, 100, 0, 0, 0),
        GradientPlacement(1920, 1080, 8, 30, 30, 30, 30, False),
        replace(
            make_event(),
            text=(
                r"{\an5\pos(200,100)\fs150\fscx120\fscy200\fsp3"
                r"\fnNoto Sans\b1}B"
            ),
        ),
        color_plane="fill",
        style=make_style(),
        measure_ink=measure,
    )
    assert measured[0].fontsize == 150
    assert measured[0].scale_x == 120
    assert measured[0].scale_y == 200
    assert measured[0].spacing == 3
    assert measured[0].fontname == "Noto Sans"
    assert measured[0].bold
    assert box.top == 58
    assert box.bottom == 150


def test_scope_anchor_without_pos_matches_injected_position() -> None:
    box = _resolved_box(
        GradientBox(0, 0, 45, 75, 22.5, 37.5),
        GradientStyleDefaults(75, 100, 100, 0, 0, 0),
        GradientPlacement(1920, 1080, 8, 30, 30, 30, 30, False),
        replace(make_event(), text="B"),
        color_plane="fill",
        style=replace(make_style(), fontsize=75),
        measure_ink=ink_measurement,
    )
    assert box.anchor_y == 37.5
    assert box.top == 53.5
    assert box.bottom == 100.5


@pytest.mark.parametrize("alignment", [4, 5, 6])
@pytest.mark.parametrize("padding", ["chi ", " chi", " chi "])
@pytest.mark.parametrize(
    "transform",
    [
        r"\fscx150\fscy150\t(0,166,0.5,\fscx100\fscy100\blur5)",
        r"\fscx100\fscy100\t(0,166,0.5,\fscx150\fscy150\blur5)",
        r"\fs75\t(0,166,0.5,\fs110\blur5)",
    ],
)
def test_animated_gradient_ignores_discarded_edge_spaces(
    alignment: int,
    padding: str,
    transform: str,
) -> None:
    provider = font_provider()
    style = replace(make_style(), fontname="Noto Sans", fontsize=75)
    measurement = provider.measure(style, "chi")
    request = GradientRequest(
        placeholder="GRADIENT",
        colors=("&H22EDFD&", "&H0000FF&"),
        step=2,
        direction="top-bottom",
        box=GradientBox(0, 0, measurement.width, 75, 200, 100),
        style_defaults=GradientStyleDefaults(75, 100, 100, 0, 2, 1),
        placement=GradientPlacement(1920, 1080, 8, 30, 30, 30, 30, False),
        style=style,
        measure_ink=provider.measure_ink,
    )
    tags = rf"{{\an{alignment}\pos(200,100){transform}\1cGRADIENT}}"
    clean_event = replace(
        make_event(),
        text=tags + "chi",
        start_time=1000,
        end_time=1250,
    )
    clean = request.expand(clean_event, 24)
    padded = request.expand(replace(clean_event, text=tags + padding), 24)
    # Both strings render in the same place, including throughout growth.
    assert [event.text.removesuffix(padding) for event in padded] == [
        event.text.removesuffix("chi") for event in clean
    ]
    assert len({event.start_time for event in clean}) > 1
    assert (
        len(
            {re.findall(r"\\clip\(([^)]+)\)", event.text)[0] for event in clean}
        )
        > 1
    )


@pytest.mark.parametrize("text", [r"chi\h", r"\hchi", "c hi"])
def test_gradient_preserves_hard_and_internal_spaces(text: str) -> None:
    measured: list[str] = []

    def measure(style: Style, plain: str) -> TextMeasurement:
        del style
        measured.append(plain)
        return TextMeasurement(45, 75, 12, 0, (4, 17, 43, 62))

    _resolved_box(
        GradientBox(0, 0, 45, 75, 22.5, 37.5),
        GradientStyleDefaults(75, 100, 100, 0, 0, 0),
        GradientPlacement(1920, 1080, 8, 30, 30, 30, 30, False),
        replace(make_event(), text=rf"{{\an5\pos(200,100)}}{text}"),
        color_plane="fill",
        style=make_style(),
        measure_ink=measure,
    )
    assert measured == [text.replace(r"\h", "\N{NO-BREAK SPACE}")]
