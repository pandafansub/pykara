"""Cross-domain validation rules that inspect document relationships."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass

from pykara.data import Event
from pykara.parsing import (
    CodeDeclaration,
    MixinDeclaration,
    TemplateDeclaration,
)
from pykara.specification import (
    FUNCTION_SPECIFICATIONS,
    MODIFIER_SPECIFICATIONS,
    SCOPE_SPECIFICATIONS,
    VARIABLE_SPECIFICATIONS,
)
from pykara.support.code_analysis import (
    collect_assigned_name_kinds,
    collect_assigned_names,
    collect_loaded_names,
)
from pykara.validation.reports import Severity, Violation

_TEMPLATE_VARIABLE_PATTERN = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)")
_TEMPLATE_EXPRESSION_PATTERN = re.compile(r"!(.+?)!", re.DOTALL)
_SPECIAL_CODE_VARIABLE_NAMES = frozenset({"__seed__"})


@dataclass(frozen=True, slots=True)
class _StringArgumentSpec:
    positional_names: tuple[str, ...]
    keyword_names: frozenset[str]


def _string_argument_specs() -> dict[str, _StringArgumentSpec]:
    specs: dict[str, _StringArgumentSpec] = {}
    for function_name, specification in FUNCTION_SPECIFICATIONS.items():
        try:
            arguments = specification.signature.split("(", 1)[1].rsplit(
                ")",
                1,
            )[0]
        except IndexError:
            continue

        positional_names: list[str] = []
        keyword_names: set[str] = set()
        for argument in arguments.split(","):
            argument = argument.strip()
            if ":" not in argument:
                positional_names.append("")
                continue
            argument_name, annotation = argument.split(":", 1)
            argument_name = argument_name.strip()
            annotation = annotation.split("=", 1)[0].strip()
            positional_names.append(argument_name)
            if (
                annotation == "str"
                or "str |" in annotation
                or "| str" in annotation
            ):
                keyword_names.add(argument_name)

        if keyword_names:
            specs[function_name] = _StringArgumentSpec(
                positional_names=tuple(positional_names),
                keyword_names=frozenset(keyword_names),
            )
    return specs


_STRING_ARGUMENT_SPECS = _string_argument_specs()


@dataclass(frozen=True, slots=True)
class EventStyleReference:
    """One event-style reference to validate against the document styles."""

    event: Event
    available_styles: frozenset[str]


@dataclass(frozen=True, slots=True)
class DeclarationStyleReference:
    """One declaration-style reference to validate against document styles."""

    declaration: TemplateDeclaration | MixinDeclaration | CodeDeclaration
    available_styles: frozenset[str]


@dataclass(frozen=True, slots=True)
class TemplateVariableReference:
    """One variable reference found inside a template body."""

    declaration: TemplateDeclaration | MixinDeclaration
    name: str


@dataclass(frozen=True, slots=True)
class BareStringArgumentReference:
    """One string function argument written as a bare name."""

    declaration: TemplateDeclaration | MixinDeclaration | CodeDeclaration
    function_name: str
    argument_name: str
    value_name: str


@dataclass(frozen=True, slots=True)
class CodeNameDeclaration:
    """One user-facing name declared by a code declaration."""

    declaration: CodeDeclaration
    name: str
    declaration_kind: str = "variable"


@dataclass(frozen=True, slots=True)
class FxModifierUsage:
    """One declaration using the fx modifier."""

    declaration: TemplateDeclaration | MixinDeclaration


@dataclass(frozen=True, slots=True)
class MixinTemplateReference:
    """One mixin declaration to validate against template declarations."""

    mixin: MixinDeclaration
    templates: tuple[TemplateDeclaration, ...]


def iter_template_variables(
    declaration: TemplateDeclaration | MixinDeclaration,
) -> tuple[str, ...]:
    """Return all `$var` references found inside a template or mixin body."""

    return tuple(_TEMPLATE_VARIABLE_PATTERN.findall(declaration.body.text))


def iter_code_declared_names(
    declaration: CodeDeclaration,
) -> tuple[CodeNameDeclaration, ...]:
    """Return user namespace declarations from one code declaration."""

    try:
        tree = ast.parse(declaration.body.source, mode="exec")
    except SyntaxError:
        return ()

    name_kinds = collect_assigned_name_kinds(tree)
    declared_names = collect_assigned_names(tree) - _SPECIAL_CODE_VARIABLE_NAMES
    return tuple(
        CodeNameDeclaration(
            declaration=declaration,
            name=name,
            declaration_kind=name_kinds.get(name, "variable"),
        )
        for name in sorted(declared_names)
    )


def iter_code_name_references(
    declaration: CodeDeclaration,
) -> tuple[str, ...]:
    """Return Python names read by one code declaration."""

    try:
        tree = ast.parse(declaration.body.source, mode="exec")
    except SyntaxError:
        return ()

    references = set(collect_loaded_names(tree))
    if declaration.modifiers.styles is not None:
        references.add(declaration.modifiers.styles)
    return tuple(sorted(references))


def iter_template_code_name_references(
    declaration: TemplateDeclaration | MixinDeclaration,
) -> tuple[str, ...]:
    """Return code name references from a template-like declaration."""

    references = set(iter_template_variables(declaration))
    for expression in _TEMPLATE_EXPRESSION_PATTERN.findall(
        declaration.body.text
    ):
        references.update(_iter_expression_variable_references(expression))

    references.update(_iter_modifier_variable_references(declaration))
    return tuple(sorted(references))


def _iter_expression_variable_references(expression: str) -> tuple[str, ...]:
    normalized_expression = _TEMPLATE_VARIABLE_PATTERN.sub(
        lambda match: f"__pykara_var_{match.group(1)}",
        expression,
    )
    try:
        tree = ast.parse(normalized_expression, mode="eval")
    except SyntaxError:
        return ()

    loaded_names = collect_loaded_names(tree)
    return tuple(
        name
        for name in sorted(loaded_names)
        if not name.startswith("__pykara_var_")
    )


def _iter_modifier_variable_references(
    declaration: TemplateDeclaration | MixinDeclaration,
) -> tuple[str, ...]:
    references: set[str] = set()

    if isinstance(declaration, TemplateDeclaration):
        modifiers = declaration.modifiers
        if modifiers.styles is not None:
            references.add(modifiers.styles)
        for loop in modifiers.loops:
            if isinstance(loop.iterations, str):
                references.update(
                    _iter_expression_variable_references(loop.iterations)
                )

        if modifiers.when is not None:
            references.update(
                _iter_expression_variable_references(modifiers.when)
            )
        if modifiers.unless is not None:
            references.update(
                _iter_expression_variable_references(modifiers.unless)
            )
        return tuple(sorted(references))

    modifiers = declaration.modifiers
    if modifiers.when is not None:
        references.update(_iter_expression_variable_references(modifiers.when))
    if modifiers.unless is not None:
        references.update(
            _iter_expression_variable_references(modifiers.unless)
        )
    return tuple(sorted(references))


def iter_bare_string_argument_references(
    declaration: TemplateDeclaration | MixinDeclaration,
) -> tuple[BareStringArgumentReference, ...]:
    """Return function calls that use bare names for string arguments."""

    references: list[BareStringArgumentReference] = []
    for expression in _TEMPLATE_EXPRESSION_PATTERN.findall(
        declaration.body.text
    ):
        normalized_expression = _TEMPLATE_VARIABLE_PATTERN.sub(
            lambda match: f"__pykara_var_{match.group(1)}",
            expression,
        )
        try:
            tree = ast.parse(normalized_expression, mode="eval")
        except SyntaxError:
            continue

        references.extend(
            _bare_string_argument_references_from_tree(
                declaration,
                tree,
            )
        )
    return tuple(references)


def iter_code_bare_string_argument_references(
    declaration: CodeDeclaration,
) -> tuple[BareStringArgumentReference, ...]:
    """Return code calls that use bare names for string arguments."""

    try:
        tree = ast.parse(declaration.body.source, mode="exec")
    except SyntaxError:
        return ()

    return tuple(
        _bare_string_argument_references_from_tree(
            declaration,
            tree,
        )
    )


def _bare_string_argument_references_from_tree(
    declaration: TemplateDeclaration | MixinDeclaration | CodeDeclaration,
    tree: ast.AST,
) -> list[BareStringArgumentReference]:
    references: list[BareStringArgumentReference] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function_name = _call_name(node.func)
        if function_name is None:
            continue
        function_spec = _STRING_ARGUMENT_SPECS.get(function_name)
        if function_spec is None:
            continue

        for index, argument in enumerate(node.args):
            if not isinstance(argument, ast.Name):
                continue
            if index >= len(function_spec.positional_names):
                continue
            argument_name = function_spec.positional_names[index]
            if argument_name not in function_spec.keyword_names:
                continue
            references.append(
                BareStringArgumentReference(
                    declaration=declaration,
                    function_name=function_name,
                    argument_name=argument_name,
                    value_name=argument.id,
                )
            )

        for keyword in node.keywords:
            if keyword.arg not in function_spec.keyword_names:
                continue
            if not isinstance(keyword.value, ast.Name):
                continue
            references.append(
                BareStringArgumentReference(
                    declaration=declaration,
                    function_name=function_name,
                    argument_name=keyword.arg,
                    value_name=keyword.value.id,
                )
            )
    return references


def _call_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base_name = _call_name(node.value)
        if base_name is None:
            return None
        return f"{base_name}.{node.attr}"
    return None


@dataclass(frozen=True, slots=True)
class ExistingStyleRule:
    """Ensure referenced styles exist in the document."""

    code: str = "cross.style_exists"
    severity: Severity = Severity.ERROR

    def check(
        self,
        subject: EventStyleReference | DeclarationStyleReference,
    ) -> Violation | None:
        style_name = self._style_name(subject)
        if style_name in subject.available_styles:
            return None

        return Violation(
            severity=self.severity,
            code=self.code,
            message="Referenced style must exist in the document style map.",
            context=self._context(subject),
            location=self._location(subject),
        )

    def _style_name(
        self,
        subject: EventStyleReference | DeclarationStyleReference,
    ) -> str:
        if isinstance(subject, EventStyleReference):
            return subject.event.style
        return subject.declaration.style

    def _context(
        self,
        subject: EventStyleReference | DeclarationStyleReference,
    ) -> str:
        if isinstance(subject, EventStyleReference):
            return (
                f"style={subject.event.style!r}, "
                f"effect={subject.event.effect!r}"
            )
        return (
            f"style={subject.declaration.style!r}, "
            f"scope={subject.declaration.scope.value!r}"
        )

    def _location(
        self,
        subject: EventStyleReference | DeclarationStyleReference,
    ) -> str:
        if isinstance(subject, EventStyleReference):
            return "event.style"
        return "declaration.style"


@dataclass(frozen=True, slots=True)
class AllowedVariableScopeRule:
    """Ensure template variables belong to the current declaration scope."""

    code: str = "cross.variable_scope_allowed"
    severity: Severity = Severity.ERROR

    def check(self, subject: TemplateVariableReference) -> Violation | None:
        variable_specification = VARIABLE_SPECIFICATIONS.get(subject.name)
        if variable_specification is None:
            return None

        allowed_groups = SCOPE_SPECIFICATIONS[
            subject.declaration.scope
        ].variable_groups
        if variable_specification.group in allowed_groups:
            return None

        return Violation(
            severity=self.severity,
            code=self.code,
            message=("Variable is not available in this declaration scope."),
            context=(
                f"variable=${subject.name}, "
                f"group={variable_specification.group}, "
                f"scope={subject.declaration.scope.value}"
            ),
            location="declaration.body",
        )


@dataclass(frozen=True, slots=True)
class QuotedStringArgumentRule:
    """Ensure string function arguments are written as strings."""

    code: str = "cross.string_argument_quoted"
    severity: Severity = Severity.ERROR

    def check(self, subject: BareStringArgumentReference) -> Violation | None:
        return Violation(
            severity=self.severity,
            code=self.code,
            message="String function arguments must be quoted.",
            context=(
                f"function={subject.function_name!r}, "
                f"argument={subject.argument_name!r}, "
                f"value={subject.value_name!r}, "
                f"scope={subject.declaration.scope.value}"
            ),
            location="declaration.body",
        )


@dataclass(frozen=True, slots=True)
class UnusedCodeDeclarationRule:
    """Ensure names declared in code are used by the template document."""

    used_names: frozenset[str]
    code: str = "cross.unused_code_declaration"
    severity: Severity = Severity.WARNING

    def check(self, subject: CodeNameDeclaration) -> Violation | None:
        if subject.name in self.used_names:
            return None

        return Violation(
            severity=self.severity,
            code=self.code,
            message=(
                f"Code {subject.declaration_kind} "
                f"{subject.name!r} is declared "
                "but never used."
            ),
            context=(
                f"name={subject.name!r}, "
                f"kind={subject.declaration_kind}, "
                f"scope={subject.declaration.scope.value}"
            ),
            location="code.body",
        )


@dataclass(frozen=True, slots=True)
class FxModifierScopeRule:
    """Ensure the fx modifier is only used by syllable declarations."""

    code: str = "cross.fx_scope_allowed"
    severity: Severity = Severity.ERROR

    def check(self, subject: FxModifierUsage) -> Violation | None:
        allowed_scopes = MODIFIER_SPECIFICATIONS["fx"].allowed_scopes
        if subject.declaration.scope in allowed_scopes:
            return None

        return Violation(
            severity=self.severity,
            code=self.code,
            message="The fx modifier is only available in syllable scope.",
            context=f"scope={subject.declaration.scope.value!r}",
            location="declaration.modifiers.fx",
        )


@dataclass(frozen=True, slots=True)
class MixinTemplateCompatibilityRule:
    """Ensure every mixin has at least one compatible active template."""

    code: str = "cross.mixin_template_compatible"
    severity: Severity = Severity.ERROR

    def check(self, subject: MixinTemplateReference) -> Violation | None:
        if any(
            self._is_compatible(subject.mixin, template)
            for template in subject.templates
        ):
            return None

        return Violation(
            severity=self.severity,
            code=self.code,
            message=(
                "Mixin declaration must target at least one compatible "
                "template with the same scope and style."
            ),
            context=(
                f"scope={subject.mixin.scope.value!r}, "
                f"style={subject.mixin.style!r}, "
                f"for_actor={subject.mixin.modifiers.for_actor!r}"
            ),
            location="mixin",
        )

    def _is_compatible(
        self,
        mixin: MixinDeclaration,
        template: TemplateDeclaration,
    ) -> bool:
        if mixin.scope is not template.scope:
            return False
        if template.style and template.style != mixin.style:
            return False
        if mixin.modifiers.for_actor is None:
            return True
        return template.actor == mixin.modifiers.for_actor
