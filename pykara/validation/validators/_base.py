"""Base validator protocols and rule-driven implementation."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, TypeVar

from pykara.validation.reports import ValidationReport
from pykara.validation.rules._base import Rule

SubjectT = TypeVar("SubjectT", contravariant=True)


class Validator(Protocol[SubjectT]):
    """Protocol for objects that validate one subject type."""

    def validate(self, subject: SubjectT) -> ValidationReport:
        """Validate one subject and return an immutable report."""
        ...


class RuleBasedValidator[SubjectT]:
    """Validator implementation that aggregates atomic rules."""

    def __init__(self, rules: Sequence[Rule[SubjectT]]) -> None:
        self._rules = tuple(rules)

    def validate(self, subject: SubjectT) -> ValidationReport:
        violations = tuple(
            violation
            for rule in self._rules
            if (violation := rule.check(subject)) is not None
        )
        return ValidationReport(violations)

    def with_rule(self, rule: Rule[SubjectT]) -> RuleBasedValidator[SubjectT]:
        """Return a new validator with one additional rule."""
        return RuleBasedValidator((*self._rules, rule))
