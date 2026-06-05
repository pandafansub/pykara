"""Unit tests for line preprocessing stages."""

# pyright: reportPrivateUsage=false

from __future__ import annotations

from dataclasses import dataclass

from pykara.data import Event, Highlight, Karaoke, Metadata, Style, Syllable
from pykara.processing.font_metrics import TextMeasurement
from pykara.processing.line_preprocessor import LinePreprocessor


@dataclass(slots=True)
class FakeExtentsProvider:
    """Deterministic text extents provider for isolated tests."""

    widths: dict[str, float]
    height: float = 20.0

    def measure(self, style: Style, text: str) -> TextMeasurement:
        del style
        return TextMeasurement(
            width=self.widths.get(text, 0.0),
            height=self.height,
            descent=4.0,
            extlead=0.0,
        )


def make_style(alignment: int = 2) -> Style:
    return Style(
        name="Default",
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
        alignment=alignment,
        margin_l=10,
        margin_r=15,
        margin_t=20,
        margin_b=25,
        encoding=1,
    )


def make_event() -> Event:
    return Event(
        text="{\\k20} ka {\\k30}to ",
        effect="karaoke",
        style="Default",
        layer=0,
        start_time=1000,
        end_time=1800,
        comment=False,
        actor="Singer",
        margin_l=0,
        margin_r=0,
        margin_t=0,
        margin_b=0,
    )


def make_karaoke() -> Karaoke:
    return Karaoke(
        text=" ka to ",
        trimmed_text="ka to",
        syllables=[
            Syllable(
                index=0,
                raw_text=" ka ",
                text=" ka ",
                trimmed_text="ka",
                prespace=" ",
                postspace=" ",
                start_time=0,
                end_time=200,
                duration=200,
                kdur=20.0,
                tag="\\k20",
                inline_fx="",
                highlights=[Highlight(0, 200, 200)],
            ),
            Syllable(
                index=1,
                raw_text="to ",
                text="to ",
                trimmed_text="to",
                prespace="",
                postspace=" ",
                start_time=200,
                end_time=500,
                duration=300,
                kdur=30.0,
                tag="\\k30",
                inline_fx="flash",
                highlights=[Highlight(200, 500, 300)],
            ),
        ],
    )


class TestLinePreprocessor:
    def build_preprocessor(self) -> LinePreprocessor:
        return LinePreprocessor(
            FakeExtentsProvider(
                widths={
                    " ka to ": 80.0,
                    "": 0.0,
                    " ": 5.0,
                    "ka": 20.0,
                    "to": 30.0,
                }
            )
        )

    def test_process_text_binds_runtime_line_and_style(self) -> None:
        preprocessor = self.build_preprocessor()

        text_stage = preprocessor._process_text(
            make_event(),
            make_karaoke(),
            make_style(),
        )

        assert text_stage.text == " ka to "
        assert text_stage.line.duration == 800
        assert text_stage.syllables[0].style.name == "Default"
        assert text_stage.syllables[1].source.trimmed_text == "to"

    def test_process_size_applies_video_x_correction(self) -> None:
        preprocessor = self.build_preprocessor()
        text_stage = preprocessor._process_text(
            make_event(),
            make_karaoke(),
            make_style(),
        )

        size_stage = preprocessor._process_size(
            text_stage,
            Metadata(res_x=1920, res_y=1080, video_x_correct_factor=1.5),
        )

        assert size_stage.width == 120.0
        assert size_stage.height == 20.0
        assert size_stage.syllables[0].width == 30.0
        assert size_stage.syllables[0].prespacewidth == 7.5
        assert size_stage.syllables[1].postspacewidth == 7.5

    def test_process_position_resolves_center_alignment(self) -> None:
        preprocessor = self.build_preprocessor()
        text_stage = preprocessor._process_text(
            make_event(),
            make_karaoke(),
            make_style(alignment=2),
        )
        size_stage = preprocessor._process_size(
            text_stage,
            Metadata(res_x=200, res_y=100),
        )

        positioned = preprocessor._process_position(
            size_stage,
            make_event(),
            Metadata(res_x=200, res_y=100),
            make_style(alignment=2),
        )

        assert positioned.left == 57.5
        assert positioned.center == 97.5
        assert positioned.right == 137.5
        assert positioned.top == 55.0
        assert positioned.middle == 65.0
        assert positioned.bottom == 75.0
        assert positioned.x == positioned.center
        assert positioned.y == positioned.bottom
        assert positioned.syllables[0].left == 62.5
        assert positioned.syllables[0].center == 72.5
        assert positioned.syllables[1].right == 117.5

    def test_preprocess_runs_full_pipeline(self) -> None:
        preprocessor = self.build_preprocessor()

        positioned = preprocessor.preprocess(
            make_event(),
            make_karaoke(),
            Metadata(res_x=200, res_y=100),
            make_style(alignment=7),
        )

        assert positioned.left == 10.0
        assert positioned.top == 20.0
        assert positioned.x == positioned.left
        assert positioned.y == positioned.top
        assert positioned.syllables[1].x == positioned.syllables[1].left
