"""Validation rules for parsed code declarations."""

from __future__ import annotations

from dataclasses import dataclass

from pykara.parsing import CodeDeclaration
from pykara.specification import DECLARATIONS
from pykara.validation.reports import Severity, Violation


@dataclass(frozen=True, slots=True)
class CodeAllowedScopeRule:
    """Ensure code declarations use one of the documented scopes."""

    code: str = "code.scope_allowed"
    severity: Severity = Severity.ERROR

    def check(self, subject: CodeDeclaration) -> Violation | None:
        allowed_scopes = DECLARATIONS["code"].allowed_scopes
        if subject.scope in allowed_scopes:
            return None

        return Violation(
            severity=self.severity,
            code=self.code,
            message="Code declaration uses an unsupported scope.",
            context=f"scope={subject.scope.value!r}",
            location="code.scope",
        )


@dataclass(frozen=True, slots=True)
class ValidPythonSyntaxRule:
    """Ensure code blocks compile as valid Python source."""

    code: str = "code.python_syntax"
    severity: Severity = Severity.ERROR

    def check(self, subject: CodeDeclaration) -> Violation | None:
        try:
            compile(subject.body.source, "<pykara-code>", "exec")
        except SyntaxError as error:
            return Violation(
                severity=self.severity,
                code=self.code,
                message="Code declaration must contain valid Python syntax.",
                context=f"line={error.lineno}, message={error.msg}",
                location="code.body",
            )

        return None
