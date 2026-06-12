"""CLI pipeline orchestration."""

from __future__ import annotations

from pathlib import Path

from pykara.adapters import SubtitleDocument
from pykara.adapters.input.sub_station_alpha import SubStationAlphaReader
from pykara.adapters.output.json_adapter import JsonWriter
from pykara.adapters.output.sub_station_alpha import SubStationAlphaWriter
from pykara.data import Event
from pykara.declaration.code import CODE_MODIFIER_REGISTRY
from pykara.declaration.mixin import MIXIN_MODIFIER_REGISTRY
from pykara.declaration.template import TEMPLATE_MODIFIER_REGISTRY
from pykara.engine import Engine
from pykara.fbf.timecodes import read_timecodes
from pykara.fbf.timeline import FrameRateSource
from pykara.parsing import DeclarationParser, ParsedDeclarations
from pykara.processing import FontMetricsProvider, LinePreprocessor
from pykara.validation.reports import ValidationReport
from pykara.validation.validators import DocumentValidator


def load_document(path: Path) -> SubtitleDocument:
    """Load one subtitle document from disk.

    Args:
        path: Input subtitle path.

    Returns:
        Loaded normalized subtitle document.
    """

    return strip_fx_events(
        SubStationAlphaReader().read(path, stop_at_generated_fx=True)
    )


def strip_fx_events(document: SubtitleDocument) -> SubtitleDocument:
    """Return ``document`` without previously generated ``fx`` events."""

    return SubtitleDocument(
        metadata=document.metadata,
        styles=document.styles,
        events=[
            event for event in document.events if event.effect.lower() != "fx"
        ],
    )


def load_declarations(
    document: SubtitleDocument,
    base_dir: Path | None = None,
) -> ParsedDeclarations:
    """Parse declarations from one loaded document.

    Args:
        document: Loaded subtitle document.

    Returns:
        Parsed declarations grouped by execution scope.
    """

    return DeclarationParser(
        template_mod_registry=TEMPLATE_MODIFIER_REGISTRY,
        mixin_mod_registry=MIXIN_MODIFIER_REGISTRY,
        code_mod_registry=CODE_MODIFIER_REGISTRY,
        base_dir=base_dir,
    ).parse(document.events)


def run_validation(
    document: SubtitleDocument,
    declarations: ParsedDeclarations,
) -> ValidationReport:
    """Run the document validator.

    Args:
        document: Loaded subtitle document.
        declarations: Parsed declarations for that document.

    Returns:
        Aggregated validation report.
    """

    return DocumentValidator().validate(document, declarations)


def run_engine(
    document: SubtitleDocument,
    declarations: ParsedDeclarations,
    seed: int | None = None,
    font_dirs: tuple[Path, ...] = (),
    fbf_framerate: FrameRateSource | None = None,
) -> list[Event]:
    """Generate fx events through the core engine.

    Args:
        document: Loaded subtitle document.
        declarations: Parsed declarations for that document.
        seed: Optional deterministic random seed.
        font_dirs: Optional directories containing fonts.
        fbf_framerate: Optional explicit frame/time source for FBF effects.

    Returns:
        Generated ``fx`` events.
    """

    preprocessor = LinePreprocessor(
        extents=FontMetricsProvider(font_dirs=font_dirs),
    )
    return Engine(preprocessor, seed=seed, fbf_framerate=fbf_framerate).apply(
        document.events,
        declarations,
        document.metadata,
        document.styles,
    )


def load_cli_framerate(
    fps: float | None,
    timecodes_path: Path | None,
) -> FrameRateSource | None:
    """Load the CLI-provided frame/time source, if any."""

    if fps is not None:
        return fps
    if timecodes_path is not None:
        return read_timecodes(timecodes_path)
    return None


def write_output(
    document: SubtitleDocument,
    fx_events: list[Event],
    output_path: Path,
    json_path: Path | None,
    generated_only: bool = False,
) -> None:
    """Write the merged output document to ASS and optional JSON.

    Args:
        document: Original loaded subtitle document.
        fx_events: Generated ``fx`` events to append.
        output_path: Destination ASS file path.
        json_path: Optional JSON output path.
        generated_only: Whether to keep only generated ``fx`` lines in the
            ASS output.
    """

    source_document = strip_fx_events(document)
    source_events = _copy_source_events(source_document)
    output_events = (
        fx_events if generated_only else [*source_events, *fx_events]
    )
    output_document = SubtitleDocument(
        metadata=source_document.metadata,
        styles=source_document.styles,
        events=output_events,
    )
    SubStationAlphaWriter().write(output_document, output_path)
    if json_path is not None:
        JsonWriter().write(output_document, json_path)


def _copy_source_events(document: SubtitleDocument) -> list[Event]:
    """Copy source events for output, commenting original karaoke lines."""

    return [
        Event(
            text=event.text,
            effect=event.effect,
            style=event.style,
            layer=event.layer,
            start_time=event.start_time,
            end_time=event.end_time,
            comment=(
                True if event.effect.lower() == "karaoke" else event.comment
            ),
            actor=event.actor,
            margin_l=event.margin_l,
            margin_r=event.margin_r,
            margin_t=event.margin_t,
            margin_b=event.margin_b,
        )
        for event in document.events
    ]
