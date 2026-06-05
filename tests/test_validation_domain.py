"""Unit tests for the phase 11 domain validation rules and validators."""

from __future__ import annotations

from dataclasses import replace

from pykara.data import Event, Metadata, Style, Syllable
from pykara.declaration import Scope
from pykara.declaration.code import CodeBody
from pykara.declaration.mixin import MixinBody, MixinModifiers
from pykara.declaration.template import (
    LoopDescriptor,
    TemplateBody,
    TemplateModifiers,
)
from pykara.parsing import (
    CodeDeclaration,
    MixinDeclaration,
    TemplateDeclaration,
)
from pykara.validation.reports import Severity
from pykara.validation.rules.code_rules import (
    CodeAllowedScopeRule,
    ValidPythonSyntaxRule,
)
from pykara.validation.rules.event_rules import (
    IncreasingEventTimeRule,
    RequiredEventStyleRule,
)
from pykara.validation.rules.karaoke_rules import (
    PositiveSyllableDurationRule,
)
from pykara.validation.rules.metadata_rules import (
    PositiveResolutionRule,
    PositiveVideoCorrectFactorRule,
)
from pykara.validation.rules.mixin_rules import (
    CompatibleMixinModifierScopeRule,
    MixinAllowedScopeRule,
    MixinPythonExpressionSyntaxRule,
)
from pykara.validation.rules.style_rules import (
    NonNegativeMarginsRule,
    PositiveFontSizeRule,
)
from pykara.validation.rules.template_rules import (
    CompatibleTemplateModifierScopeRule,
    PythonExpressionSyntaxRule,
    TemplateAllowedScopeRule,
)
from pykara.validation.validators import (
    CodeValidator,
    EventValidator,
    KaraokeValidator,
    MetadataValidator,
    MixinValidator,
    StyleValidator,
    TemplateValidator,
)


def make_metadata() -> Metadata:
    return Metadata(res_x=1920, res_y=1080, video_x_correct_factor=1.0)


def make_style() -> Style:
    return Style(
        name="Default",
        fontname="Arial",
        fontsize=42.0,
        primary_colour="&H00FFFFFF",
        secondary_colour="&H0000FFFF",
        outline_colour="&H00000000",
        back_colour="&H64000000",
        bold=False,
        italic=False,
        underline=False,
        strike_out=False,
        scale_x=100.0,
        scale_y=100.0,
        spacing=0.0,
        angle=0.0,
        border_style=1,
        outline=2.0,
        shadow=1.0,
        alignment=2,
        margin_l=10,
        margin_r=10,
        margin_t=10,
        margin_b=10,
        encoding=1,
    )


def make_event() -> Event:
    return Event(
        text="{\\k20}ka",
        effect="karaoke",
        style="Default",
        layer=0,
        start_time=100,
        end_time=400,
        comment=False,
        actor="Singer",
        margin_l=0,
        margin_r=0,
        margin_t=0,
        margin_b=0,
    )


def make_syllable() -> Syllable:
    return Syllable(
        index=1,
        raw_text="ka",
        text="ka",
        trimmed_text="ka",
        prespace="",
        postspace="",
        start_time=0,
        end_time=200,
        duration=200,
        kdur=20.0,
        tag="\\k20",
        inline_fx="",
        highlights=[],
    )


def make_template_declaration() -> TemplateDeclaration:
    return TemplateDeclaration(
        body=TemplateBody(r"{\pos($left,$top)}!x + 1!"),
        scope=Scope.SYL,
        modifiers=TemplateModifiers(),
    )


def make_code_declaration() -> CodeDeclaration:
    return CodeDeclaration(
        body=CodeBody("counter = 1\ncounter += 1"),
        scope=Scope.SYL,
    )


def make_mixin_declaration() -> MixinDeclaration:
    return MixinDeclaration(
        body=MixinBody(r"{\1c&HFFFFFF&}!x + 1!"),
        scope=Scope.SYL,
        modifiers=MixinModifiers(),
    )


class TestMetadataRules:
    def test_positive_resolution_rule_accepts_valid_metadata(self) -> None:
        assert PositiveResolutionRule().check(make_metadata()) is None

    def test_positive_resolution_rule_reports_invalid_metadata(self) -> None:
        violation = PositiveResolutionRule().check(
            replace(make_metadata(), res_x=0)
        )

        assert violation is not None
        assert violation.code == "metadata.resolution_positive"
        assert violation.severity is Severity.ERROR

    def test_positive_video_factor_rule_accepts_valid_metadata(self) -> None:
        assert PositiveVideoCorrectFactorRule().check(make_metadata()) is None

    def test_positive_video_factor_rule_reports_invalid_metadata(self) -> None:
        violation = PositiveVideoCorrectFactorRule().check(
            replace(make_metadata(), video_x_correct_factor=0.0)
        )

        assert violation is not None
        assert violation.code == "metadata.video_x_correct_factor_positive"
        assert violation.severity is Severity.ERROR

    def test_metadata_validator_aggregates_rule_results(self) -> None:
        report = MetadataValidator().validate(
            Metadata(res_x=0, res_y=1080, video_x_correct_factor=-1.0)
        )

        assert tuple(violation.code for violation in report.violations) == (
            "metadata.resolution_positive",
            "metadata.video_x_correct_factor_positive",
        )


class TestStyleRules:
    def test_positive_font_size_rule_accepts_valid_style(self) -> None:
        assert PositiveFontSizeRule().check(make_style()) is None

    def test_positive_font_size_rule_reports_invalid_style(self) -> None:
        violation = PositiveFontSizeRule().check(
            replace(make_style(), fontsize=0.0)
        )

        assert violation is not None
        assert violation.code == "style.fontsize_positive"
        assert violation.severity is Severity.ERROR

    def test_non_negative_margins_rule_accepts_valid_style(self) -> None:
        assert NonNegativeMarginsRule().check(make_style()) is None

    def test_non_negative_margins_rule_reports_invalid_style(self) -> None:
        violation = NonNegativeMarginsRule().check(
            replace(make_style(), margin_r=-1)
        )

        assert violation is not None
        assert violation.code == "style.margins_non_negative"
        assert violation.severity is Severity.ERROR

    def test_style_validator_aggregates_rule_results(self) -> None:
        report = StyleValidator().validate(
            replace(make_style(), fontsize=-2.0, margin_b=-1)
        )

        assert tuple(violation.code for violation in report.violations) == (
            "style.fontsize_positive",
            "style.margins_non_negative",
        )


class TestEventRules:
    def test_increasing_event_time_rule_accepts_valid_event(self) -> None:
        assert IncreasingEventTimeRule().check(make_event()) is None

    def test_increasing_event_time_rule_reports_invalid_event(self) -> None:
        violation = IncreasingEventTimeRule().check(
            replace(make_event(), start_time=400, end_time=400)
        )

        assert violation is not None
        assert violation.code == "event.time_order"
        assert violation.severity is Severity.ERROR

    def test_increasing_event_time_rule_ignores_zero_length_directives(
        self,
    ) -> None:
        event = replace(
            make_event(),
            text=r"{\pos($syl_center,$syl_middle)}",
            effect="template syl",
            start_time=0,
            end_time=0,
            comment=True,
        )

        assert IncreasingEventTimeRule().check(event) is None

    def test_increasing_event_time_rule_ignores_plain_zero_length_karaoke(
        self,
    ) -> None:
        event = replace(
            make_event(),
            text="plain text without timed syllables",
            start_time=0,
            end_time=0,
        )

        assert IncreasingEventTimeRule().check(event) is None

    def test_required_event_style_rule_accepts_valid_event(self) -> None:
        assert RequiredEventStyleRule().check(make_event()) is None

    def test_required_event_style_rule_reports_invalid_event(self) -> None:
        violation = RequiredEventStyleRule().check(
            replace(make_event(), style="   ")
        )

        assert violation is not None
        assert violation.code == "event.style_required"
        assert violation.severity is Severity.ERROR

    def test_event_validator_aggregates_rule_results(self) -> None:
        report = EventValidator().validate(
            replace(make_event(), start_time=500, end_time=400, style="")
        )

        assert tuple(violation.code for violation in report.violations) == (
            "event.time_order",
            "event.style_required",
        )


class TestKaraokeRules:
    def test_positive_syllable_duration_rule_accepts_valid_syllable(
        self,
    ) -> None:
        assert PositiveSyllableDurationRule().check(make_syllable()) is None

    def test_positive_syllable_duration_rule_accepts_zero_duration_syllable(
        self,
    ) -> None:
        assert (
            PositiveSyllableDurationRule().check(
                replace(make_syllable(), duration=0, end_time=0, kdur=0.0)
            )
            is None
        )

    def test_positive_syllable_duration_rule_reports_invalid_syllable(
        self,
    ) -> None:
        violation = PositiveSyllableDurationRule().check(
            replace(make_syllable(), duration=-1)
        )

        assert violation is not None
        assert violation.code == "karaoke.duration_positive"
        assert violation.severity is Severity.ERROR

    def test_karaoke_validator_aggregates_rule_results(self) -> None:
        report = KaraokeValidator().validate(
            replace(
                make_syllable(),
                duration=-1,
                text="   ",
                trimmed_text="",
            )
        )

        assert tuple(violation.code for violation in report.violations) == (
            "karaoke.duration_positive",
        )


class TestTemplateRules:
    def test_template_allowed_scope_rule_accepts_valid_template(self) -> None:
        assert (
            TemplateAllowedScopeRule().check(make_template_declaration())
            is None
        )

    def test_template_allowed_scope_rule_reports_invalid_template(self) -> None:
        violation = TemplateAllowedScopeRule().check(
            replace(make_template_declaration(), scope=Scope.SETUP)
        )

        assert violation is not None
        assert violation.code == "template.scope_allowed"
        assert violation.severity is Severity.ERROR

    def test_python_expression_rule_accepts_python_expression(self) -> None:
        assert (
            PythonExpressionSyntaxRule().check(make_template_declaration())
            is None
        )

    def test_python_expression_rule_reports_unsupported_syntax(self) -> None:
        violation = PythonExpressionSyntaxRule().check(
            replace(
                make_template_declaration(),
                body=TemplateBody("!value .. other!"),
            )
        )

        assert violation is not None
        assert violation.code == "template.expression_python_only"
        assert violation.severity is Severity.ERROR

    def test_modifier_scope_rule_accepts_compatible_modifiers(self) -> None:
        declaration = replace(
            make_template_declaration(),
            modifiers=TemplateModifiers(no_blank=True),
        )

        assert CompatibleTemplateModifierScopeRule().check(declaration) is None

    def test_modifier_scope_rule_accepts_line_no_text(self) -> None:
        declaration = replace(
            make_template_declaration(),
            scope=Scope.LINE,
            modifiers=TemplateModifiers(no_text=True),
        )

        assert CompatibleTemplateModifierScopeRule().check(declaration) is None

    def test_modifier_scope_rule_accepts_line_no_merge(self) -> None:
        declaration = replace(
            make_template_declaration(),
            scope=Scope.LINE,
            modifiers=TemplateModifiers(no_merge=True),
        )

        assert CompatibleTemplateModifierScopeRule().check(declaration) is None

    def test_modifier_scope_rule_accepts_all_compatible_modifiers(
        self,
    ) -> None:
        declaration = replace(
            make_template_declaration(),
            modifiers=TemplateModifiers(
                loops=(LoopDescriptor(name="spark", iterations=2),),
                no_blank=True,
                no_merge=True,
                no_text=True,
                fx="flash",
                styles="selected_styles",
                when="enabled",
                unless="muted",
            ),
        )

        assert CompatibleTemplateModifierScopeRule().check(declaration) is None

    def test_modifier_scope_rule_reports_incompatible_modifier(self) -> None:
        declaration = replace(
            make_template_declaration(),
            scope=Scope.LINE,
            modifiers=TemplateModifiers(fx="flash"),
        )

        violation = CompatibleTemplateModifierScopeRule().check(declaration)

        assert violation is not None
        assert violation.code == "template.modifier_scope_compatible"
        assert violation.severity is Severity.ERROR

    def test_template_validator_aggregates_rule_results(self) -> None:
        report = TemplateValidator().validate(
            TemplateDeclaration(
                body=TemplateBody("!value .. other!"),
                scope=Scope.LINE,
                modifiers=TemplateModifiers(fx="flash"),
            )
        )

        assert tuple(violation.code for violation in report.violations) == (
            "template.expression_python_only",
            "template.modifier_scope_compatible",
        )


class TestCodeRules:
    def test_code_allowed_scope_rule_accepts_valid_code(self) -> None:
        assert CodeAllowedScopeRule().check(make_code_declaration()) is None

    def test_code_allowed_scope_rule_reports_invalid_code(self) -> None:
        violation = CodeAllowedScopeRule().check(
            replace(make_code_declaration(), scope=Scope.CHAR)
        )

        assert violation is not None
        assert violation.code == "code.scope_allowed"
        assert violation.severity is Severity.ERROR

    def test_valid_python_syntax_rule_accepts_valid_code(self) -> None:
        assert ValidPythonSyntaxRule().check(make_code_declaration()) is None

    def test_valid_python_syntax_rule_reports_invalid_code(self) -> None:
        violation = ValidPythonSyntaxRule().check(
            replace(
                make_code_declaration(),
                body=CodeBody("if True print('x')"),
            )
        )

        assert violation is not None
        assert violation.code == "code.python_syntax"
        assert violation.severity is Severity.ERROR

    def test_code_validator_aggregates_rule_results(self) -> None:
        report = CodeValidator().validate(
            CodeDeclaration(
                body=CodeBody("local value = foo .. bar"),
                scope=Scope.CHAR,
            )
        )

        assert tuple(violation.code for violation in report.violations) == (
            "code.scope_allowed",
            "code.python_syntax",
        )


class TestMixinRules:
    def test_mixin_allowed_scope_rule_accepts_valid_mixin(self) -> None:
        assert MixinAllowedScopeRule().check(make_mixin_declaration()) is None

    def test_mixin_allowed_scope_rule_reports_invalid_mixin(self) -> None:
        violation = MixinAllowedScopeRule().check(
            replace(make_mixin_declaration(), scope=Scope.SETUP)
        )

        assert violation is not None
        assert violation.code == "mixin.scope_allowed"
        assert violation.severity is Severity.ERROR

    def test_mixin_python_expression_rule_accepts_python_expression(
        self,
    ) -> None:
        assert (
            MixinPythonExpressionSyntaxRule().check(make_mixin_declaration())
            is None
        )

    def test_mixin_python_expression_rule_reports_unsupported_syntax(
        self,
    ) -> None:
        violation = MixinPythonExpressionSyntaxRule().check(
            replace(
                make_mixin_declaration(),
                body=MixinBody("!value .. other!"),
            )
        )

        assert violation is not None
        assert violation.code == "mixin.expression_python_only"
        assert violation.severity is Severity.ERROR

    def test_mixin_modifier_scope_rule_accepts_compatible_modifiers(
        self,
    ) -> None:
        declaration = replace(
            make_mixin_declaration(),
            modifiers=MixinModifiers(
                prepend=True,
                layer=2,
                for_actor="lead",
                when="enabled",
                unless="muted",
            ),
        )

        assert CompatibleMixinModifierScopeRule().check(declaration) is None

    def test_mixin_modifier_scope_rule_reports_incompatible_modifier(
        self,
    ) -> None:
        violation = CompatibleMixinModifierScopeRule().check(
            replace(
                make_mixin_declaration(),
                scope=Scope.LINE,
                modifiers=MixinModifiers(fx="flash"),
            )
        )

        assert violation is not None
        assert violation.code == "mixin.modifier_scope_compatible"
        assert violation.severity is Severity.ERROR

    def test_mixin_validator_aggregates_rule_results(self) -> None:
        report = MixinValidator().validate(
            MixinDeclaration(
                body=MixinBody("!value .. other!"),
                scope=Scope.LINE,
                modifiers=MixinModifiers(fx="flash"),
            )
        )

        assert tuple(violation.code for violation in report.violations) == (
            "mixin.expression_python_only",
            "mixin.modifier_scope_compatible",
        )
