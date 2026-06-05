"""Unit tests for pykara.errors — every class carries its structured fields."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pykara.errors import (
    AdapterError,
    BoundMethodInExpressionError,
    DeclarativeParseError,
    DocumentReadError,
    DocumentWriteError,
    EngineError,
    ExecutionAttributeUnavailableError,
    KaraokeParseError,
    LinePreprocessingError,
    ModifierParseError,
    ParsingError,
    ProcessingError,
    PykaraError,
    ReservedNameError,
    TemplateCodeError,
    TemplateExecutionCancelledError,
    TemplateRuntimeError,
    UnknownModifierError,
    UnknownVariableError,
    ValidationError,
)


def make_report(error_count: int = 1) -> MagicMock:
    report = MagicMock()
    report.errors = (MagicMock(),) * error_count
    return report


class TestPykaraError:
    def test_is_exception(self) -> None:
        assert issubclass(PykaraError, Exception)

    def test_can_be_raised(self) -> None:
        with pytest.raises(PykaraError):
            raise PykaraError("base error")


class TestAdapterError:
    def test_inherits_from_pykara_error(self) -> None:
        assert issubclass(AdapterError, PykaraError)


class TestDocumentReadError:
    def test_stores_path(self) -> None:
        path = Path("input.ass")
        err = DocumentReadError(path)
        assert err.path == path

    def test_inherits_from_adapter_error(self) -> None:
        assert issubclass(DocumentReadError, AdapterError)

    def test_default_message_contains_path(self) -> None:
        path = Path("input.ass")
        assert str(path) in str(DocumentReadError(path))

    def test_custom_message(self) -> None:
        err = DocumentReadError(Path("x.ass"), message="custom")
        assert str(err) == "custom"


class TestDocumentWriteError:
    def test_stores_path(self) -> None:
        path = Path("out.ass")
        err = DocumentWriteError(path)
        assert err.path == path

    def test_inherits_from_adapter_error(self) -> None:
        assert issubclass(DocumentWriteError, AdapterError)

    def test_default_message_contains_path(self) -> None:
        path = Path("out.ass")
        assert str(path) in str(DocumentWriteError(path))

    def test_custom_message(self) -> None:
        err = DocumentWriteError(Path("x.ass"), message="disk full")
        assert str(err) == "disk full"


class TestKaraokeParseError:
    def test_stores_event_text(self) -> None:
        err = KaraokeParseError("hello world")
        assert err.event_text == "hello world"

    def test_inherits_from_parsing_error(self) -> None:
        assert issubclass(KaraokeParseError, ParsingError)

    def test_inherits_from_pykara_error(self) -> None:
        assert issubclass(KaraokeParseError, PykaraError)

    def test_default_message_contains_event_text(self) -> None:
        err = KaraokeParseError("hello world")
        assert "hello world" in str(err)

    def test_custom_message(self) -> None:
        err = KaraokeParseError("bad", message="unexpected tag")
        assert str(err) == "unexpected tag"


class TestDeclarativeParseError:
    def test_stores_effect_field(self) -> None:
        err = DeclarativeParseError("template")
        assert err.effect_field == "template"

    def test_inherits_from_parsing_error(self) -> None:
        assert issubclass(DeclarativeParseError, ParsingError)

    def test_default_message_contains_effect_field(self) -> None:
        err = DeclarativeParseError("template")
        assert "template" in str(err)

    def test_empty_effect_field_is_allowed(self) -> None:
        err = DeclarativeParseError()
        assert err.effect_field == ""

    def test_custom_message(self) -> None:
        err = DeclarativeParseError("template", message="scope required")
        assert str(err) == "scope required"


class TestUnknownModifierError:
    def test_stores_modifier(self) -> None:
        err = UnknownModifierError(modifier="foobar")
        assert err.modifier == "foobar"

    def test_stores_effect_field(self) -> None:
        err = UnknownModifierError(
            modifier="foobar", effect_field="template syl foobar"
        )
        assert err.effect_field == "template syl foobar"

    def test_inherits_from_declarative_parse_error(self) -> None:
        assert issubclass(UnknownModifierError, DeclarativeParseError)

    def test_default_message_contains_modifier(self) -> None:
        err = UnknownModifierError(modifier="foobar")
        assert "foobar" in str(err)

    def test_effect_field_defaults_to_empty(self) -> None:
        err = UnknownModifierError(modifier="x")
        assert err.effect_field == ""


class TestModifierParseError:
    def test_stores_modifier_and_reason(self) -> None:
        err = ModifierParseError("loop", "expected number after 'loop'")
        assert err.modifier == "loop"
        assert err.reason == "expected number after 'loop'"

    def test_stores_effect_field(self) -> None:
        err = ModifierParseError(
            "loop", "reason", effect_field="template syl loop"
        )
        assert err.effect_field == "template syl loop"

    def test_inherits_from_declarative_parse_error(self) -> None:
        assert issubclass(ModifierParseError, DeclarativeParseError)

    def test_default_message_contains_modifier_and_reason(self) -> None:
        err = ModifierParseError("loop", "expected number")
        msg = str(err)
        assert "loop" in msg
        assert "expected number" in msg

    def test_effect_field_defaults_to_empty(self) -> None:
        err = ModifierParseError("fx", "reason")
        assert err.effect_field == ""


class TestValidationError:
    def test_stores_report(self) -> None:
        report = make_report(error_count=2)
        err = ValidationError(report)
        assert err.report is report

    def test_inherits_from_pykara_error(self) -> None:
        assert issubclass(ValidationError, PykaraError)

    def test_message_contains_error_count(self) -> None:
        report = make_report(error_count=3)
        err = ValidationError(report)
        assert "3" in str(err)


class TestLinePreprocessingError:
    def test_stores_event_text(self) -> None:
        err = LinePreprocessingError("hello world")
        assert err.event_text == "hello world"

    def test_inherits_from_processing_error(self) -> None:
        assert issubclass(LinePreprocessingError, ProcessingError)

    def test_inherits_from_pykara_error(self) -> None:
        assert issubclass(LinePreprocessingError, PykaraError)

    def test_default_message_contains_event_text(self) -> None:
        assert "hello world" in str(LinePreprocessingError("hello world"))

    def test_custom_message(self) -> None:
        err = LinePreprocessingError("x", message="bad font")
        assert str(err) == "bad font"


class TestTemplateCodeError:
    def test_stores_source_and_cause(self) -> None:
        cause = SyntaxError("invalid syntax")
        err = TemplateCodeError("def f(: pass", cause)
        assert err.source == "def f(: pass"
        assert err.cause is cause

    def test_inherits_from_engine_error(self) -> None:
        assert issubclass(TemplateCodeError, EngineError)

    def test_message_contains_cause(self) -> None:
        cause = SyntaxError("invalid syntax")
        err = TemplateCodeError("bad code", cause)
        assert "invalid syntax" in str(err)


class TestExecutionAttributeUnavailableError:
    def test_stores_attribute_name(self) -> None:
        err = ExecutionAttributeUnavailableError("style")
        assert err.attribute_name == "style"

    def test_inherits_from_engine_error(self) -> None:
        assert issubclass(ExecutionAttributeUnavailableError, EngineError)

    def test_message_contains_attribute_name(self) -> None:
        err = ExecutionAttributeUnavailableError("metadata")
        assert "metadata" in str(err)


class TestTemplateRuntimeError:
    def test_stores_source_and_cause(self) -> None:
        cause = ZeroDivisionError("division by zero")
        err = TemplateRuntimeError("1/0", cause)
        assert err.source == "1/0"
        assert err.cause is cause

    def test_inherits_from_engine_error(self) -> None:
        assert issubclass(TemplateRuntimeError, EngineError)

    def test_message_contains_cause(self) -> None:
        cause = ZeroDivisionError("division by zero")
        err = TemplateRuntimeError("1/0", cause)
        assert "division by zero" in str(err)


class TestReservedNameError:
    def test_stores_fields(self) -> None:
        err = ReservedNameError("color", "color = '#fff'")
        assert err.name == "color"
        assert err.source == "color = '#fff'"

    def test_inherits_from_engine_error(self) -> None:
        assert issubclass(ReservedNameError, EngineError)

    def test_message_contains_name(self) -> None:
        err = ReservedNameError("color", "color = '#fff'")
        assert "color" in str(err)


class TestUnknownVariableError:
    def test_stores_fields(self) -> None:
        err = UnknownVariableError("lwidth", "{\\k50}hello")
        assert err.variable_name == "lwidth"
        assert err.template_text == "{\\k50}hello"

    def test_inherits_from_engine_error(self) -> None:
        assert issubclass(UnknownVariableError, EngineError)

    def test_message_contains_variable_name(self) -> None:
        err = UnknownVariableError("lwidth", "some text")
        assert "lwidth" in str(err)


class TestBoundMethodInExpressionError:
    def test_stores_fields(self) -> None:
        err = BoundMethodInExpressionError("retime", "method")
        assert err.expression == "retime"
        assert err.result_type == "method"

    def test_inherits_from_engine_error(self) -> None:
        assert issubclass(BoundMethodInExpressionError, EngineError)

    def test_message_contains_expression_and_type(self) -> None:
        err = BoundMethodInExpressionError("retime", "method")
        msg = str(err)
        assert "retime" in msg
        assert "method" in msg


class TestTemplateExecutionCancelledError:
    def test_inherits_from_engine_error(self) -> None:
        assert issubclass(TemplateExecutionCancelledError, EngineError)

    def test_inherits_from_pykara_error(self) -> None:
        assert issubclass(TemplateExecutionCancelledError, PykaraError)

    def test_can_be_raised_and_caught(self) -> None:
        with pytest.raises(TemplateExecutionCancelledError):
            raise TemplateExecutionCancelledError()

    def test_caught_as_engine_error(self) -> None:
        with pytest.raises(EngineError):
            raise TemplateExecutionCancelledError()
