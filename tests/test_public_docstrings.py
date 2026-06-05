"""Audit public API docstrings that phase 19 promises to review."""

from __future__ import annotations

import inspect
from collections.abc import Callable

from pykara.adapters import SubtitleReader, SubtitleWriter
from pykara.adapters.input.sub_station_alpha import SubStationAlphaReader
from pykara.adapters.output.json_adapter import JsonWriter
from pykara.adapters.output.sub_station_alpha import SubStationAlphaWriter
from pykara.engine import Engine
from pykara.interfaces.cli.args import build_parser
from pykara.interfaces.cli.main import main
from pykara.interfaces.cli.pipeline import (
    load_declarations,
    load_document,
    run_engine,
    run_validation,
    write_output,
)
from pykara.processing import FontMetricsProvider, LinePreprocessor
from pykara.validation.validators import CrossValidator, DocumentValidator


def _assert_docstring_has_sections(
    target: Callable[..., object],
    *,
    args: bool = False,
    returns: bool = False,
    raises: bool = False,
) -> None:
    docstring = inspect.getdoc(target)
    assert docstring is not None
    if args:
        assert "Args:" in docstring
    if returns:
        assert "Returns:" in docstring
    if raises:
        assert "Raises:" in docstring


def test_public_protocol_methods_have_structured_docstrings() -> None:
    _assert_docstring_has_sections(SubtitleReader.read, args=True, returns=True)
    _assert_docstring_has_sections(SubtitleWriter.write, args=True)


def test_public_adapters_have_structured_docstrings() -> None:
    _assert_docstring_has_sections(
        SubStationAlphaReader.read,
        args=True,
        returns=True,
        raises=True,
    )
    _assert_docstring_has_sections(SubStationAlphaWriter.write, args=True)
    _assert_docstring_has_sections(JsonWriter.write, args=True, raises=True)
    _assert_docstring_has_sections(JsonWriter.to_dict, args=True, returns=True)


def test_public_cli_functions_have_structured_docstrings() -> None:
    _assert_docstring_has_sections(build_parser, returns=True)
    _assert_docstring_has_sections(main, returns=True)
    _assert_docstring_has_sections(load_document, args=True, returns=True)
    _assert_docstring_has_sections(load_declarations, args=True, returns=True)
    _assert_docstring_has_sections(run_validation, args=True, returns=True)
    _assert_docstring_has_sections(run_engine, args=True, returns=True)
    _assert_docstring_has_sections(write_output, args=True)


def test_public_processing_validation_docstrings() -> None:
    _assert_docstring_has_sections(
        FontMetricsProvider.measure,
        args=True,
        returns=True,
    )
    _assert_docstring_has_sections(
        LinePreprocessor.preprocess, args=True, returns=True
    )
    _assert_docstring_has_sections(Engine.apply, args=True, returns=True)
    _assert_docstring_has_sections(
        CrossValidator.validate, args=True, returns=True
    )
    _assert_docstring_has_sections(
        DocumentValidator.validate, args=True, returns=True
    )
