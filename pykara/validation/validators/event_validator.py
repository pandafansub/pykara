"""Concrete validator for subtitle events."""

from __future__ import annotations

from collections.abc import Sequence

from pykara.data import Event
from pykara.validation.rules._base import Rule
from pykara.validation.rules.event_rules import (
    IncreasingEventTimeRule,
    RequiredEventStyleRule,
)
from pykara.validation.validators._base import RuleBasedValidator


class EventValidator(RuleBasedValidator[Event]):
    """Validate events using the phase 11 domain rules."""

    def __init__(self, rules: Sequence[Rule[Event]] | None = None) -> None:
        super().__init__(
            rules or (IncreasingEventTimeRule(), RequiredEventStyleRule())
        )
