"""Base protocol for atomic validation rules."""

from __future__ import annotations

from typing import Protocol, TypeVar

from pykara.validation.reports import Severity, Violation

SubjectT = TypeVar("SubjectT", contravariant=True)


class Rule(Protocol[SubjectT]):
    """One atomic validation rule for one subject type."""

    @property
    def code(self) -> str:
        """Stable rule identifier."""
        ...

    @property
    def severity(self) -> Severity:
        """Severity emitted by this rule."""
        ...

    def check(self, subject: SubjectT) -> Violation | None:
        """Return one violation or ``None`` when the subject is valid."""
        ...
