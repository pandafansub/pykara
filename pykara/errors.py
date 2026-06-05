"""Pykara exception hierarchy.

Every error raised by the package derives from :class:`PykaraError`.
No internal module raises ``ValueError``, ``RuntimeError``, or similar directly.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pykara.validation.reports import ValidationReport


class PykaraError(Exception):
    """Root of the Pykara exception hierarchy."""


class AdapterError(PykaraError):
    """Base for errors originating in input/output adapters."""


class DocumentReadError(AdapterError):
    """Raised when a subtitle document cannot be read from disk."""

    def __init__(self, path: Path, message: str = "") -> None:
        self.path = path
        super().__init__(message or f"Could not read document: {path}")


class DocumentWriteError(AdapterError):
    """Raised when a subtitle document cannot be written to disk."""

    def __init__(self, path: Path, message: str = "") -> None:
        self.path = path
        super().__init__(message or f"Could not write document: {path}")


class ParsingError(PykaraError):
    """Base for parsing errors."""


class KaraokeParseError(ParsingError):
    """Raised when karaoke tags in an event cannot be parsed."""

    def __init__(self, event_text: str, message: str = "") -> None:
        self.event_text = event_text
        super().__init__(
            message or f"Failed to parse karaoke tags in: {event_text!r}"
        )


class DeclarativeParseError(ParsingError):
    """Raised when a template or code declaration cannot be parsed.

    ``effect_field`` is the raw content of the effect field that caused the
    error. May be empty when the error is detected before the parser has full
    context.
    """

    def __init__(self, effect_field: str = "", message: str = "") -> None:
        self.effect_field = effect_field
        super().__init__(
            message or f"Invalid declaration in effect field: {effect_field!r}"
        )


class UnknownModifierError(DeclarativeParseError):
    """Raised when an unregistered modifier keyword is encountered."""

    def __init__(
        self,
        modifier: str,
        effect_field: str = "",
        message: str = "",
    ) -> None:
        self.modifier = modifier
        super().__init__(
            effect_field=effect_field,
            message=message or f"Unknown modifier: {modifier!r}",
        )


class ModifierParseError(DeclarativeParseError):
    """Raised when a modifier is present but its arguments are invalid."""

    def __init__(
        self,
        modifier: str,
        reason: str,
        effect_field: str = "",
    ) -> None:
        self.modifier = modifier
        self.reason = reason
        super().__init__(
            effect_field=effect_field,
            message=f"Modifier {modifier!r}: {reason}",
        )


class ValidationError(PykaraError):
    """Raised when the ValidationReport contains ERROR-level violations."""

    def __init__(self, report: ValidationReport) -> None:
        self.report = report
        count = len(report.errors)
        super().__init__(
            f"{count} validation error(s) — inspect report for details"
        )


class ProcessingError(PykaraError):
    """Base for pre-processing errors."""


class InternalConsistencyError(PykaraError):
    """Raised when an internal invariant is violated."""


class DependencyUnavailableError(PykaraError):
    """Raised when an optional runtime dependency is unexpectedly missing."""


class LinePreprocessingError(ProcessingError):
    """Raised when line layout pre-processing fails."""

    def __init__(self, event_text: str, message: str = "") -> None:
        self.event_text = event_text
        super().__init__(
            message or f"Failed to preprocess line: {event_text!r}"
        )


class EngineError(PykaraError):
    """Base for engine execution errors."""


class ExecutionAttributeUnavailableError(EngineError):
    """Raised when an execution attribute is unavailable in the current
    context.
    """

    def __init__(self, attribute_name: str) -> None:
        self.attribute_name = attribute_name
        super().__init__(
            "Execution attribute "
            f"{attribute_name!r} is unavailable in the current context"
        )


class TemplateCodeError(EngineError):
    """Raised on Python syntax errors inside a CodeBody."""

    def __init__(self, source: str, cause: SyntaxError) -> None:
        self.source = source
        self.cause = cause
        super().__init__(f"Syntax error in code block: {cause}")


class TemplateRuntimeError(EngineError):
    """Raised when a CodeBody or inline expression fails at runtime."""

    def __init__(self, source: str, cause: Exception) -> None:
        self.source = source
        self.cause = cause
        super().__init__(f"Runtime error in template: {cause}")


class UnknownStyleReferenceError(EngineError):
    """Raised when a styles modifier references a style that does not exist."""

    def __init__(self, style_name: str, source: str) -> None:
        self.style_name = style_name
        self.source = source
        super().__init__(
            "Styles modifier "
            f"{source!r} references unknown style {style_name!r}"
        )


class ReservedNameError(EngineError):
    """Raised when code tries to bind a name reserved by Pykara."""

    def __init__(self, name: str, source: str) -> None:
        self.name = name
        self.source = source
        super().__init__(f"Cannot assign to reserved name {name!r}")


class UnknownVariableError(EngineError):
    """Raised when a $variable reference in TemplateBody does not exist."""

    def __init__(self, variable_name: str, template_text: str) -> None:
        self.variable_name = variable_name
        self.template_text = template_text
        super().__init__(
            f"Unknown variable ${variable_name!r} "
            f"in template: {template_text!r}"
        )


class BoundMethodInExpressionError(EngineError):
    """Raised when an inline expression !…! evaluates to a callable.

    Likely cause: a method reference without a call —
    ``!retime.syl!`` instead of ``!retime.syl()!``.
    """

    def __init__(self, expression: str, result_type: str) -> None:
        self.expression = expression
        self.result_type = result_type
        super().__init__(
            f"Expression !{expression}! returned a callable ({result_type}); "
            "did you forget to call the function?"
        )


class LockedStoreKeyError(EngineError):
    """Raised when a store key locked by lock() is overwritten by put()."""

    def __init__(self, key: str) -> None:
        self.key = key
        super().__init__(f"Cannot put {key!r}: key is locked")


class TemplateExecutionCancelledError(EngineError):
    """Raised to explicitly cancel template execution."""
