"""Mixin modifier models and parser handlers."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import ClassVar

from pykara.declaration._shared import consume_condition_expression
from pykara.errors import ModifierParseError


@dataclass(frozen=True, slots=True)
class MixinModifiers:
    """Normalized mixin modifiers parsed from effect tokens."""

    prepend: bool = False
    layer: int | None = None
    for_actor: str | None = None
    fx: str | None = None
    when: str | None = None
    unless: str | None = None


class PrependModifier:
    """Parse the prepend modifier."""

    keyword: ClassVar[str] = "prepend"
    aliases: ClassVar[tuple[str, ...]] = ()

    def apply(
        self,
        remaining_tokens: list[str],
        current: MixinModifiers,
    ) -> tuple[MixinModifiers, list[str]]:
        return replace(current, prepend=True), remaining_tokens


class LayerModifier:
    """Parse the layer modifier."""

    keyword: ClassVar[str] = "layer"
    aliases: ClassVar[tuple[str, ...]] = ()

    def apply(
        self,
        remaining_tokens: list[str],
        current: MixinModifiers,
    ) -> tuple[MixinModifiers, list[str]]:
        if not remaining_tokens:
            raise ModifierParseError("layer", "expected integer after 'layer'")
        try:
            layer = int(remaining_tokens[0])
        except ValueError as error:
            raise ModifierParseError(
                "layer",
                "expected integer after 'layer'",
            ) from error
        return replace(current, layer=layer), remaining_tokens[1:]


class ForModifier:
    """Parse the for modifier."""

    keyword: ClassVar[str] = "for"
    aliases: ClassVar[tuple[str, ...]] = ()

    def apply(
        self,
        remaining_tokens: list[str],
        current: MixinModifiers,
    ) -> tuple[MixinModifiers, list[str]]:
        if not remaining_tokens:
            raise ModifierParseError("for", "expected actor name after 'for'")
        return (
            replace(current, for_actor=remaining_tokens[0]),
            remaining_tokens[1:],
        )


class MixinFxModifier:
    """Parse the fx modifier."""

    keyword: ClassVar[str] = "fx"
    aliases: ClassVar[tuple[str, ...]] = ()

    def apply(
        self,
        remaining_tokens: list[str],
        current: MixinModifiers,
    ) -> tuple[MixinModifiers, list[str]]:
        if not remaining_tokens:
            raise ModifierParseError("fx", "expected name after 'fx'")
        return replace(current, fx=remaining_tokens[0]), remaining_tokens[1:]


class MixinWhenModifier:
    """Parse the when modifier."""

    keyword: ClassVar[str] = "when"
    aliases: ClassVar[tuple[str, ...]] = ()

    def apply(
        self,
        remaining_tokens: list[str],
        current: MixinModifiers,
    ) -> tuple[MixinModifiers, list[str]]:
        expression, rest = consume_condition_expression(
            "when",
            remaining_tokens,
        )
        return replace(current, when=expression), rest


class MixinUnlessModifier:
    """Parse the unless modifier."""

    keyword: ClassVar[str] = "unless"
    aliases: ClassVar[tuple[str, ...]] = ()

    def apply(
        self,
        remaining_tokens: list[str],
        current: MixinModifiers,
    ) -> tuple[MixinModifiers, list[str]]:
        expression, rest = consume_condition_expression(
            "unless",
            remaining_tokens,
        )
        return replace(current, unless=expression), rest
