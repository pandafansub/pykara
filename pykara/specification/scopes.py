"""Scope-level language contracts."""

from __future__ import annotations

from dataclasses import dataclass

from pykara.declaration import Scope


@dataclass(frozen=True, slots=True)
class ScopeSpecification:
    """Describe what one execution scope means and exposes."""

    name: Scope
    description: str
    variable_groups: frozenset[str]


SCOPE_SPECIFICATIONS: dict[Scope, ScopeSpecification] = {
    Scope.SETUP: ScopeSpecification(
        Scope.SETUP,
        "Executed once before processing any karaoke line.",
        frozenset(),
    ),
    Scope.LINE: ScopeSpecification(
        Scope.LINE,
        "Executed once per karaoke line.",
        frozenset({"template_vars", "line_vars"}),
    ),
    Scope.WORD: ScopeSpecification(
        Scope.WORD,
        "Executed once per word.",
        frozenset({"template_vars", "line_vars", "word_vars"}),
    ),
    Scope.SYL: ScopeSpecification(
        Scope.SYL,
        "Executed once per syllable.",
        frozenset({"template_vars", "line_vars", "word_vars", "syl_vars"}),
    ),
    Scope.CHAR: ScopeSpecification(
        Scope.CHAR,
        "Executed once per character.",
        frozenset(
            {"template_vars", "line_vars", "word_vars", "syl_vars", "char_vars"}
        ),
    ),
}
