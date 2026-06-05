"""Code modifier models and parser handlers."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import ClassVar

from pykara.declaration._shared import consume_required_argument


@dataclass(frozen=True, slots=True)
class CodeModifiers:
    """Normalized code modifiers parsed from effect tokens."""

    styles: str | None = None


class CodeStylesModifier:
    """Parse the styles modifier."""

    keyword: ClassVar[str] = "styles"
    aliases: ClassVar[tuple[str, ...]] = ()

    def apply(
        self,
        remaining_tokens: list[str],
        current: CodeModifiers,
    ) -> tuple[CodeModifiers, list[str]]:
        styles_name, rest = consume_required_argument(
            "styles",
            remaining_tokens,
        )
        return replace(current, styles=styles_name), rest
