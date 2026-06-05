"""Shared declaration utilities."""

from __future__ import annotations

from typing import ClassVar, Protocol, TypeVar

from pykara.errors import ModifierParseError, UnknownModifierError

ModifierT = TypeVar("ModifierT")


class ModifierHandler(Protocol[ModifierT]):
    """Protocol implemented by one concrete class per modifier."""

    keyword: ClassVar[str]
    aliases: ClassVar[tuple[str, ...]] = ()

    def apply(
        self,
        remaining_tokens: list[str],
        current: ModifierT,
    ) -> tuple[ModifierT, list[str]]:
        """Consume tokens and return updated modifiers plus remaining tokens."""
        ...


class ModifierRegistry[ModifierT]:
    """Keep a runtime-extensible keyword-to-handler mapping."""

    def __init__(self, default: ModifierT) -> None:
        self._default = default
        self._handlers: dict[str, ModifierHandler[ModifierT]] = {}

    def register(self, handler: ModifierHandler[ModifierT]) -> None:
        """Register one handler under its keyword and aliases."""
        self._handlers[handler.keyword.lower()] = handler
        for alias in handler.aliases:
            self._handlers[alias.lower()] = handler

    def parse(self, tokens: list[str]) -> ModifierT:
        """Parse one modifier token stream into the target modifier object."""
        current = self._default
        remaining_tokens = list(tokens)
        while remaining_tokens:
            keyword, *remaining_tokens = remaining_tokens
            handler = self._handlers.get(keyword.lower())
            if handler is None:
                raise UnknownModifierError(modifier=keyword)
            current, remaining_tokens = handler.apply(
                remaining_tokens,
                current,
            )
        return current


def consume_condition_expression(
    modifier: str,
    remaining: list[str],
) -> tuple[str, list[str]]:
    """Consume a token or parenthesized expression after a modifier."""

    if not remaining:
        raise ModifierParseError(
            modifier,
            f"expected token or expression after {modifier!r}",
        )

    first_token = remaining[0]
    if not first_token.startswith("("):
        return first_token, remaining[1:]

    expression_tokens: list[str] = []
    depth = 0
    rest = list(remaining)
    while rest:
        token = rest.pop(0)
        expression_tokens.append(token)
        depth += token.count("(")
        depth -= token.count(")")
        if depth <= 0:
            return " ".join(expression_tokens), rest

    raise ModifierParseError(
        modifier,
        f"expected closing ')' in expression after {modifier!r}",
    )


def consume_required_argument(
    modifier: str,
    remaining: list[str],
) -> tuple[str, list[str]]:
    """Consume one required plain argument after a modifier."""

    if not remaining:
        raise ModifierParseError(
            modifier,
            f"expected name after {modifier!r}",
        )
    return remaining[0], remaining[1:]
