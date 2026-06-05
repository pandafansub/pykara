"""Validation rules for document metadata."""

from __future__ import annotations

from dataclasses import dataclass

from pykara.data import Metadata
from pykara.validation.reports import Severity, Violation


@dataclass(frozen=True, slots=True)
class PositiveResolutionRule:
    """Ensure script resolution dimensions are strictly positive."""

    code: str = "metadata.resolution_positive"
    severity: Severity = Severity.ERROR

    def check(self, subject: Metadata) -> Violation | None:
        if subject.res_x > 0 and subject.res_y > 0:
            return None

        return Violation(
            severity=self.severity,
            code=self.code,
            message="Metadata resolution must use positive dimensions.",
            context=f"res_x={subject.res_x}, res_y={subject.res_y}",
            location="metadata",
        )


@dataclass(frozen=True, slots=True)
class PositiveVideoCorrectFactorRule:
    """Ensure the derived video correction factor is valid."""

    code: str = "metadata.video_x_correct_factor_positive"
    severity: Severity = Severity.ERROR

    def check(self, subject: Metadata) -> Violation | None:
        if subject.video_x_correct_factor > 0:
            return None

        return Violation(
            severity=self.severity,
            code=self.code,
            message="Metadata video_x_correct_factor must be positive.",
            context=f"video_x_correct_factor={subject.video_x_correct_factor}",
            location="metadata.video_x_correct_factor",
        )
