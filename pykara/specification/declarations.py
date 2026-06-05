"""Public declaration-level language contracts."""

from __future__ import annotations

from dataclasses import dataclass

from pykara.declaration import Scope


@dataclass(frozen=True, slots=True)
class DeclarationSpecification:
    """Describe one declaration type supported by the language."""

    name: str
    allowed_scopes: frozenset[Scope]
    allowed_modifiers: frozenset[str]
    description: str


TEMPLATE_DECLARATION = DeclarationSpecification(
    name="template",
    allowed_scopes=frozenset({Scope.LINE, Scope.WORD, Scope.SYL, Scope.CHAR}),
    allowed_modifiers=frozenset(
        {
            "loop",
            "no_blank",
            "no_merge",
            "no_text",
            "fx",
            "styles",
            "when",
            "unless",
        }
    ),
    description="Generate effect lines from parameterized text.",
)

MIXIN_DECLARATION = DeclarationSpecification(
    name="mixin",
    allowed_scopes=frozenset({Scope.LINE, Scope.WORD, Scope.SYL, Scope.CHAR}),
    allowed_modifiers=frozenset(
        {"prepend", "layer", "for", "fx", "when", "unless"}
    ),
    description="Inject tags into generated template output.",
)

CODE_DECLARATION = DeclarationSpecification(
    name="code",
    allowed_scopes=frozenset({Scope.SETUP, Scope.LINE, Scope.WORD, Scope.SYL}),
    allowed_modifiers=frozenset({"styles"}),
    description="Execute Python code in the execution environment.",
)

DECLARATIONS: dict[str, DeclarationSpecification] = {
    TEMPLATE_DECLARATION.name: TEMPLATE_DECLARATION,
    MIXIN_DECLARATION.name: MIXIN_DECLARATION,
    CODE_DECLARATION.name: CODE_DECLARATION,
}
