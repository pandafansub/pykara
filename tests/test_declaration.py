"""Unit tests for declaration bodies, modifier handlers, and registry."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

from pykara.declaration._shared import ModifierRegistry
from pykara.declaration.code import CodeBody, CodeModifiers, CodeStylesModifier
from pykara.declaration.mixin import (
    ForModifier,
    LayerModifier,
    MixinFxModifier,
    MixinModifiers,
    MixinUnlessModifier,
    MixinWhenModifier,
    PrependModifier,
)
from pykara.declaration.template import (
    TEMPLATE_MODIFIER_REGISTRY,
    FxModifier,
    LoopDescriptor,
    LoopModifier,
    NoBlankModifier,
    NoMergeModifier,
    NoTextModifier,
    StylesModifier,
    TemplateBody,
    TemplateModifiers,
    UnlessModifier,
    WhenModifier,
)
from pykara.errors import ModifierParseError, UnknownModifierError


class TestTemplateBody:
    def test_equality(self) -> None:
        assert TemplateBody("hello") == TemplateBody("hello")

    def test_is_frozen(self) -> None:
        body = TemplateBody("hello")
        attribute_name = "text"

        with pytest.raises(FrozenInstanceError):
            setattr(body, attribute_name, "updated")


class TestCodeBody:
    def test_equality(self) -> None:
        assert CodeBody("x = 1") == CodeBody("x = 1")

    def test_is_frozen(self) -> None:
        body = CodeBody("x = 1")
        attribute_name = "source"

        with pytest.raises(FrozenInstanceError):
            setattr(body, attribute_name, "x = 2")


class TestLoopModifier:
    def test_parses_unnamed_loop_and_consumes_token(self) -> None:
        modifier = LoopModifier()
        current = TemplateModifiers()

        result, remaining = modifier.apply(["3", "fx", "flash"], current)

        assert result == replace(
            current,
            loops=(LoopDescriptor(name="i", iterations=3),),
        )
        assert remaining == ["fx", "flash"]

    def test_parses_named_loop(self) -> None:
        modifier = LoopModifier()
        current = TemplateModifiers()

        result, remaining = modifier.apply(
            ["wave", "4", "fx", "flash"],
            current,
        )

        assert result == replace(
            current,
            loops=(
                LoopDescriptor(
                    name="wave",
                    iterations=4,
                    explicit_name="wave",
                ),
            ),
        )
        assert remaining == ["fx", "flash"]

    def test_raises_without_number(self) -> None:
        with pytest.raises(ModifierParseError) as exc_info:
            LoopModifier().apply(["abc"], TemplateModifiers())

        assert exc_info.value.modifier == "loop"

    @pytest.mark.parametrize("token", ["0", "-1"])
    def test_rejects_non_positive_counts(self, token: str) -> None:
        with pytest.raises(ModifierParseError):
            LoopModifier().apply([token], TemplateModifiers())

    def test_rejects_duplicate_unnamed_loops(self) -> None:
        current = TemplateModifiers(loops=(LoopDescriptor("i", 2),))

        with pytest.raises(ModifierParseError):
            LoopModifier().apply(["3"], current)

    def test_rejects_mixing_unnamed_and_named_loops(self) -> None:
        current = TemplateModifiers(loops=(LoopDescriptor("i", 2),))

        with pytest.raises(ModifierParseError):
            LoopModifier().apply(["wave", "3"], current)

    def test_rejects_duplicate_named_loops(self) -> None:
        current = TemplateModifiers(
            loops=(LoopDescriptor("wave", 2, explicit_name="wave"),)
        )

        with pytest.raises(ModifierParseError):
            LoopModifier().apply(["wave", "3"], current)


class TestNoBlankModifier:
    def test_sets_flag_and_consumes_nothing(self) -> None:
        modifier = NoBlankModifier()
        current = TemplateModifiers()

        result, remaining = modifier.apply(["fx", "flash"], current)

        assert result == replace(current, no_blank=True)
        assert remaining == ["fx", "flash"]


class TestNoTextModifier:
    def test_sets_flag_and_consumes_nothing(self) -> None:
        modifier = NoTextModifier()
        current = TemplateModifiers()

        result, remaining = modifier.apply(["loop", "2"], current)

        assert result == replace(current, no_text=True)
        assert remaining == ["loop", "2"]


class TestNoMergeModifier:
    def test_sets_flag_and_consumes_nothing(self) -> None:
        modifier = NoMergeModifier()
        current = TemplateModifiers()

        result, remaining = modifier.apply(["loop", "2"], current)

        assert result == replace(current, no_merge=True)
        assert remaining == ["loop", "2"]


class TestFxModifier:
    def test_parses_fx_name_and_consumes_token(self) -> None:
        modifier = FxModifier()
        current = TemplateModifiers()

        result, remaining = modifier.apply(["flash", "loop", "2"], current)

        assert result == replace(current, fx="flash")
        assert remaining == ["loop", "2"]

    def test_raises_without_argument(self) -> None:
        with pytest.raises(ModifierParseError) as exc_info:
            FxModifier().apply([], TemplateModifiers())

        assert exc_info.value.modifier == "fx"


class TestStylesModifier:
    def test_parses_styles_name_and_consumes_token(self) -> None:
        modifier = StylesModifier()
        current = TemplateModifiers()

        result, remaining = modifier.apply(["my_styles", "no_text"], current)

        assert result == replace(current, styles="my_styles")
        assert remaining == ["no_text"]

    def test_raises_without_argument(self) -> None:
        with pytest.raises(ModifierParseError) as exc_info:
            StylesModifier().apply([], TemplateModifiers())

        assert exc_info.value.modifier == "styles"


class TestCodeStylesModifier:
    def test_parses_styles_name_and_consumes_token(self) -> None:
        modifier = CodeStylesModifier()
        current = CodeModifiers()

        result, remaining = modifier.apply(["my_styles", "other"], current)

        assert result == replace(current, styles="my_styles")
        assert remaining == ["other"]

    def test_raises_without_argument(self) -> None:
        with pytest.raises(ModifierParseError) as exc_info:
            CodeStylesModifier().apply([], CodeModifiers())

        assert exc_info.value.modifier == "styles"


class TestMixinModifiers:
    def test_prepend_sets_flag_and_consumes_nothing(self) -> None:
        modifier = PrependModifier()
        current = MixinModifiers()

        result, remaining = modifier.apply(["layer", "2"], current)

        assert result == replace(current, prepend=True)
        assert remaining == ["layer", "2"]

    def test_layer_parses_integer_and_consumes_token(self) -> None:
        modifier = LayerModifier()
        current = MixinModifiers()

        result, remaining = modifier.apply(["2", "for", "actor"], current)

        assert result == replace(current, layer=2)
        assert remaining == ["for", "actor"]

    def test_layer_raises_without_argument(self) -> None:
        with pytest.raises(ModifierParseError) as exc_info:
            LayerModifier().apply([], MixinModifiers())

        assert exc_info.value.modifier == "layer"

    def test_layer_rejects_non_integer(self) -> None:
        with pytest.raises(ModifierParseError) as exc_info:
            LayerModifier().apply(["top"], MixinModifiers())

        assert exc_info.value.modifier == "layer"

    def test_for_parses_actor_and_consumes_token(self) -> None:
        modifier = ForModifier()
        current = MixinModifiers()

        result, remaining = modifier.apply(["Singer", "fx", "flash"], current)

        assert result == replace(current, for_actor="Singer")
        assert remaining == ["fx", "flash"]

    def test_for_raises_without_argument(self) -> None:
        with pytest.raises(ModifierParseError) as exc_info:
            ForModifier().apply([], MixinModifiers())

        assert exc_info.value.modifier == "for"

    def test_fx_parses_name_and_consumes_token(self) -> None:
        modifier = MixinFxModifier()
        current = MixinModifiers()

        result, remaining = modifier.apply(["flash", "prepend"], current)

        assert result == replace(current, fx="flash")
        assert remaining == ["prepend"]

    def test_fx_raises_without_argument(self) -> None:
        with pytest.raises(ModifierParseError) as exc_info:
            MixinFxModifier().apply([], MixinModifiers())

        assert exc_info.value.modifier == "fx"

    def test_when_parses_parenthesized_expression(self) -> None:
        modifier = MixinWhenModifier()
        current = MixinModifiers()

        result, remaining = modifier.apply(
            ["(line.actor", "==", '"lead")', "prepend"],
            current,
        )

        assert result == replace(current, when='(line.actor == "lead")')
        assert remaining == ["prepend"]

    def test_unless_parses_parenthesized_expression(self) -> None:
        modifier = MixinUnlessModifier()
        current = MixinModifiers()

        result, remaining = modifier.apply(
            ["(syl.i", "==", "0)", "layer", "2"],
            current,
        )

        assert result == replace(current, unless="(syl.i == 0)")
        assert remaining == ["layer", "2"]


class TestWhenModifier:
    def test_parses_single_token_condition(self) -> None:
        modifier = WhenModifier()
        current = TemplateModifiers()

        result, remaining = modifier.apply(
            ["group_red", "loop", "2"],
            current,
        )

        assert result == replace(current, when="group_red")
        assert remaining == ["loop", "2"]

    def test_parses_parenthesized_expression(self) -> None:
        modifier = WhenModifier()
        current = TemplateModifiers()

        result, remaining = modifier.apply(
            ["(line.actor", "==", '"red")', "fx", "flash"],
            current,
        )

        assert result == replace(current, when='(line.actor == "red")')
        assert remaining == ["fx", "flash"]

    def test_raises_without_argument(self) -> None:
        with pytest.raises(ModifierParseError) as exc_info:
            WhenModifier().apply([], TemplateModifiers())

        assert exc_info.value.modifier == "when"

    def test_raises_for_unclosed_parenthesized_expression(self) -> None:
        with pytest.raises(ModifierParseError) as exc_info:
            WhenModifier().apply(
                ["(line.actor", "==", '"red"', "fx"],
                TemplateModifiers(),
            )

        assert exc_info.value.modifier == "when"


class TestUnlessModifier:
    def test_parses_single_token_condition(self) -> None:
        modifier = UnlessModifier()
        current = TemplateModifiers()

        result, remaining = modifier.apply(
            ["group_red", "loop", "2"],
            current,
        )

        assert result == replace(current, unless="group_red")
        assert remaining == ["loop", "2"]

    def test_parses_parenthesized_expression(self) -> None:
        modifier = UnlessModifier()
        current = TemplateModifiers()

        result, remaining = modifier.apply(
            ["(line.actor", "==", '"red")', "fx", "flash"],
            current,
        )

        assert result == replace(current, unless='(line.actor == "red")')
        assert remaining == ["fx", "flash"]

    def test_raises_without_argument(self) -> None:
        with pytest.raises(ModifierParseError) as exc_info:
            UnlessModifier().apply([], TemplateModifiers())

        assert exc_info.value.modifier == "unless"


class TestModifierRegistry:
    def build_registry(self) -> ModifierRegistry[TemplateModifiers]:
        registry = ModifierRegistry(default=TemplateModifiers())
        registry.register(LoopModifier())
        registry.register(NoBlankModifier())
        registry.register(NoMergeModifier())
        registry.register(NoTextModifier())
        registry.register(FxModifier())
        registry.register(StylesModifier())
        registry.register(WhenModifier())
        registry.register(UnlessModifier())
        return registry

    def test_registers_aliases(self) -> None:
        registry = self.build_registry()

        result = registry.parse(["loop", "4"])

        assert result.loops == (LoopDescriptor(name="i", iterations=4),)

    def test_raises_unknown_modifier(self) -> None:
        registry = self.build_registry()

        with pytest.raises(UnknownModifierError) as exc_info:
            registry.parse(["mystery"])

        assert exc_info.value.modifier == "mystery"

    def test_parses_multiple_modifiers_sequentially(self) -> None:
        registry = self.build_registry()

        result = registry.parse(
            [
                "loop",
                "3",
                "no_blank",
                "no_merge",
                "no_text",
                "fx",
                "flash",
                "styles",
                "my_styles",
                "when",
                "(line.actor",
                "==",
                '"red")',
                "unless",
                "group_blue",
            ]
        )

        assert result == TemplateModifiers(
            loops=(LoopDescriptor(name="i", iterations=3),),
            no_blank=True,
            no_merge=True,
            no_text=True,
            fx="flash",
            styles="my_styles",
            when='(line.actor == "red")',
            unless="group_blue",
        )

    def test_parses_multiple_named_loops_in_order(self) -> None:
        registry = self.build_registry()

        result = registry.parse(["loop", "a", "2", "loop", "b", "3"])

        assert result.loops == (
            LoopDescriptor(name="a", iterations=2, explicit_name="a"),
            LoopDescriptor(name="b", iterations=3, explicit_name="b"),
        )


class TestTemplateModifierRegistry:
    def test_default_registry_is_ready_for_use(self) -> None:
        result = TEMPLATE_MODIFIER_REGISTRY.parse(
            ["loop", "2", "no_blank", "no_merge"]
        )

        assert result == TemplateModifiers(
            loops=(LoopDescriptor(name="i", iterations=2),),
            no_blank=True,
            no_merge=True,
        )
