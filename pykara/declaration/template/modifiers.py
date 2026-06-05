"""Template modifier models and parser handlers."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import ClassVar

from pykara.declaration._shared import (
    consume_condition_expression,
    consume_required_argument,
)
from pykara.errors import ModifierParseError

_SNAKE_CASE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass(frozen=True, slots=True)
class LoopDescriptor:
    """One loop declared on a template."""

    name: str
    iterations: int | str
    explicit_name: str | None = None

    @property
    def is_implicit(self) -> bool:
        return self.explicit_name is None


@dataclass(frozen=True, slots=True)
class TemplateModifiers:
    """Normalized template modifiers parsed from effect tokens."""

    loops: tuple[LoopDescriptor, ...] = ()
    no_blank: bool = False
    no_merge: bool = False
    no_text: bool = False
    fx: str | None = None
    styles: str | None = None
    when: str | None = None
    unless: str | None = None


class LoopModifier:
    """Parse the loop modifier."""

    keyword: ClassVar[str] = "loop"
    aliases: ClassVar[tuple[str, ...]] = ()

    def apply(
        self,
        remaining_tokens: list[str],
        current: TemplateModifiers,
    ) -> tuple[TemplateModifiers, list[str]]:
        if not remaining_tokens:
            raise ModifierParseError(
                "loop",
                "expected positive integer after 'loop'",
            )

        if len(remaining_tokens) >= 2 and _SNAKE_CASE_PATTERN.match(
            remaining_tokens[0]
        ):
            loop_name = remaining_tokens[0]
            loop_count, rest = self._parse_iteration_count(remaining_tokens[1:])
            descriptor = LoopDescriptor(
                name=loop_name,
                iterations=loop_count,
                explicit_name=loop_name,
            )
            return self._append_loop(
                current,
                descriptor,
                rest,
            )

        loop_count, rest = self._parse_iteration_count(remaining_tokens)
        descriptor = LoopDescriptor(name="i", iterations=loop_count)
        return self._append_loop(current, descriptor, rest)

    def _append_loop(
        self,
        current: TemplateModifiers,
        descriptor: LoopDescriptor,
        remaining_tokens: list[str],
    ) -> tuple[TemplateModifiers, list[str]]:
        existing_loops = current.loops
        if descriptor.is_implicit:
            if any(loop.is_implicit for loop in existing_loops):
                raise ModifierParseError(
                    "loop",
                    "unnamed loop can only appear once per template",
                )
            if any(not loop.is_implicit for loop in existing_loops):
                raise ModifierParseError(
                    "loop",
                    "cannot mix unnamed and named loop declarations",
                )
        else:
            if any(loop.is_implicit for loop in existing_loops):
                raise ModifierParseError(
                    "loop",
                    "cannot mix named and unnamed loop declarations",
                )
            if any(loop.name == descriptor.name for loop in existing_loops):
                raise ModifierParseError(
                    "loop",
                    f"loop name {descriptor.name!r} cannot be declared twice",
                )

        updated = replace(current, loops=(*existing_loops, descriptor))
        return updated, remaining_tokens

    def _parse_iteration_count(
        self,
        remaining_tokens: list[str],
    ) -> tuple[int | str, list[str]]:
        first_token = remaining_tokens[0]
        if first_token.startswith("("):
            expression, rest = consume_condition_expression(
                "loop",
                remaining_tokens,
            )
            return expression[1:-1], rest

        return self._parse_positive_integer(first_token), remaining_tokens[1:]

    def _parse_positive_integer(self, token: str) -> int:
        try:
            value = int(token)
        except ValueError as error:
            raise ModifierParseError(
                "loop",
                "expected positive integer after 'loop'",
            ) from error

        if value <= 0:
            raise ModifierParseError(
                "loop",
                "loop iteration count must be a positive integer",
            )
        return value


class NoBlankModifier:
    """Parse the no_blank modifier."""

    keyword: ClassVar[str] = "no_blank"
    aliases: ClassVar[tuple[str, ...]] = ()

    def apply(
        self,
        remaining_tokens: list[str],
        current: TemplateModifiers,
    ) -> tuple[TemplateModifiers, list[str]]:
        return replace(current, no_blank=True), remaining_tokens


class NoTextModifier:
    """Parse the no_text modifier."""

    keyword: ClassVar[str] = "no_text"
    aliases: ClassVar[tuple[str, ...]] = ()

    def apply(
        self,
        remaining_tokens: list[str],
        current: TemplateModifiers,
    ) -> tuple[TemplateModifiers, list[str]]:
        return replace(current, no_text=True), remaining_tokens


class NoMergeModifier:
    """Parse the no_merge modifier."""

    keyword: ClassVar[str] = "no_merge"
    aliases: ClassVar[tuple[str, ...]] = ()

    def apply(
        self,
        remaining_tokens: list[str],
        current: TemplateModifiers,
    ) -> tuple[TemplateModifiers, list[str]]:
        return replace(current, no_merge=True), remaining_tokens


class FxModifier:
    """Parse the fx modifier."""

    keyword: ClassVar[str] = "fx"
    aliases: ClassVar[tuple[str, ...]] = ()

    def apply(
        self,
        remaining_tokens: list[str],
        current: TemplateModifiers,
    ) -> tuple[TemplateModifiers, list[str]]:
        if not remaining_tokens:
            raise ModifierParseError("fx", "expected name after 'fx'")
        return replace(current, fx=remaining_tokens[0]), remaining_tokens[1:]


class StylesModifier:
    """Parse the styles modifier."""

    keyword: ClassVar[str] = "styles"
    aliases: ClassVar[tuple[str, ...]] = ()

    def apply(
        self,
        remaining_tokens: list[str],
        current: TemplateModifiers,
    ) -> tuple[TemplateModifiers, list[str]]:
        styles_name, rest = consume_required_argument(
            "styles",
            remaining_tokens,
        )
        return replace(current, styles=styles_name), rest


class WhenModifier:
    """Parse the when modifier."""

    keyword: ClassVar[str] = "when"
    aliases: ClassVar[tuple[str, ...]] = ()

    def apply(
        self,
        remaining_tokens: list[str],
        current: TemplateModifiers,
    ) -> tuple[TemplateModifiers, list[str]]:
        expression, rest = consume_condition_expression(
            "when",
            remaining_tokens,
        )
        return replace(current, when=expression), rest


class UnlessModifier:
    """Parse the unless modifier."""

    keyword: ClassVar[str] = "unless"
    aliases: ClassVar[tuple[str, ...]] = ()

    def apply(
        self,
        remaining_tokens: list[str],
        current: TemplateModifiers,
    ) -> tuple[TemplateModifiers, list[str]]:
        expression, rest = consume_condition_expression(
            "unless",
            remaining_tokens,
        )
        return replace(current, unless=expression), rest
