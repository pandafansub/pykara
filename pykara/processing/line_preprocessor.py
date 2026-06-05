"""Line preprocessing stages for text, sizing, and positioning."""

from __future__ import annotations

from dataclasses import dataclass

from pykara.data import Event, Karaoke, Metadata, Style
from pykara.data.events import RuntimeLine
from pykara.data.events.karaoke import Syllable
from pykara.processing.font_metrics import TextExtentsProvider


@dataclass(frozen=True, slots=True)
class TextSyllable:
    """Syllable data after text-only preprocessing."""

    source: Syllable
    style: Style


@dataclass(frozen=True, slots=True)
class SizedSyllable:
    """Syllable data after text measurement."""

    source: Syllable
    style: Style
    width: float
    height: float
    prespacewidth: float
    postspacewidth: float


@dataclass(frozen=True, slots=True)
class TextProcessedLine:
    """Line data after text-only preprocessing."""

    line: RuntimeLine
    text: str
    syllables: tuple[TextSyllable, ...]


@dataclass(frozen=True, slots=True)
class SizedLine:
    """Line data after size measurement."""

    line: RuntimeLine
    text: str
    syllables: tuple[SizedSyllable, ...]
    width: float
    height: float


@dataclass(frozen=True, slots=True)
class PositionedLine:
    """Line data after coordinate resolution."""

    line: RuntimeLine
    text: str
    syllables: tuple[Syllable, ...]
    width: float
    height: float
    left: float
    center: float
    right: float
    top: float
    middle: float
    bottom: float
    x: float
    y: float


class LinePreprocessor:
    """Prepare karaoke lines for engine execution."""

    def __init__(self, extents: TextExtentsProvider) -> None:
        self._extents = extents

    @property
    def extents(self) -> TextExtentsProvider:
        """Expose the configured measurement provider."""

        return self._extents

    def preprocess(
        self,
        event: Event,
        karaoke: Karaoke,
        metadata: Metadata,
        style: Style,
    ) -> PositionedLine:
        """Run the full preprocessing pipeline.

        Args:
            event: Source karaoke event.
            karaoke: Parsed karaoke payload for the event.
            metadata: Script-level metadata.
            style: Resolved base style for the event.

        Returns:
            Fully positioned line ready for engine execution.
        """

        text_stage = self._process_text(event, karaoke, style)
        size_stage = self._process_size(text_stage, metadata)
        return self._process_position(size_stage, event, metadata, style)

    def _process_text(
        self,
        event: Event,
        karaoke: Karaoke,
        style: Style,
    ) -> TextProcessedLine:
        """Bind text, style, and runtime line data."""

        runtime_line = RuntimeLine(
            event=event,
            styleref=style,
            duration=event.end_time - event.start_time,
        )
        syllables = tuple(
            TextSyllable(source=syllable, style=style)
            for syllable in karaoke.syllables
        )
        return TextProcessedLine(
            line=runtime_line,
            text=karaoke.text,
            syllables=syllables,
        )

    def _process_size(
        self,
        line: TextProcessedLine,
        metadata: Metadata,
    ) -> SizedLine:
        """Measure line and syllable sizes."""

        line_measurement = self._extents.measure(line.line.styleref, line.text)
        x_factor = metadata.video_x_correct_factor

        sized_syllables = tuple(
            self._measure_syllable(text_syllable, x_factor)
            for text_syllable in line.syllables
        )
        return SizedLine(
            line=line.line,
            text=line.text,
            syllables=sized_syllables,
            width=line_measurement.width * x_factor,
            height=line_measurement.height,
        )

    def _process_position(
        self,
        line: SizedLine,
        event: Event,
        metadata: Metadata,
        style: Style,
    ) -> PositionedLine:
        """Resolve line and syllable coordinates from alignment and margins."""

        margin_left = event.margin_l if event.margin_l > 0 else style.margin_l
        margin_right = event.margin_r if event.margin_r > 0 else style.margin_r
        margin_top = event.margin_t if event.margin_t > 0 else style.margin_t
        margin_bottom = event.margin_b if event.margin_b > 0 else style.margin_b

        left = self._resolve_line_left(
            alignment=style.alignment,
            res_x=metadata.res_x,
            margin_left=margin_left,
            margin_right=margin_right,
            line_width=line.width,
        )
        top, middle, bottom = self._resolve_line_vertical_box(
            alignment=style.alignment,
            res_y=metadata.res_y,
            margin_top=margin_top,
            margin_bottom=margin_bottom,
            line_height=line.height,
        )
        center = left + line.width / 2
        right = left + line.width
        x = self._resolve_anchor_x(style.alignment, left, center, right)
        y = self._resolve_anchor_y(style.alignment, top, middle, bottom)

        positioned_syllables: list[Syllable] = []
        cursor = left
        for sized_syllable in line.syllables:
            source = sized_syllable.source
            visible_left = cursor + sized_syllable.prespacewidth
            visible_center = visible_left + sized_syllable.width / 2
            visible_right = visible_left + sized_syllable.width

            source.style = sized_syllable.style
            source.width = sized_syllable.width
            source.height = sized_syllable.height
            source.prespacewidth = sized_syllable.prespacewidth
            source.postspacewidth = sized_syllable.postspacewidth
            source.left = visible_left
            source.center = visible_center
            source.right = visible_right
            source.top = top
            source.middle = middle
            source.bottom = bottom
            source.x = self._resolve_anchor_x(
                style.alignment,
                visible_left,
                visible_center,
                visible_right,
            )
            source.y = y
            positioned_syllables.append(source)

            cursor += (
                sized_syllable.prespacewidth
                + sized_syllable.width
                + sized_syllable.postspacewidth
            )

        return PositionedLine(
            line=line.line,
            text=line.text,
            syllables=tuple(positioned_syllables),
            width=line.width,
            height=line.height,
            left=left,
            center=center,
            right=right,
            top=top,
            middle=middle,
            bottom=bottom,
            x=x,
            y=y,
        )

    def _measure_syllable(
        self,
        syllable: TextSyllable,
        x_factor: float,
    ) -> SizedSyllable:
        """Measure one syllable and surrounding spaces."""

        source = syllable.source
        text_measurement = self._extents.measure(
            syllable.style,
            source.trimmed_text,
        )
        prespace_measurement = self._extents.measure(
            syllable.style,
            source.prespace,
        )
        postspace_measurement = self._extents.measure(
            syllable.style,
            source.postspace,
        )
        return SizedSyllable(
            source=source,
            style=syllable.style,
            width=text_measurement.width * x_factor,
            height=text_measurement.height,
            prespacewidth=prespace_measurement.width * x_factor,
            postspacewidth=postspace_measurement.width * x_factor,
        )

    def _resolve_line_left(
        self,
        *,
        alignment: int,
        res_x: int,
        margin_left: int,
        margin_right: int,
        line_width: float,
    ) -> float:
        """Resolve the line left coordinate for the current alignment."""

        if alignment in {1, 4, 7}:
            return float(margin_left)
        if alignment in {2, 5, 8}:
            return (
                res_x - margin_left - margin_right - line_width
            ) / 2 + margin_left
        return float(res_x - margin_right) - line_width

    def _resolve_line_vertical_box(
        self,
        *,
        alignment: int,
        res_y: int,
        margin_top: int,
        margin_bottom: int,
        line_height: float,
    ) -> tuple[float, float, float]:
        """Resolve the vertical line box for the current alignment."""

        if alignment in {1, 2, 3}:
            bottom = float(res_y - margin_bottom)
            return (
                bottom - line_height,
                bottom - line_height / 2,
                bottom,
            )
        if alignment in {4, 5, 6}:
            top = (
                res_y - margin_top - margin_bottom - line_height
            ) / 2 + margin_top
            return (top, top + line_height / 2, top + line_height)
        top = float(margin_top)
        return (top, top + line_height / 2, top + line_height)

    def _resolve_anchor_x(
        self,
        alignment: int,
        left: float,
        center: float,
        right: float,
    ) -> float:
        """Resolve horizontal anchor from alignment."""

        if alignment in {1, 4, 7}:
            return left
        if alignment in {2, 5, 8}:
            return center
        return right

    def _resolve_anchor_y(
        self,
        alignment: int,
        top: float,
        middle: float,
        bottom: float,
    ) -> float:
        """Resolve vertical anchor from alignment."""

        if alignment in {1, 2, 3}:
            return bottom
        if alignment in {4, 5, 6}:
            return middle
        return top
