"""Unit tests for the declaration parser."""

from __future__ import annotations

import pytest

from pykara.data import Event
from pykara.declaration import Scope
from pykara.declaration.code import CODE_MODIFIER_REGISTRY
from pykara.declaration.mixin import MIXIN_MODIFIER_REGISTRY
from pykara.declaration.template import TEMPLATE_MODIFIER_REGISTRY
from pykara.errors import DeclarativeParseError
from pykara.parsing import (
    CodeDeclaration,
    DeclarationParser,
    MixinDeclaration,
    ParsedDeclarations,
    TemplateDeclaration,
)


def make_event(
    *,
    effect: str,
    text: str = "",
    comment: bool = True,
    style: str = "Default",
    actor: str = "",
) -> Event:
    return Event(
        text=text,
        effect=effect,
        style=style,
        layer=0,
        start_time=0,
        end_time=0,
        comment=comment,
        actor=actor,
        margin_l=0,
        margin_r=0,
        margin_t=0,
        margin_b=0,
    )


class TestDeclarationParser:
    def build_parser(self) -> DeclarationParser:
        return DeclarationParser(
            template_mod_registry=TEMPLATE_MODIFIER_REGISTRY,
            mixin_mod_registry=MIXIN_MODIFIER_REGISTRY,
            code_mod_registry=CODE_MODIFIER_REGISTRY,
        )

    def test_parse_returns_grouped_declarations(self) -> None:
        parser = self.build_parser()

        parsed = parser.parse(
            [
                make_event(
                    effect="template line when group_red",
                    text="line body",
                    style="StyleA",
                ),
                make_event(
                    effect=(
                        "template syl fx flash styles my_styles "
                        "unless group_blue"
                    ),
                    text="syl body",
                    style="StyleB",
                ),
                make_event(
                    effect="template char no_blank no_merge no_text",
                    text="char body",
                    style="StyleB",
                    actor="lead",
                ),
                make_event(
                    effect="mixin char prepend layer 2 for lead when ok",
                    text="mixin body",
                    style="StyleB",
                ),
                make_event(
                    effect="code setup",
                    text="state = 1",
                    style="StyleSetup",
                ),
                make_event(
                    effect="code syl styles my_styles",
                    text="counter += 1",
                    style="StyleCode",
                ),
                make_event(
                    effect="karaoke",
                    text="{\\k20}ka",
                    style="Ignored",
                ),
                make_event(
                    effect="template syl",
                    text="not parsed",
                    comment=False,
                    style="Ignored",
                ),
            ]
        )

        assert isinstance(parsed, ParsedDeclarations)
        assert parsed.active_styles == {
            "StyleA",
            "StyleB",
            "StyleSetup",
            "StyleCode",
        }

        line_declaration = parsed.line[0]
        syl_template = parsed.syl[0]
        syl_code = parsed.syl[1]
        char_declaration = parsed.char[0]
        char_mixin = parsed.mixin_char[0]
        setup_declaration = parsed.setup[0]

        assert isinstance(line_declaration, TemplateDeclaration)
        assert line_declaration.scope is Scope.LINE
        assert line_declaration.body.text == "line body"
        assert line_declaration.modifiers.when == "group_red"

        assert isinstance(syl_template, TemplateDeclaration)
        assert syl_template.scope is Scope.SYL
        assert syl_template.modifiers.fx == "flash"
        assert syl_template.modifiers.styles == "my_styles"
        assert syl_template.modifiers.unless == "group_blue"

        assert isinstance(char_declaration, TemplateDeclaration)
        assert char_declaration.scope is Scope.CHAR
        assert char_declaration.modifiers.no_blank is True
        assert char_declaration.modifiers.no_merge is True
        assert char_declaration.modifiers.no_text is True
        assert char_declaration.actor == "lead"

        assert isinstance(char_mixin, MixinDeclaration)
        assert char_mixin.scope is Scope.CHAR
        assert char_mixin.body.text == "mixin body"
        assert char_mixin.modifiers.prepend is True
        assert char_mixin.modifiers.layer == 2
        assert char_mixin.modifiers.for_actor == "lead"
        assert char_mixin.modifiers.when == "ok"

        assert isinstance(setup_declaration, CodeDeclaration)
        assert setup_declaration.scope is Scope.SETUP
        assert setup_declaration.body.source == "state = 1"

        assert isinstance(syl_code, CodeDeclaration)
        assert syl_code.scope is Scope.SYL
        assert syl_code.modifiers.styles == "my_styles"
        assert syl_code.body.source == "counter += 1"

    def test_parse_supports_multiple_named_loops(self) -> None:
        parser = self.build_parser()

        parsed = parser.parse(
            [
                make_event(
                    effect="template syl loop wave 2 loop phase 3",
                    text="body",
                )
            ]
        )

        declaration = parsed.syl[0]
        assert isinstance(declaration, TemplateDeclaration)
        assert [loop.name for loop in declaration.modifiers.loops] == [
            "wave",
            "phase",
        ]
        assert [loop.iterations for loop in declaration.modifiers.loops] == [
            2,
            3,
        ]

    def test_parse_supports_loop_expressions(self) -> None:
        parser = self.build_parser()

        parsed = parser.parse(
            [
                make_event(
                    effect=(
                        "template syl loop j (math.floor($syl_width / 5) + 5)"
                    ),
                    text="body",
                )
            ]
        )

        declaration = parsed.syl[0]
        assert isinstance(declaration, TemplateDeclaration)
        assert declaration.modifiers.loops[0].name == "j"
        assert (
            declaration.modifiers.loops[0].iterations
            == "math.floor($syl_width / 5) + 5"
        )

    def test_parse_scopes_declarations_to_event_style_by_default(
        self,
    ) -> None:
        parser = self.build_parser()

        parsed = parser.parse(
            [
                make_event(
                    effect="template syl",
                    text="body",
                    style="Romaji",
                ),
                make_event(
                    effect="code syl all",
                    text="shared = 1",
                    style="Romaji",
                ),
            ]
        )

        template = parsed.syl[0]
        code = parsed.syl[1]
        assert isinstance(template, TemplateDeclaration)
        assert isinstance(code, CodeDeclaration)
        assert template.style == "Romaji"
        assert code.style == ""

    @pytest.mark.parametrize(
        ("effect", "message_part"),
        [
            ("template", "explicit scope"),
            ("code", "explicit scope"),
            ("mixin", "explicit scope"),
            ("template mystery", "Invalid scope"),
            ("code mystery", "Invalid scope"),
            ("mixin mystery", "Invalid scope"),
        ],
    )
    def test_parse_rejects_missing_or_invalid_scope(
        self,
        effect: str,
        message_part: str,
    ) -> None:
        parser = self.build_parser()

        with pytest.raises(DeclarativeParseError) as error_info:
            parser.parse([make_event(effect=effect, text="body")])

        assert error_info.value.effect_field == effect
        assert message_part in str(error_info.value)

    def test_parse_rejects_extra_token_after_template_scope(self) -> None:
        parser = self.build_parser()

        with pytest.raises(DeclarativeParseError) as error_info:
            parser.parse(
                [make_event(effect="template line mygroup", text="body")]
            )

        assert error_info.value.effect_field == "template line mygroup"
        assert "Unexpected token after template scope" in str(error_info.value)

    def test_parse_rejects_mixin_all_selector(self) -> None:
        parser = self.build_parser()

        with pytest.raises(DeclarativeParseError) as error_info:
            parser.parse([make_event(effect="mixin syl all", text="body")])

        assert error_info.value.effect_field == "mixin syl all"
        assert "'all' is not allowed" in str(error_info.value)

    def test_parse_rejects_template_only_modifiers_on_mixin(self) -> None:
        parser = self.build_parser()

        with pytest.raises(DeclarativeParseError) as error_info:
            parser.parse([make_event(effect="mixin syl loop 2", text="body")])

        assert error_info.value.effect_field == "mixin syl loop 2"
        assert "Unexpected token after mixin scope" in str(error_info.value)

    def test_parse_rejects_extra_token_after_code_scope(self) -> None:
        parser = self.build_parser()

        with pytest.raises(DeclarativeParseError) as error_info:
            parser.parse([make_event(effect="code setup extra", text="body")])

        assert error_info.value.effect_field == "code setup extra"
        assert "Unexpected token after code scope" in str(error_info.value)

    def test_parse_rejects_scope_not_allowed_for_declaration(self) -> None:
        parser = self.build_parser()

        with pytest.raises(DeclarativeParseError) as error_info:
            parser.parse([make_event(effect="code char", text="body")])

        assert error_info.value.effect_field == "code char"
        assert "not allowed" in str(error_info.value)
