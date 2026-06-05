"""Concrete validator for mixin declarations."""

from __future__ import annotations

from collections.abc import Sequence

from pykara.parsing import MixinDeclaration
from pykara.validation.rules._base import Rule
from pykara.validation.rules.mixin_rules import (
    CompatibleMixinModifierScopeRule,
    MixinAllowedScopeRule,
    MixinPythonExpressionSyntaxRule,
)
from pykara.validation.validators._base import RuleBasedValidator


class MixinValidator(RuleBasedValidator[MixinDeclaration]):
    """Validate mixin declarations using mixin-specific domain rules."""

    def __init__(
        self,
        rules: Sequence[Rule[MixinDeclaration]] | None = None,
    ) -> None:
        super().__init__(
            rules
            or (
                MixinAllowedScopeRule(),
                MixinPythonExpressionSyntaxRule(),
                CompatibleMixinModifierScopeRule(),
            )
        )
