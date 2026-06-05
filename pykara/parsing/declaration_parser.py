"""Parser for template, mixin, and code declaration events."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from pykara.data import Event
from pykara.declaration import Scope
from pykara.declaration._shared import ModifierRegistry
from pykara.declaration.code import CodeBody, CodeModifiers
from pykara.declaration.mixin import MixinBody, MixinModifiers
from pykara.declaration.template import TemplateBody, TemplateModifiers
from pykara.errors import (
    DeclarativeParseError,
    InternalConsistencyError,
    UnknownModifierError,
)
from pykara.specification import DECLARATIONS, SCOPE_SPECIFICATIONS


def _empty_code_declarations() -> list[CodeDeclaration]:
    return []


def _empty_scoped_declarations() -> list[TemplateDeclaration | CodeDeclaration]:
    return []


def _empty_template_declarations() -> list[TemplateDeclaration]:
    return []


def _empty_mixin_declarations() -> list[MixinDeclaration]:
    return []


def _empty_active_styles() -> set[str]:
    return set()


@dataclass(frozen=True, slots=True)
class TemplateDeclaration:
    """One parsed template declaration."""

    body: TemplateBody
    scope: Scope
    modifiers: TemplateModifiers
    style: str = ""
    actor: str = ""
    layer: int = 0


@dataclass(frozen=True, slots=True)
class CodeDeclaration:
    """One parsed code declaration."""

    body: CodeBody
    scope: Scope
    modifiers: CodeModifiers = field(default_factory=CodeModifiers)
    style: str = ""


@dataclass(frozen=True, slots=True)
class MixinDeclaration:
    """One parsed mixin declaration."""

    body: MixinBody
    scope: Scope
    modifiers: MixinModifiers
    style: str = ""
    actor: str = ""


@dataclass(slots=True)
class ParsedDeclarations:
    """Parsed declarations grouped by execution scope."""

    setup: list[CodeDeclaration] = field(
        default_factory=_empty_code_declarations
    )
    line: list[TemplateDeclaration | CodeDeclaration] = field(
        default_factory=_empty_scoped_declarations
    )
    word: list[TemplateDeclaration | CodeDeclaration] = field(
        default_factory=_empty_scoped_declarations
    )
    syl: list[TemplateDeclaration | CodeDeclaration] = field(
        default_factory=_empty_scoped_declarations
    )
    char: list[TemplateDeclaration] = field(
        default_factory=_empty_template_declarations
    )
    mixin_line: list[MixinDeclaration] = field(
        default_factory=_empty_mixin_declarations
    )
    mixin_word: list[MixinDeclaration] = field(
        default_factory=_empty_mixin_declarations
    )
    mixin_syl: list[MixinDeclaration] = field(
        default_factory=_empty_mixin_declarations
    )
    mixin_char: list[MixinDeclaration] = field(
        default_factory=_empty_mixin_declarations
    )
    active_styles: set[str] = field(default_factory=_empty_active_styles)

    def iter_scoped_declarations(
        self,
    ) -> Iterable[TemplateDeclaration | CodeDeclaration]:
        """Yield template and code declarations in validation order."""

        yield from self.line
        yield from self.syl
        yield from self.word
        yield from self.char

    def iter_template_declarations(self) -> Iterable[TemplateDeclaration]:
        """Yield all template declarations in validation order."""

        for declaration in self.iter_scoped_declarations():
            if isinstance(declaration, TemplateDeclaration):
                yield declaration

    def iter_code_declarations(self) -> Iterable[CodeDeclaration]:
        """Yield all code declarations in validation order."""

        yield from self.setup
        for declaration in self.iter_scoped_declarations():
            if isinstance(declaration, CodeDeclaration):
                yield declaration

    def iter_mixin_declarations(self) -> Iterable[MixinDeclaration]:
        """Yield all mixin declarations in scope order."""

        yield from self.mixin_line
        yield from self.mixin_word
        yield from self.mixin_syl
        yield from self.mixin_char


class DeclarationParser:
    """Parse commented declaration events into normalized objects."""

    def __init__(
        self,
        template_mod_registry: ModifierRegistry[TemplateModifiers],
        mixin_mod_registry: ModifierRegistry[MixinModifiers],
        code_mod_registry: ModifierRegistry[CodeModifiers],
    ) -> None:
        self._template_mod_registry = template_mod_registry
        self._mixin_mod_registry = mixin_mod_registry
        self._code_mod_registry = code_mod_registry

    def parse(self, events: list[Event]) -> ParsedDeclarations:
        """Parse template and code declarations from commented events.

        Args:
            events: Domain events to inspect.

        Returns:
            Declarations grouped by execution scope.

        Raises:
            DeclarativeParseError: If a declaration lacks an explicit scope
                or contains unsupported tokens.
        """

        parsed = ParsedDeclarations()

        for event in events:
            declaration = self._parse_event(event)
            if declaration is None:
                continue

            parsed.active_styles.add(event.style)
            self._append_declaration(parsed, declaration)

        return parsed

    def _parse_event(
        self, event: Event
    ) -> TemplateDeclaration | CodeDeclaration | MixinDeclaration | None:
        """Parse one event when it contains a supported declaration."""

        if not event.comment:
            return None

        effect_tokens = event.effect.split()
        if not effect_tokens:
            return None

        declaration_name = effect_tokens[0].lower()
        declaration_spec = DECLARATIONS.get(declaration_name)
        if declaration_spec is None:
            return None

        scope, remaining_tokens = self._parse_scope(
            declaration_name=declaration_name,
            effect_field=event.effect,
            tokens=effect_tokens[1:],
        )
        if scope not in declaration_spec.allowed_scopes:
            raise DeclarativeParseError(
                effect_field=event.effect,
                message=(
                    f"Scope {scope.value!r} is not allowed for "
                    f"{declaration_name!r}"
                ),
            )

        if declaration_name == "mixin":
            declaration_style, remaining_tokens = self._parse_mixin_style(
                event=event,
                effect_field=event.effect,
                remaining_tokens=remaining_tokens,
            )
        else:
            declaration_style, remaining_tokens = self._parse_style_selector(
                event=event,
                remaining_tokens=remaining_tokens,
            )

        if declaration_name == "template":
            modifiers = self._parse_template_modifiers(
                effect_field=event.effect,
                tokens=remaining_tokens,
            )
            return TemplateDeclaration(
                body=TemplateBody(event.text),
                scope=scope,
                modifiers=modifiers,
                layer=event.layer,
                style=declaration_style,
                actor=event.actor,
            )

        if declaration_name == "mixin":
            modifiers = self._parse_mixin_modifiers(
                effect_field=event.effect,
                tokens=remaining_tokens,
            )
            return MixinDeclaration(
                body=MixinBody(event.text),
                scope=scope,
                modifiers=modifiers,
                style=declaration_style,
                actor=event.actor,
            )

        modifiers = self._parse_code_modifiers(
            effect_field=event.effect,
            tokens=remaining_tokens,
        )

        return CodeDeclaration(
            body=CodeBody(event.text),
            scope=scope,
            modifiers=modifiers,
            style=declaration_style,
        )

    def _parse_style_selector(
        self,
        *,
        event: Event,
        remaining_tokens: list[str],
    ) -> tuple[str, list[str]]:
        """Return the declaration style filter and unconsumed tokens."""

        if remaining_tokens and remaining_tokens[0].lower() == "all":
            return "", remaining_tokens[1:]

        return event.style, remaining_tokens

    def _parse_mixin_style(
        self,
        *,
        event: Event,
        effect_field: str,
        remaining_tokens: list[str],
    ) -> tuple[str, list[str]]:
        """Return the mixin style filter and reject unsupported all selector."""

        if remaining_tokens and remaining_tokens[0].lower() == "all":
            raise DeclarativeParseError(
                effect_field=effect_field,
                message="'all' is not allowed for mixin declarations",
            )
        return event.style, remaining_tokens

    def _parse_scope(
        self,
        *,
        declaration_name: str,
        effect_field: str,
        tokens: list[str],
    ) -> tuple[Scope, list[str]]:
        """Parse and validate the explicit declaration scope."""

        if not tokens:
            raise DeclarativeParseError(
                effect_field=effect_field,
                message=(
                    f"{declaration_name!r} declaration requires "
                    "an explicit scope"
                ),
            )

        scope_token = tokens[0].lower()
        scope = self._scope_from_token(scope_token)
        if scope is None:
            raise DeclarativeParseError(
                effect_field=effect_field,
                message=(
                    f"Invalid scope {scope_token!r} for {declaration_name!r}"
                ),
            )

        return scope, tokens[1:]

    def _parse_template_modifiers(
        self,
        *,
        effect_field: str,
        tokens: list[str],
    ) -> TemplateModifiers:
        """Parse template modifiers through the injected registry."""

        try:
            return self._template_mod_registry.parse(tokens)
        except UnknownModifierError as error:
            raise DeclarativeParseError(
                effect_field=effect_field,
                message=(
                    f"Unexpected token after template scope: {error.modifier!r}"
                ),
            ) from error

    def _parse_mixin_modifiers(
        self,
        *,
        effect_field: str,
        tokens: list[str],
    ) -> MixinModifiers:
        """Parse mixin modifiers through the injected registry."""

        try:
            return self._mixin_mod_registry.parse(tokens)
        except UnknownModifierError as error:
            raise DeclarativeParseError(
                effect_field=effect_field,
                message=(
                    f"Unexpected token after mixin scope: {error.modifier!r}"
                ),
            ) from error

    def _parse_code_modifiers(
        self,
        *,
        effect_field: str,
        tokens: list[str],
    ) -> CodeModifiers:
        """Parse code modifiers through the injected registry."""

        try:
            return self._code_mod_registry.parse(tokens)
        except UnknownModifierError as error:
            raise DeclarativeParseError(
                effect_field=effect_field,
                message=(
                    f"Unexpected token after code scope: {error.modifier!r}"
                ),
            ) from error

    def _scope_from_token(self, token: str) -> Scope | None:
        """Resolve one scope token using the shared specifications."""

        for scope in SCOPE_SPECIFICATIONS:
            if scope.value == token:
                return scope
        return None

    def _append_declaration(
        self,
        parsed: ParsedDeclarations,
        declaration: TemplateDeclaration | CodeDeclaration | MixinDeclaration,
    ) -> None:
        """Append one parsed declaration to the matching scope bucket."""

        if declaration.scope is Scope.SETUP:
            if not isinstance(declaration, CodeDeclaration):
                message = "SETUP scope is only valid for code declarations."
                raise InternalConsistencyError(message)
            parsed.setup.append(declaration)
            return

        if declaration.scope is Scope.LINE:
            if isinstance(declaration, MixinDeclaration):
                parsed.mixin_line.append(declaration)
            else:
                parsed.line.append(declaration)
            return

        if declaration.scope is Scope.WORD:
            if isinstance(declaration, MixinDeclaration):
                parsed.mixin_word.append(declaration)
            else:
                parsed.word.append(declaration)
            return

        if declaration.scope is Scope.SYL:
            if isinstance(declaration, MixinDeclaration):
                parsed.mixin_syl.append(declaration)
            else:
                parsed.syl.append(declaration)
            return

        if isinstance(declaration, MixinDeclaration):
            parsed.mixin_char.append(declaration)
            return
        if not isinstance(declaration, TemplateDeclaration):
            message = "CHAR scope is only valid for template declarations."
            raise InternalConsistencyError(message)
        parsed.char.append(declaration)
