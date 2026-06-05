"""Immutable validation report data structures."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Severity(StrEnum):
    """Severity of one validation violation."""

    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class Violation:
    """One stable, structured validation issue."""

    severity: Severity
    code: str
    message: str
    context: str
    location: str | None = None


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """Immutable result of a validation run."""

    violations: tuple[Violation, ...] = ()

    @property
    def errors(self) -> tuple[Violation, ...]:
        """Return only ERROR-level violations."""
        return tuple(
            violation
            for violation in self.violations
            if violation.severity is Severity.ERROR
        )

    @property
    def warnings(self) -> tuple[Violation, ...]:
        """Return only WARNING-level violations."""
        return tuple(
            violation
            for violation in self.violations
            if violation.severity is Severity.WARNING
        )

    @property
    def has_errors(self) -> bool:
        """Return whether the report contains any ERROR-level violation."""
        return bool(self.errors)

    def merge(self, other: ValidationReport) -> ValidationReport:
        """Return a new report containing violations from both reports."""
        return ValidationReport(self.violations + other.violations)
