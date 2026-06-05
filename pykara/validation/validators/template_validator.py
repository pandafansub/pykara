"""Concrete validator for template declarations."""

from __future__ import annotations

from collections.abc import Sequence

from pykara.parsing import TemplateDeclaration
from pykara.validation.rules._base import Rule
from pykara.validation.rules.template_rules import (
    CompatibleTemplateModifierScopeRule,
    PythonExpressionSyntaxRule,
    TemplateAllowedScopeRule,
)
from pykara.validation.validators._base import RuleBasedValidator


class TemplateValidator(RuleBasedValidator[TemplateDeclaration]):
    """Validate template declarations using the phase 11 domain rules."""

    def __init__(
        self,
        rules: Sequence[Rule[TemplateDeclaration]] | None = None,
    ) -> None:
        super().__init__(
            rules
            or (
                TemplateAllowedScopeRule(),
                PythonExpressionSyntaxRule(),
                CompatibleTemplateModifierScopeRule(),
            )
        )
