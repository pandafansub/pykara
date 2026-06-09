"""Validation rules for parsed code declarations."""

from __future__ import annotations

from dataclasses import dataclass

from pykara.declaration import Scope
from pykara.errors import IncludeParseError
from pykara.parsing import CodeDeclaration
from pykara.specification import DECLARATIONS
from pykara.support.include_parser import (
    is_include_source,
    parse_include_paths,
)
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
        if is_include_source(subject.body.source):
            return self._check_include_syntax(subject)

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

    def _check_include_syntax(
        self,
        subject: CodeDeclaration,
    ) -> Violation | None:
        source = subject.body.source
        if subject.scope is not Scope.SETUP:
            return Violation(
                severity=self.severity,
                code=self.code,
                message="Include declarations are only allowed in setup scope.",
                context=f"scope={subject.scope.value}",
                location="code.scope",
            )

        try:
            parse_include_paths(source)
        except IncludeParseError as error:
            return Violation(
                severity=self.severity,
                code=self.code,
                message="Include declaration must contain valid path syntax.",
                context=f"message={error}",
                location="code.body",
            )

        return None
