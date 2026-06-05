"""Unit tests for validation infrastructure introduced in phase 7."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, dataclass

import pytest

from pykara.validation.reports import Severity, ValidationReport, Violation
from pykara.validation.validators import RuleBasedValidator


def make_violation(
    *,
    severity: Severity,
    code: str,
) -> Violation:
    return Violation(
        severity=severity,
        code=code,
        message=f"message for {code}",
        context="sample",
        location="subject",
    )


@dataclass(frozen=True, slots=True)
class StartsWithRule:
    code: str
    severity: Severity
    prefix: str

    def check(self, subject: str) -> Violation | None:
        if subject.startswith(self.prefix):
            return None
        return Violation(
            severity=self.severity,
            code=self.code,
            message=f"subject must start with {self.prefix!r}",
            context=subject,
            location="string subject",
        )


class TestValidationReport:
    def test_splits_errors_and_warnings(self) -> None:
        error = make_violation(severity=Severity.ERROR, code="E001")
        warning = make_violation(severity=Severity.WARNING, code="W001")
        report = ValidationReport((error, warning))

        assert report.errors == (error,)
        assert report.warnings == (warning,)
        assert report.has_errors is True

    def test_merge_returns_new_report(self) -> None:
        left = ValidationReport(
            (make_violation(severity=Severity.ERROR, code="E001"),)
        )
        right = ValidationReport(
            (make_violation(severity=Severity.WARNING, code="W001"),)
        )

        merged = left.merge(right)

        assert merged.violations == left.violations + right.violations
        assert left.violations != merged.violations

    def test_is_immutable(self) -> None:
        report = ValidationReport()
        attribute_name = "violations"

        with pytest.raises(FrozenInstanceError):
            setattr(report, attribute_name, ())


class TestRuleBasedValidator:
    def test_aggregates_rule_violations(self) -> None:
        validator: RuleBasedValidator[str] = RuleBasedValidator(
            [
                StartsWithRule("E001", Severity.ERROR, "py"),
                StartsWithRule("W001", Severity.WARNING, "pykara"),
            ]
        )

        report = validator.validate("python")

        assert tuple(violation.code for violation in report.violations) == (
            "W001",
        )
        assert report.has_errors is False

    def test_with_rule_is_immutable(self) -> None:
        base: RuleBasedValidator[str] = RuleBasedValidator(
            [StartsWithRule("E001", Severity.ERROR, "py")]
        )
        extended = base.with_rule(
            StartsWithRule("W001", Severity.WARNING, "pykara")
        )

        base_report = base.validate("pydantic")
        extended_report = extended.validate("pydantic")

        assert (
            tuple(violation.code for violation in base_report.violations) == ()
        )
        assert tuple(
            violation.code for violation in extended_report.violations
        ) == ("W001",)

    def test_returns_error_report_when_error_rule_fails(self) -> None:
        validator: RuleBasedValidator[str] = RuleBasedValidator(
            [StartsWithRule("E001", Severity.ERROR, "pykara")]
        )

        report = validator.validate("python")

        assert report.has_errors is True
        assert tuple(violation.code for violation in report.errors) == ("E001",)
