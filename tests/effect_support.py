"""Shared helpers for motion and gradient tests."""

from __future__ import annotations

from dataclasses import dataclass

from pykara.data import Event, Style
from pykara.engine import GeneratedLine
from pykara.engine.engine import Engine
from pykara.processing import LinePreprocessor, TextMeasurement


@dataclass(slots=True)
class FakeExtentsProvider:
    widths: dict[str, float]

    def measure(self, style: Style, text: str) -> TextMeasurement:
        del style
        return TextMeasurement(
            width=self.widths.get(text, float(len(text) * 10)),
            height=20.0,
            descent=4.0,
            extlead=0.0,
        )


def make_style(name: str = "Default") -> Style:
    return Style(
        name=name,
        fontname="Arial",
        fontsize=40.0,
        primary_colour="&H00FFFFFF",
        secondary_colour="&H0000FFFF",
        outline_colour="&H00000000",
        back_colour="&H64000000",
        bold=False,
        italic=False,
        underline=False,
        strike_out=False,
        scale_x=100.0,
        scale_y=100.0,
        spacing=0.0,
        angle=0.0,
        border_style=1,
        outline=2.0,
        shadow=1.0,
        alignment=2,
        margin_l=10,
        margin_r=10,
        margin_t=10,
        margin_b=10,
        encoding=1,
    )


def make_event(text: str = r"{\k20}go{\k30}al") -> Event:
    return Event(
        text=text,
        effect="karaoke",
        style="Default",
        layer=0,
        start_time=1000,
        end_time=1500,
        comment=False,
        actor="Singer",
        margin_l=0,
        margin_r=0,
        margin_t=0,
        margin_b=0,
    )


def make_generated_line() -> GeneratedLine:
    return GeneratedLine.from_event(make_event(), make_style())


def build_engine() -> Engine:
    extents = FakeExtentsProvider(
        {
            "goal": 40.0,
            "": 0.0,
            "go": 20.0,
            "al": 20.0,
            "g": 10.0,
            "o": 10.0,
            "a": 10.0,
            "l": 10.0,
        }
    )
    return Engine(LinePreprocessor(extents), seed=1)
