"""Validation rules for normalized subtitle styles."""

from __future__ import annotations

from dataclasses import dataclass

from pykara.data import Style
from pykara.validation.reports import Severity, Violation


@dataclass(frozen=True, slots=True)
class PositiveFontSizeRule:
    """Ensure style font size is strictly positive."""

    code: str = "style.fontsize_positive"
    severity: Severity = Severity.ERROR

    def check(self, subject: Style) -> Violation | None:
        if subject.fontsize > 0:
            return None

        return Violation(
            severity=self.severity,
            code=self.code,
            message="Style fontsize must be positive.",
            context=f"style={subject.name!r}, fontsize={subject.fontsize}",
            location="style.fontsize",
        )


@dataclass(frozen=True, slots=True)
class NonNegativeMarginsRule:
    """Ensure ASS margins never become negative."""

    code: str = "style.margins_non_negative"
    severity: Severity = Severity.ERROR

    def check(self, subject: Style) -> Violation | None:
        margins = {
            "margin_l": subject.margin_l,
            "margin_r": subject.margin_r,
            "margin_t": subject.margin_t,
            "margin_b": subject.margin_b,
        }
        invalid_margin = next(
            ((name, value) for name, value in margins.items() if value < 0),
            None,
        )
        if invalid_margin is None:
            return None

        margin_name, margin_value = invalid_margin
        return Violation(
            severity=self.severity,
            code=self.code,
            message="Style margins must be zero or greater.",
            context=(f"style={subject.name!r}, {margin_name}={margin_value}"),
            location=f"style.{margin_name}",
        )
