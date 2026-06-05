"""Concrete validator for karaoke syllables."""

from __future__ import annotations

from collections.abc import Sequence

from pykara.data import Syllable
from pykara.validation.rules._base import Rule
from pykara.validation.rules.karaoke_rules import PositiveSyllableDurationRule
from pykara.validation.validators._base import RuleBasedValidator


class KaraokeValidator(RuleBasedValidator[Syllable]):
    """Validate karaoke syllables using the phase 11 domain rules."""

    def __init__(self, rules: Sequence[Rule[Syllable]] | None = None) -> None:
        super().__init__(rules or (PositiveSyllableDurationRule(),))
