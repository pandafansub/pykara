"""Validation rules for parsed karaoke syllables."""

from __future__ import annotations

from dataclasses import dataclass

from pykara.data import Syllable
from pykara.validation.reports import Severity, Violation


@dataclass(frozen=True, slots=True)
class PositiveSyllableDurationRule:
    """Ensure syllable timing is non-negative."""

    code: str = "karaoke.duration_positive"
    severity: Severity = Severity.ERROR

    def check(self, subject: Syllable) -> Violation | None:
        if subject.duration >= 0:
            return None

        return Violation(
            severity=self.severity,
            code=self.code,
            message="Syllable duration must be non-negative.",
            context=f"index={subject.index}, duration={subject.duration}",
            location="syllable.duration",
        )
