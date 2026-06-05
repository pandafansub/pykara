"""Concrete validator for metadata models."""

from __future__ import annotations

from collections.abc import Sequence

from pykara.data import Metadata
from pykara.validation.rules._base import Rule
from pykara.validation.rules.metadata_rules import (
    PositiveResolutionRule,
    PositiveVideoCorrectFactorRule,
)
from pykara.validation.validators._base import RuleBasedValidator


class MetadataValidator(RuleBasedValidator[Metadata]):
    """Validate metadata using the phase 11 domain rules."""

    def __init__(self, rules: Sequence[Rule[Metadata]] | None = None) -> None:
        super().__init__(
            rules
            or (
                PositiveResolutionRule(),
                PositiveVideoCorrectFactorRule(),
            )
        )
