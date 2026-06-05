"""Concrete validator for style models."""

from __future__ import annotations

from collections.abc import Sequence

from pykara.data import Style
from pykara.validation.rules._base import Rule
from pykara.validation.rules.style_rules import (
    NonNegativeMarginsRule,
    PositiveFontSizeRule,
)
from pykara.validation.validators._base import RuleBasedValidator


class StyleValidator(RuleBasedValidator[Style]):
    """Validate styles using the phase 11 domain rules."""

    def __init__(self, rules: Sequence[Rule[Style]] | None = None) -> None:
        super().__init__(
            rules or (PositiveFontSizeRule(), NonNegativeMarginsRule())
        )
