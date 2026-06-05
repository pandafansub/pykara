"""Concrete validator for code declarations."""

from __future__ import annotations

from collections.abc import Sequence

from pykara.parsing import CodeDeclaration
from pykara.validation.rules._base import Rule
from pykara.validation.rules.code_rules import (
    CodeAllowedScopeRule,
    ValidPythonSyntaxRule,
)
from pykara.validation.validators._base import RuleBasedValidator


class CodeValidator(RuleBasedValidator[CodeDeclaration]):
    """Validate code declarations using the phase 11 domain rules."""

    def __init__(
        self,
        rules: Sequence[Rule[CodeDeclaration]] | None = None,
    ) -> None:
        super().__init__(
            rules or (CodeAllowedScopeRule(), ValidPythonSyntaxRule())
        )
