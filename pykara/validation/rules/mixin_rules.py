"""Validation rules for parsed mixin declarations."""

from __future__ import annotations

import re
from dataclasses import dataclass

from pykara.parsing import MixinDeclaration
from pykara.specification import DECLARATIONS, MODIFIER_SPECIFICATIONS
from pykara.validation.reports import Severity, Violation

INLINE_EXPRESSION_PATTERN = re.compile(r"!(.+?)!", re.DOTALL)
UNSUPPORTED_INLINE_MARKERS = (
    re.compile(r"\bfunction\b"),
    re.compile(r"\.\."),
    re.compile(r"\blocal\b"),
    re.compile(r"#\w+"),
)


def contains_unsupported_inline_marker(source: str) -> bool:
    """Return whether an inline expression contains unsupported syntax."""

    return any(
        pattern.search(source) is not None
        for pattern in UNSUPPORTED_INLINE_MARKERS
    )


def _iter_active_modifiers(
    declaration: MixinDeclaration,
) -> tuple[str, ...]:
    modifiers = declaration.modifiers
    active_modifiers: list[str] = []

    if modifiers.prepend:
        active_modifiers.append("prepend")
    if modifiers.layer is not None:
        active_modifiers.append("layer")
    if modifiers.for_actor is not None:
        active_modifiers.append("for")
    if modifiers.fx is not None:
        active_modifiers.append("fx")
    if modifiers.when is not None:
        active_modifiers.append("when")
    if modifiers.unless is not None:
        active_modifiers.append("unless")

    return tuple(active_modifiers)


@dataclass(frozen=True, slots=True)
class MixinAllowedScopeRule:
    """Ensure mixin declarations use one of the documented scopes."""

    code: str = "mixin.scope_allowed"
    severity: Severity = Severity.ERROR

    def check(self, subject: MixinDeclaration) -> Violation | None:
        allowed_scopes = DECLARATIONS["mixin"].allowed_scopes
        if subject.scope in allowed_scopes:
            return None

        return Violation(
            severity=self.severity,
            code=self.code,
            message="Mixin declaration uses an unsupported scope.",
            context=f"scope={subject.scope.value!r}",
            location="mixin.scope",
        )


@dataclass(frozen=True, slots=True)
class MixinPythonExpressionSyntaxRule:
    """Reject unsupported syntax inside inline mixin expressions."""

    code: str = "mixin.expression_python_only"
    severity: Severity = Severity.ERROR

    def check(self, subject: MixinDeclaration) -> Violation | None:
        for match in INLINE_EXPRESSION_PATTERN.finditer(subject.body.text):
            expression = match.group(1)
            if not contains_unsupported_inline_marker(expression):
                continue

            return Violation(
                severity=self.severity,
                code=self.code,
                message=(
                    "Mixin inline expressions must use Python syntax, "
                    "not unsupported expression syntax."
                ),
                context=f"expression={expression!r}",
                location="mixin.body",
            )
        return None


@dataclass(frozen=True, slots=True)
class CompatibleMixinModifierScopeRule:
    """Ensure active mixin modifiers are valid for the current scope."""

    code: str = "mixin.modifier_scope_compatible"
    severity: Severity = Severity.ERROR

    def check(self, subject: MixinDeclaration) -> Violation | None:
        for modifier_name in _iter_active_modifiers(subject):
            specification = MODIFIER_SPECIFICATIONS[modifier_name]
            if "mixin" not in specification.applicable_to:
                return Violation(
                    severity=self.severity,
                    code=self.code,
                    message="Mixin modifier is not available for mixins.",
                    context=f"modifier={modifier_name!r}",
                    location="mixin.modifiers",
                )
            if subject.scope in specification.allowed_scopes:
                continue

            return Violation(
                severity=self.severity,
                code=self.code,
                message="Mixin modifier is not allowed for this scope.",
                context=(
                    f"modifier={modifier_name!r}, scope={subject.scope.value!r}"
                ),
                location="mixin.modifiers",
            )
        return None
