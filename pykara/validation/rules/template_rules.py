"""Validation rules for parsed template declarations."""

from __future__ import annotations

import re
from dataclasses import dataclass

from pykara.parsing import TemplateDeclaration
from pykara.specification import DECLARATIONS, MODIFIER_SPECIFICATIONS
from pykara.validation.reports import Severity, Violation

_INLINE_EXPRESSION_PATTERN = re.compile(r"!(.+?)!", re.DOTALL)
_UNSUPPORTED_INLINE_MARKERS = (
    re.compile(r"\bfunction\b"),
    re.compile(r"\.\."),
    re.compile(r"\blocal\b"),
    re.compile(r"#\w+"),
)


def _contains_unsupported_inline_marker(source: str) -> bool:
    return any(
        pattern.search(source) is not None
        for pattern in _UNSUPPORTED_INLINE_MARKERS
    )


def _iter_active_modifiers(
    declaration: TemplateDeclaration,
) -> tuple[str, ...]:
    modifiers = declaration.modifiers
    active_modifiers: list[str] = []

    if modifiers.loops:
        active_modifiers.append("loop")
    if modifiers.no_blank:
        active_modifiers.append("no_blank")
    if modifiers.no_merge:
        active_modifiers.append("no_merge")
    if modifiers.no_text:
        active_modifiers.append("no_text")
    if modifiers.fx is not None:
        active_modifiers.append("fx")
    if modifiers.styles is not None:
        active_modifiers.append("styles")
    if modifiers.when is not None:
        active_modifiers.append("when")
    if modifiers.unless is not None:
        active_modifiers.append("unless")

    return tuple(active_modifiers)


@dataclass(frozen=True, slots=True)
class TemplateAllowedScopeRule:
    """Ensure template declarations use one of the documented scopes."""

    code: str = "template.scope_allowed"
    severity: Severity = Severity.ERROR

    def check(self, subject: TemplateDeclaration) -> Violation | None:
        allowed_scopes = DECLARATIONS["template"].allowed_scopes
        if subject.scope in allowed_scopes:
            return None

        return Violation(
            severity=self.severity,
            code=self.code,
            message="Template declaration uses an unsupported scope.",
            context=f"scope={subject.scope.value!r}",
            location="template.scope",
        )


@dataclass(frozen=True, slots=True)
class PythonExpressionSyntaxRule:
    """Reject unsupported syntax inside inline template expressions."""

    code: str = "template.expression_python_only"
    severity: Severity = Severity.ERROR

    def check(self, subject: TemplateDeclaration) -> Violation | None:
        for match in _INLINE_EXPRESSION_PATTERN.finditer(subject.body.text):
            expression = match.group(1)
            if not _contains_unsupported_inline_marker(expression):
                continue

            return Violation(
                severity=self.severity,
                code=self.code,
                message=(
                    "Template inline expressions must use Python syntax, "
                    "not unsupported expression syntax."
                ),
                context=f"expression={expression!r}",
                location="template.body",
            )
        return None


@dataclass(frozen=True, slots=True)
class CompatibleTemplateModifierScopeRule:
    """Ensure active template modifiers are valid for the current scope."""

    code: str = "template.modifier_scope_compatible"
    severity: Severity = Severity.ERROR

    def check(self, subject: TemplateDeclaration) -> Violation | None:
        for modifier_name in _iter_active_modifiers(subject):
            specification = MODIFIER_SPECIFICATIONS[modifier_name]
            if subject.scope in specification.allowed_scopes:
                continue

            return Violation(
                severity=self.severity,
                code=self.code,
                message=("Template modifier is not allowed for this scope."),
                context=(
                    f"modifier={modifier_name!r}, scope={subject.scope.value!r}"
                ),
                location="template.modifiers",
            )
        return None
