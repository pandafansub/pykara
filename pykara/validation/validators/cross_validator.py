"""Validator for cross-document and cross-declaration rules."""

from __future__ import annotations

from collections.abc import Iterable

from pykara.adapters import SubtitleDocument
from pykara.parsing import (
    CodeDeclaration,
    MixinDeclaration,
    ParsedDeclarations,
    TemplateDeclaration,
)
from pykara.validation.reports import ValidationReport, Violation
from pykara.validation.rules.cross_rules import (
    AllowedVariableScopeRule,
    BareStringArgumentReference,
    CodeNameReference,
    DeclarationStyleReference,
    EventStyleReference,
    ExistingStyleRule,
    FxModifierScopeRule,
    FxModifierUsage,
    MixinTemplateCompatibilityRule,
    MixinTemplateReference,
    QuotedStringArgumentRule,
    TemplateVariableReference,
    UnusedCodeDeclarationRule,
    iter_bare_string_argument_references,
    iter_code_bare_string_argument_references,
    iter_code_declared_names,
    iter_code_name_references,
    iter_template_code_name_references,
    iter_template_variables,
)


class CrossValidator:
    """Validate relationships that span the document and declarations."""

    def __init__(self) -> None:
        self._style_rule = ExistingStyleRule()
        self._variable_scope_rule = AllowedVariableScopeRule()
        self._quoted_string_argument_rule = QuotedStringArgumentRule()
        self._fx_scope_rule = FxModifierScopeRule()
        self._mixin_template_rule = MixinTemplateCompatibilityRule()

    def validate(
        self,
        document: SubtitleDocument,
        declarations: ParsedDeclarations,
    ) -> ValidationReport:
        """Validate relationships that span document and declaration data.

        Args:
            document: Loaded subtitle document.
            declarations: Parsed declarations for that document.

        Returns:
            Validation report for cross-cutting rules.
        """
        violations = (
            *self._validate_style_references(document, declarations),
            *self._validate_template_variables(declarations),
            *self._validate_mixin_variables(declarations),
            *self._validate_quoted_string_arguments(declarations),
            *self._validate_code_declaration_usage(declarations),
            *self._validate_fx_usage(declarations),
            *self._validate_mixin_template_usage(declarations),
        )
        return ValidationReport(violations)

    def _validate_style_references(
        self,
        document: SubtitleDocument,
        declarations: ParsedDeclarations,
    ) -> tuple[Violation, ...]:
        available_styles = frozenset(document.styles)
        violations: list[Violation] = []
        for event in document.events:
            violation = self._style_rule.check(
                EventStyleReference(
                    event=event,
                    available_styles=available_styles,
                )
            )
            if violation is not None:
                violations.append(violation)

        for declaration in (
            *declarations.iter_scoped_declarations(),
            *declarations.iter_mixin_declarations(),
        ):
            if not declaration.style:
                continue
            violation = self._style_rule.check(
                DeclarationStyleReference(
                    declaration=declaration,
                    available_styles=available_styles,
                )
            )
            if violation is not None:
                violations.append(violation)
        return tuple(violations)

    def _validate_template_variables(
        self,
        declarations: ParsedDeclarations,
    ) -> tuple[Violation, ...]:
        return tuple(
            violation
            for declaration in declarations.iter_template_declarations()
            for name in iter_template_variables(declaration)
            if (
                violation := self._variable_scope_rule.check(
                    TemplateVariableReference(
                        declaration=declaration,
                        name=name,
                    )
                )
            )
            is not None
        )

    def _validate_fx_usage(
        self,
        declarations: ParsedDeclarations,
    ) -> tuple[Violation, ...]:
        return tuple(
            violation
            for declaration in (
                *declarations.iter_template_declarations(),
                *declarations.iter_mixin_declarations(),
            )
            if declaration.modifiers.fx is not None
            if (
                violation := self._fx_scope_rule.check(
                    FxModifierUsage(declaration=declaration)
                )
            )
            is not None
        )

    def _validate_quoted_string_arguments(
        self,
        declarations: ParsedDeclarations,
    ) -> tuple[Violation, ...]:
        return tuple(
            violation
            for reference in self._iter_bare_string_argument_references(
                declarations
            )
            if (violation := self._quoted_string_argument_rule.check(reference))
            is not None
        )

    def _validate_code_declaration_usage(
        self,
        declarations: ParsedDeclarations,
    ) -> tuple[Violation, ...]:
        references = tuple(self._iter_used_code_names(declarations))
        unused_rule = UnusedCodeDeclarationRule(used_names=frozenset())
        violations: list[Violation] = []
        for declaration in declarations.iter_code_declarations():
            for declared_name in iter_code_declared_names(declaration):
                if self._has_compatible_code_name_reference(
                    declared_name.declaration,
                    declared_name.name,
                    references,
                ):
                    continue
                violation = unused_rule.check(declared_name)
                if violation is not None:
                    violations.append(violation)
        return tuple(violations)

    def _validate_mixin_variables(
        self,
        declarations: ParsedDeclarations,
    ) -> tuple[Violation, ...]:
        return tuple(
            violation
            for declaration in declarations.iter_mixin_declarations()
            for name in iter_template_variables(declaration)
            if (
                violation := self._variable_scope_rule.check(
                    TemplateVariableReference(
                        declaration=declaration,
                        name=name,
                    )
                )
            )
            is not None
        )

    def _validate_mixin_template_usage(
        self,
        declarations: ParsedDeclarations,
    ) -> tuple[Violation, ...]:
        templates = tuple(declarations.iter_template_declarations())
        return tuple(
            violation
            for declaration in declarations.iter_mixin_declarations()
            if (
                violation := self._mixin_template_rule.check(
                    MixinTemplateReference(
                        mixin=declaration,
                        templates=templates,
                    )
                )
            )
            is not None
        )

    def _iter_bare_string_argument_references(
        self,
        declarations: ParsedDeclarations,
    ) -> Iterable[BareStringArgumentReference]:
        for declaration in (
            *declarations.iter_template_declarations(),
            *declarations.iter_mixin_declarations(),
            *declarations.iter_code_declarations(),
        ):
            if isinstance(declaration, CodeDeclaration):
                yield from iter_code_bare_string_argument_references(
                    declaration
                )
            else:
                yield from iter_bare_string_argument_references(declaration)

    def _iter_used_code_names(
        self,
        declarations: ParsedDeclarations,
    ) -> Iterable[CodeNameReference]:
        for declaration in declarations.iter_code_declarations():
            yield from iter_code_name_references(declaration)

        for declaration in (
            *declarations.iter_template_declarations(),
            *declarations.iter_mixin_declarations(),
        ):
            yield from iter_template_code_name_references(declaration)

    def _has_compatible_code_name_reference(
        self,
        declaration: CodeDeclaration,
        name: str,
        references: tuple[CodeNameReference, ...],
    ) -> bool:
        return any(
            reference.name == name
            and self._code_contexts_match(declaration, reference.declaration)
            for reference in references
        )

    def _code_contexts_match(
        self,
        declaration: CodeDeclaration,
        reference: CodeDeclaration | TemplateDeclaration | MixinDeclaration,
    ) -> bool:
        if not declaration.style or not reference.style:
            return True
        return declaration.style == reference.style
