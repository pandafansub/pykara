"""Integration tests for phase 12 cross and document validation."""

from __future__ import annotations

from pykara.adapters import SubtitleDocument
from pykara.data import Event, Metadata, Style
from pykara.declaration import Scope
from pykara.declaration.code import CodeBody, CodeModifiers
from pykara.declaration.mixin import MixinBody, MixinModifiers
from pykara.declaration.template import (
    LoopDescriptor,
    TemplateBody,
    TemplateModifiers,
)
from pykara.parsing import (
    CodeDeclaration,
    MixinDeclaration,
    ParsedDeclarations,
    TemplateDeclaration,
)
from pykara.validation.reports import Severity, ValidationReport
from pykara.validation.validators import CrossValidator, DocumentValidator


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


def make_event(
    *,
    text: str = "{\\k20}ka",
    effect: str = "karaoke",
    style: str = "Default",
    comment: bool = False,
) -> Event:
    return Event(
        text=text,
        effect=effect,
        style=style,
        layer=0,
        start_time=100,
        end_time=400,
        comment=comment,
        actor="Singer",
        margin_l=0,
        margin_r=0,
        margin_t=0,
        margin_b=0,
    )


def make_template_declaration(
    *,
    text: str = "{\\pos($line_left,$line_top)}",
    scope: Scope = Scope.SYL,
    modifiers: TemplateModifiers | None = None,
    style: str = "",
) -> TemplateDeclaration:
    return TemplateDeclaration(
        body=TemplateBody(text),
        scope=scope,
        modifiers=modifiers or TemplateModifiers(),
        style=style,
        actor="lead",
    )


def make_mixin_declaration(
    *,
    text: str = "{\\bord4}",
    scope: Scope = Scope.SYL,
    modifiers: MixinModifiers | None = None,
    actor: str = "lead",
) -> MixinDeclaration:
    return MixinDeclaration(
        body=MixinBody(text),
        scope=scope,
        modifiers=modifiers or MixinModifiers(),
        actor=actor,
    )


def make_code_declaration(
    *,
    source: str = "counter = 1",
    scope: Scope = Scope.SYL,
) -> CodeDeclaration:
    return CodeDeclaration(body=CodeBody(source), scope=scope)


def make_document(*, events: list[Event] | None = None) -> SubtitleDocument:
    style = make_style()
    return SubtitleDocument(
        metadata=Metadata(res_x=1920, res_y=1080),
        styles={style.name: style},
        events=events or [make_event()],
    )


class TestCrossValidator:
    def test_accepts_valid_document_and_declarations(self) -> None:
        document = make_document()
        declarations = ParsedDeclarations(
            syl=[make_template_declaration(text="{\\pos($syl_x,$syl_y)}")]
        )

        report = CrossValidator().validate(document, declarations)

        assert report.violations == ()

    def test_reports_missing_style_reference(self) -> None:
        document = make_document(events=[make_event(style="Missing")])

        report = CrossValidator().validate(document, ParsedDeclarations())

        assert tuple(violation.code for violation in report.violations) == (
            "cross.style_exists",
        )

    def test_reports_syl_variable_used_in_line_scope(self) -> None:
        declarations = ParsedDeclarations(
            line=[
                make_template_declaration(
                    text="{\\pos($syl_x,$syl_y)}",
                    scope=Scope.LINE,
                )
            ]
        )

        report = CrossValidator().validate(make_document(), declarations)

        assert tuple(violation.code for violation in report.violations) == (
            "cross.variable_scope_allowed",
            "cross.variable_scope_allowed",
        )

    def test_reports_char_variable_used_in_syl_scope(self) -> None:
        declarations = ParsedDeclarations(
            syl=[
                make_template_declaration(
                    text="char=$char_x",
                    scope=Scope.SYL,
                )
            ]
        )

        report = CrossValidator().validate(make_document(), declarations)

        assert tuple(violation.code for violation in report.violations) == (
            "cross.variable_scope_allowed",
        )

    def test_ignores_unknown_template_variables(self) -> None:
        declarations = ParsedDeclarations(
            syl=[
                make_template_declaration(
                    text="$custom_name",
                    scope=Scope.SYL,
                )
            ]
        )

        report = CrossValidator().validate(make_document(), declarations)

        assert report.violations == ()

    def test_accepts_quoted_string_arguments(self) -> None:
        declarations = ParsedDeclarations(
            syl=[
                make_template_declaration(
                    text=(
                        "!put('name', 123)!!lock('name', 123)!"
                        "!get('name')!"
                        "!color.interpolate(0.5, '&H000000&', '&HFFFFFF&')!"
                    ),
                )
            ]
        )

        report = CrossValidator().validate(make_document(), declarations)

        assert report.violations == ()

    def test_reports_bare_string_arguments(self) -> None:
        declarations = ParsedDeclarations(
            syl=[
                make_template_declaration(
                    text=(
                        "!put(name, 123)!!lock(name, 123)!!get(name)!"
                        "!color.interpolate(0.5, red, blue)!"
                    ),
                )
            ]
        )

        report = CrossValidator().validate(make_document(), declarations)

        assert tuple(violation.code for violation in report.violations) == (
            "cross.string_argument_quoted",
            "cross.string_argument_quoted",
            "cross.string_argument_quoted",
            "cross.string_argument_quoted",
            "cross.string_argument_quoted",
        )
        assert tuple(violation.context for violation in report.violations) == (
            "function='put', argument='key', value='name', scope=syl",
            "function='lock', argument='key', value='name', scope=syl",
            "function='get', argument='key', value='name', scope=syl",
            (
                "function='color.interpolate', argument='start_color', "
                "value='red', scope=syl"
            ),
            (
                "function='color.interpolate', argument='end_color', "
                "value='blue', scope=syl"
            ),
        )

    def test_reports_bare_string_keyword_arguments(self) -> None:
        declarations = ParsedDeclarations(
            syl=[
                make_template_declaration(
                    text="!put(key=name, value=123)!",
                )
            ]
        )

        report = CrossValidator().validate(make_document(), declarations)

        assert tuple(violation.code for violation in report.violations) == (
            "cross.string_argument_quoted",
        )
        assert tuple(violation.context for violation in report.violations) == (
            "function='put', argument='key', value='name', scope=syl",
        )

    def test_ignores_calls_without_string_argument_violations(self) -> None:
        declarations = ParsedDeclarations(
            syl=[
                make_template_declaration(
                    text=(
                        "!(lambda: 1)()!"
                        "!helper(name)!"
                        "!color.interpolate("
                        "progress, '&H000000&', '&HFFFFFF&'"
                        ")!"
                        "!put(key='name', value=value)!"
                        "!put('name', 1, extra)!"
                    ),
                )
            ]
        )

        report = CrossValidator().validate(make_document(), declarations)

        assert report.violations == ()

    def test_ignores_invalid_inline_python_for_string_arguments(self) -> None:
        declarations = ParsedDeclarations(
            syl=[
                make_template_declaration(
                    text="!put(!",
                )
            ]
        )

        report = CrossValidator().validate(make_document(), declarations)

        assert report.violations == ()

    def test_reports_bare_string_arguments_in_code_declarations(self) -> None:
        declarations = ParsedDeclarations(
            setup=[
                make_code_declaration(
                    source="value = color.interpolate(0.5, red, blue)",
                    scope=Scope.SETUP,
                )
            ]
        )

        report = CrossValidator().validate(make_document(), declarations)

        assert tuple(violation.code for violation in report.errors) == (
            "cross.string_argument_quoted",
            "cross.string_argument_quoted",
        )
        assert tuple(violation.context for violation in report.errors) == (
            (
                "function='color.interpolate', argument='start_color', "
                "value='red', scope=setup"
            ),
            (
                "function='color.interpolate', argument='end_color', "
                "value='blue', scope=setup"
            ),
        )

    def test_reports_bare_string_arguments_in_word_code_declarations(
        self,
    ) -> None:
        declarations = ParsedDeclarations(
            word=[
                make_code_declaration(
                    source="value = put(name, 1)",
                    scope=Scope.WORD,
                )
            ]
        )

        report = CrossValidator().validate(make_document(), declarations)

        assert tuple(violation.code for violation in report.errors) == (
            "cross.string_argument_quoted",
        )
        assert tuple(violation.context for violation in report.errors) == (
            "function='put', argument='key', value='name', scope=word",
        )

    def test_reports_unused_code_declarations_as_warnings(self) -> None:
        declarations = ParsedDeclarations(
            setup=[
                make_code_declaration(
                    source=(
                        "accent = '&H00AAFF&'\nderived = accent\nunused = 1"
                    ),
                    scope=Scope.SETUP,
                )
            ],
            syl=[
                make_template_declaration(
                    text=r"{\1c$accent}!derived!",
                )
            ],
        )

        report = CrossValidator().validate(make_document(), declarations)

        assert tuple(violation.code for violation in report.violations) == (
            "cross.unused_code_declaration",
        )
        assert report.violations[0].severity is Severity.WARNING
        assert report.violations[0].message == (
            "Code variable 'unused' is declared but never used."
        )
        assert report.violations[0].context == (
            "name='unused', kind=variable, scope=setup"
        )

    def test_reports_unused_code_functions_as_warnings(self) -> None:
        declarations = ParsedDeclarations(
            setup=[
                make_code_declaration(
                    source="def pick():\n    return '&H00AAFF&'",
                    scope=Scope.SETUP,
                )
            ],
            syl=[
                make_template_declaration(
                    text=r"{\1c&HFFFFFF&}",
                )
            ],
        )

        report = CrossValidator().validate(make_document(), declarations)

        assert tuple(violation.code for violation in report.violations) == (
            "cross.unused_code_declaration",
        )
        assert report.violations[0].severity is Severity.WARNING
        assert report.violations[0].message == (
            "Code function 'pick' is declared but never used."
        )
        assert report.violations[0].context == (
            "name='pick', kind=function, scope=setup"
        )

    def test_accepts_code_names_used_by_modifiers_and_mixins(
        self,
    ) -> None:
        declarations = ParsedDeclarations(
            setup=[
                make_code_declaration(
                    source=(
                        "accent = '&H00AAFF&'\n"
                        "enabled = True\n"
                        "repeat_count = 2\n"
                        "my_styles = ('Default',)"
                    ),
                    scope=Scope.SETUP,
                )
            ],
            syl=[
                make_template_declaration(
                    modifiers=TemplateModifiers(
                        loops=(LoopDescriptor("spark", "repeat_count"),),
                        styles="my_styles",
                        when="enabled",
                    ),
                )
            ],
            mixin_syl=[
                make_mixin_declaration(
                    text=r"{\1c$accent}!repeat_count!",
                )
            ],
        )

        report = CrossValidator().validate(make_document(), declarations)

        assert report.violations == ()

    def test_reports_unused_code_declarations_from_every_code_scope(
        self,
    ) -> None:
        declarations = ParsedDeclarations(
            setup=[
                make_code_declaration(
                    source="setup_unused = 1",
                    scope=Scope.SETUP,
                )
            ],
            line=[
                make_code_declaration(
                    source="line_unused = 1",
                    scope=Scope.LINE,
                )
            ],
            word=[
                make_code_declaration(
                    source="word_unused = 1",
                    scope=Scope.WORD,
                )
            ],
            syl=[
                make_code_declaration(
                    source="syl_unused = 1",
                    scope=Scope.SYL,
                )
            ],
        )

        report = CrossValidator().validate(make_document(), declarations)

        assert tuple(violation.context for violation in report.warnings) == (
            "name='setup_unused', kind=variable, scope=setup",
            "name='line_unused', kind=variable, scope=line",
            "name='syl_unused', kind=variable, scope=syl",
            "name='word_unused', kind=variable, scope=word",
        )

    def test_ignores_dunderseed_for_unused_code_declaration_warnings(
        self,
    ) -> None:
        declarations = ParsedDeclarations(
            setup=[
                make_code_declaration(
                    source="__seed__ = 7\nunused = 1",
                    scope=Scope.SETUP,
                )
            ],
        )

        report = CrossValidator().validate(make_document(), declarations)

        assert tuple(violation.context for violation in report.warnings) == (
            "name='unused', kind=variable, scope=setup",
        )

    def test_tracks_import_function_and_class_declarations(
        self,
    ) -> None:
        declarations = ParsedDeclarations(
            setup=[
                make_code_declaration(
                    source=(
                        "import math\n"
                        "import random as rng\n"
                        "from pathlib import Path\n"
                        "class Palette: pass\n"
                        "def helper(): return math.ceil(1.2)\n"
                        "async def async_helper(): return rng.randint(1, 2)"
                    ),
                    scope=Scope.SETUP,
                )
            ],
            syl=[
                make_template_declaration(
                    text="!helper()!-!async_helper!-!Palette!-!Path!",
                )
            ],
        )

        report = CrossValidator().validate(make_document(), declarations)

        assert report.violations == ()

    def test_ignores_local_function_class_and_comprehension_assignments(
        self,
    ) -> None:
        declarations = ParsedDeclarations(
            setup=[
                make_code_declaration(
                    source=(
                        "def helper():\n"
                        "    local_value = 1\n"
                        "    return [item for item in range(local_value)]\n"
                        "class Palette:\n"
                        "    local_attr = 1"
                    ),
                    scope=Scope.SETUP,
                )
            ],
            syl=[make_template_declaration(text="!helper!-!Palette!")],
        )

        report = CrossValidator().validate(make_document(), declarations)

        assert report.violations == ()

    def test_counts_augmented_assignment_as_code_usage(self) -> None:
        declarations = ParsedDeclarations(
            setup=[
                make_code_declaration(
                    source="counter = 1\ncounter += 1",
                    scope=Scope.SETUP,
                )
            ],
        )

        report = CrossValidator().validate(make_document(), declarations)

        assert report.violations == ()

    def test_uses_code_styles_modifier_as_variable_reference(self) -> None:
        declarations = ParsedDeclarations(
            setup=[
                make_code_declaration(
                    source="my_styles = ('Default',)",
                    scope=Scope.SETUP,
                )
            ],
            line=[
                CodeDeclaration(
                    body=CodeBody("pass"),
                    scope=Scope.LINE,
                    modifiers=CodeModifiers(styles="my_styles"),
                )
            ],
        )

        report = CrossValidator().validate(make_document(), declarations)

        assert report.violations == ()

    def test_invalid_code_syntax_does_not_add_unused_variable_warning(
        self,
    ) -> None:
        declarations = ParsedDeclarations(
            setup=[
                make_code_declaration(
                    source="broken =",
                    scope=Scope.SETUP,
                )
            ],
        )

        report = CrossValidator().validate(make_document(), declarations)

        assert tuple(violation.code for violation in report.violations) == ()

    def test_reports_fx_modifier_outside_syl_scope(self) -> None:
        declarations = ParsedDeclarations(
            line=[
                make_template_declaration(
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(fx="flash"),
                )
            ]
        )

        report = CrossValidator().validate(make_document(), declarations)

        assert tuple(violation.code for violation in report.violations) == (
            "cross.fx_scope_allowed",
        )

    def test_accepts_fx_modifier_in_syl_scope(self) -> None:
        declarations = ParsedDeclarations(
            syl=[
                make_template_declaration(
                    modifiers=TemplateModifiers(fx="flash"),
                )
            ]
        )

        report = CrossValidator().validate(make_document(), declarations)

        assert report.violations == ()

    def test_accepts_mixin_with_compatible_template(self) -> None:
        declarations = ParsedDeclarations(
            syl=[make_template_declaration()],
            mixin_syl=[make_mixin_declaration(actor="unrelated")],
        )

        report = CrossValidator().validate(make_document(), declarations)

        assert report.violations == ()

    def test_reports_mixin_for_actor_without_compatible_template(self) -> None:
        declarations = ParsedDeclarations(
            syl=[make_template_declaration()],
            mixin_syl=[
                make_mixin_declaration(
                    modifiers=MixinModifiers(for_actor="missing")
                )
            ],
        )

        report = CrossValidator().validate(make_document(), declarations)

        assert tuple(violation.code for violation in report.violations) == (
            "cross.mixin_template_compatible",
        )

    def test_reports_mixin_without_compatible_template(self) -> None:
        declarations = ParsedDeclarations(
            syl=[make_template_declaration()],
            mixin_word=[make_mixin_declaration(scope=Scope.WORD)],
        )

        report = CrossValidator().validate(make_document(), declarations)

        assert tuple(violation.code for violation in report.violations) == (
            "cross.mixin_template_compatible",
        )

    def test_reports_mixin_when_template_style_does_not_match(self) -> None:
        declarations = ParsedDeclarations(
            syl=[make_template_declaration(style="Alt")],
            mixin_syl=[make_mixin_declaration()],
        )

        report = CrossValidator().validate(make_document(), declarations)

        assert tuple(violation.code for violation in report.violations) == (
            "cross.mixin_template_compatible",
        )

    def test_reports_mixin_variable_used_outside_scope(self) -> None:
        declarations = ParsedDeclarations(
            line=[make_template_declaration(scope=Scope.LINE)],
            mixin_line=[
                make_mixin_declaration(text="$syl_x", scope=Scope.LINE)
            ],
        )

        report = CrossValidator().validate(make_document(), declarations)

        assert tuple(violation.code for violation in report.violations) == (
            "cross.variable_scope_allowed",
        )


class TestDocumentValidator:
    def test_validates_all_declaration_buckets(self) -> None:
        declarations = ParsedDeclarations(
            line=[make_template_declaration(scope=Scope.LINE)],
            word=[make_template_declaration(scope=Scope.WORD)],
            syl=[make_template_declaration(scope=Scope.SYL)],
            char=[make_template_declaration(scope=Scope.CHAR)],
            mixin_line=[make_mixin_declaration(scope=Scope.LINE)],
            mixin_word=[make_mixin_declaration(scope=Scope.WORD)],
            mixin_syl=[make_mixin_declaration(scope=Scope.SYL)],
            mixin_char=[make_mixin_declaration(scope=Scope.CHAR)],
            setup=[make_code_declaration(source="pass", scope=Scope.SETUP)],
        )

        report = DocumentValidator().validate(make_document(), declarations)

        assert report.violations == ()

    def test_validates_word_code_declarations(self) -> None:
        declarations = ParsedDeclarations(
            word=[
                make_code_declaration(
                    source="broken =",
                    scope=Scope.WORD,
                )
            ]
        )

        report = DocumentValidator().validate(make_document(), declarations)

        assert tuple(violation.code for violation in report.violations) == (
            "code.python_syntax",
        )

    def test_aggregates_cross_rule_violations(self) -> None:
        document = make_document(events=[make_event(style="Missing")])
        declarations = ParsedDeclarations(
            line=[
                make_template_declaration(
                    text="{\\pos($syl_x,$syl_y)}",
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(fx="flash"),
                ),
                make_code_declaration(scope=Scope.LINE),
            ]
        )

        report = DocumentValidator().validate(document, declarations)

        assert "cross.style_exists" in {
            violation.code for violation in report.violations
        }
        assert "cross.variable_scope_allowed" in {
            violation.code for violation in report.violations
        }
        assert "cross.fx_scope_allowed" in {
            violation.code for violation in report.violations
        }

    def test_accepts_timed_blank_karaoke_syllables(self) -> None:
        document = make_document(events=[make_event(text="{\\k20}   ")])

        report = DocumentValidator().validate(document, ParsedDeclarations())

        assert report.violations == ()

    def test_accepts_consecutive_leading_karaoke_tags_as_blank_syllable(
        self,
    ) -> None:
        document = make_document(
            events=[
                make_event(
                    text=(
                        "{\\k23}{\\k22}ka{\\k25}na{\\k77}shii "
                        "{\\k25}to{\\k43}ki"
                    )
                )
            ]
        )

        report = DocumentValidator().validate(document, ParsedDeclarations())

        assert report.violations == ()

    def test_accepts_zero_duration_karaoke_syllable_in_dialogue(self) -> None:
        document = make_document(
            events=[
                make_event(
                    text=r"{\k46}bomb{\k0}-{\k91}bomb {\k24}dan{\k65}cin'"
                )
            ]
        )

        report = DocumentValidator().validate(document, ParsedDeclarations())

        assert report.violations == ()

    def test_accepts_zero_duration_karaoke_syllable_in_comment(self) -> None:
        document = make_document(
            events=[
                make_event(
                    text=r"{\k46}bomb{\k0}-{\k91}bomb {\k24}dan{\k65}cin'",
                    comment=True,
                )
            ]
        )

        report = DocumentValidator().validate(document, ParsedDeclarations())

        assert report.violations == ()

    def test_validates_commented_karaoke_same_as_dialogue(self) -> None:
        class RecordingDocumentValidator(DocumentValidator):
            def __init__(self) -> None:
                super().__init__()
                self.seen_comments: list[bool] = []

            def _validate_event_karaoke(self, event: Event) -> ValidationReport:
                self.seen_comments.append(event.comment)
                return super()._validate_event_karaoke(event)

        validator = RecordingDocumentValidator()
        validator.validate(
            make_document(events=[make_event(text=r"{\k0}-", comment=False)]),
            ParsedDeclarations(),
        )
        validator.validate(
            make_document(events=[make_event(text=r"{\k0}-", comment=True)]),
            ParsedDeclarations(),
        )

        assert validator.seen_comments == [False, True]

    def test_ignores_k_tags_when_effect_is_not_karaoke(self) -> None:
        document = make_document(
            events=[make_event(text=r"{\k0}-", effect="", comment=False)]
        )

        report = DocumentValidator().validate(document, ParsedDeclarations())

        assert report.violations == ()

    def test_validates_ko_tags_for_karaoke_events(self) -> None:
        document = make_document(events=[make_event(text=r"{\ko0}go")])

        report = DocumentValidator().validate(document, ParsedDeclarations())

        assert report.violations == ()

    def test_skips_non_karaoke_events_for_karaoke_validation(self) -> None:
        document = make_document(events=[make_event(text="plain text")])

        report = DocumentValidator().validate(document, ParsedDeclarations())

        assert report.violations == ()
