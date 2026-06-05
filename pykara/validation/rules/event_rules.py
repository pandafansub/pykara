"""Validation rules for subtitle events."""

from __future__ import annotations

import re
from dataclasses import dataclass

from pykara.data import Event
from pykara.validation.reports import Severity, Violation

_KARAOKE_TAG_PATTERN = re.compile(r"\\(?:k|K|kf|ko)\d+")


@dataclass(frozen=True, slots=True)
class IncreasingEventTimeRule:
    """Ensure karaoke source events have a positive duration."""

    code: str = "event.time_order"
    severity: Severity = Severity.ERROR

    def check(self, subject: Event) -> Violation | None:
        if not self._requires_timing_validation(subject):
            return None

        if subject.start_time < subject.end_time:
            return None

        return Violation(
            severity=self.severity,
            code=self.code,
            message="Event start_time must be smaller than end_time.",
            context=(
                f"start_time={subject.start_time}, end_time={subject.end_time}"
            ),
            location="event.timing",
        )

    def _requires_timing_validation(self, event: Event) -> bool:
        return (
            "karaoke" in event.effect.lower()
            and _KARAOKE_TAG_PATTERN.search(event.text) is not None
        )


@dataclass(frozen=True, slots=True)
class RequiredEventStyleRule:
    """Ensure every event references a non-empty style name."""

    code: str = "event.style_required"
    severity: Severity = Severity.ERROR

    def check(self, subject: Event) -> Violation | None:
        if subject.style.strip():
            return None

        return Violation(
            severity=self.severity,
            code=self.code,
            message="Event style must not be empty.",
            context=f"text={subject.text!r}, effect={subject.effect!r}",
            location="event.style",
        )
