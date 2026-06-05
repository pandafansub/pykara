"""Declarative metadata for supported template modifiers."""

from __future__ import annotations

from dataclasses import dataclass

from pykara.declaration import Scope


@dataclass(frozen=True, slots=True)
class ModifierSpecification:
    """Describe one modifier keyword independent from its implementation."""

    keyword: str
    aliases: tuple[str, ...]
    takes_argument: bool
    applicable_to: frozenset[str]
    allowed_scopes: frozenset[Scope]
    description: str


TEMPLATE_SCOPES = frozenset({Scope.LINE, Scope.WORD, Scope.SYL, Scope.CHAR})
STYLE_SCOPES = frozenset(
    {Scope.SETUP, Scope.LINE, Scope.WORD, Scope.SYL, Scope.CHAR}
)


MODIFIER_SPECIFICATIONS: dict[str, ModifierSpecification] = {
    "loop": ModifierSpecification(
        keyword="loop",
        aliases=(),
        takes_argument=True,
        applicable_to=frozenset({"template"}),
        allowed_scopes=TEMPLATE_SCOPES,
        description="Declare one named or unnamed loop for template iteration.",
    ),
    "no_blank": ModifierSpecification(
        keyword="no_blank",
        aliases=(),
        takes_argument=False,
        applicable_to=frozenset({"template"}),
        allowed_scopes=frozenset(
            {Scope.LINE, Scope.WORD, Scope.SYL, Scope.CHAR}
        ),
        description="Skip blank lines, words, syllables, or characters.",
    ),
    "no_text": ModifierSpecification(
        keyword="no_text",
        aliases=(),
        takes_argument=False,
        applicable_to=frozenset({"template"}),
        allowed_scopes=frozenset(
            {Scope.LINE, Scope.WORD, Scope.SYL, Scope.CHAR}
        ),
        description="Do not append the source scope text to the output.",
    ),
    "no_merge": ModifierSpecification(
        keyword="no_merge",
        aliases=(),
        takes_argument=False,
        applicable_to=frozenset({"template"}),
        allowed_scopes=frozenset(
            {Scope.LINE, Scope.WORD, Scope.SYL, Scope.CHAR}
        ),
        description="Keep adjacent ASS override blocks separate.",
    ),
    "fx": ModifierSpecification(
        keyword="fx",
        aliases=(),
        takes_argument=True,
        applicable_to=frozenset({"template", "mixin"}),
        allowed_scopes=frozenset({Scope.SYL}),
        description="Filter by the requested inline-fx tag.",
    ),
    "styles": ModifierSpecification(
        keyword="styles",
        aliases=(),
        takes_argument=True,
        applicable_to=frozenset({"template", "code"}),
        allowed_scopes=STYLE_SCOPES,
        description="Filter karaoke events by a tuple of style names.",
    ),
    "when": ModifierSpecification(
        keyword="when",
        aliases=(),
        takes_argument=True,
        applicable_to=frozenset({"template", "mixin"}),
        allowed_scopes=TEMPLATE_SCOPES,
        description="Apply the template only when the condition is true.",
    ),
    "unless": ModifierSpecification(
        keyword="unless",
        aliases=(),
        takes_argument=True,
        applicable_to=frozenset({"template", "mixin"}),
        allowed_scopes=TEMPLATE_SCOPES,
        description="Apply the template only when the condition is false.",
    ),
    "prepend": ModifierSpecification(
        keyword="prepend",
        aliases=(),
        takes_argument=False,
        applicable_to=frozenset({"mixin"}),
        allowed_scopes=TEMPLATE_SCOPES,
        description="Insert the mixin before the template body.",
    ),
    "layer": ModifierSpecification(
        keyword="layer",
        aliases=(),
        takes_argument=True,
        applicable_to=frozenset({"mixin"}),
        allowed_scopes=TEMPLATE_SCOPES,
        description="Apply the mixin only to generated lines on this layer.",
    ),
    "for": ModifierSpecification(
        keyword="for",
        aliases=(),
        takes_argument=True,
        applicable_to=frozenset({"mixin"}),
        allowed_scopes=TEMPLATE_SCOPES,
        description="Apply the mixin only to templates with this actor.",
    ),
}
