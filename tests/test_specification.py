"""Consistency tests for the public language specification."""

from __future__ import annotations

from pykara.declaration import Scope
from pykara.specification import (
    CODE_DECLARATION,
    DECLARATIONS,
    EXPOSED_MODULES,
    EXPRESSION_OBJECT_SPECIFICATIONS,
    EXPRESSION_PROPERTY_SPECIFICATIONS,
    FUNCTION_SPECIFICATIONS,
    MIXIN_DECLARATION,
    MODIFIER_SPECIFICATIONS,
    SCOPE_SPECIFICATIONS,
    TEMPLATE_DECLARATION,
    VARIABLE_SPECIFICATIONS,
)

EXPECTED_TEMPLATE_VARIABLES = {
    "layer",
    "actor",
}

EXPECTED_LINE_VARIABLES = {
    "line_start",
    "line_end",
    "line_dur",
    "line_mid",
    "line_i",
    "line_left",
    "line_center",
    "line_right",
    "line_width",
    "line_top",
    "line_middle",
    "line_bottom",
    "line_height",
    "line_x",
    "line_y",
}

EXPECTED_WORD_VARIABLES = {
    "word_start",
    "word_end",
    "word_dur",
    "word_kdur",
    "word_mid",
    "word_n",
    "word_i",
    "word_left",
    "word_center",
    "word_right",
    "word_width",
    "word_top",
    "word_middle",
    "word_bottom",
    "word_height",
    "word_x",
    "word_y",
}

EXPECTED_SYL_VARIABLES = {
    "syl_start",
    "syl_end",
    "syl_dur",
    "syl_kdur",
    "syl_mid",
    "syl_n",
    "syl_i",
    "syl_left",
    "syl_center",
    "syl_right",
    "syl_width",
    "syl_top",
    "syl_middle",
    "syl_bottom",
    "syl_height",
    "syl_x",
    "syl_y",
}

EXPECTED_CHAR_VARIABLES = {
    "char_left",
    "char_i",
    "char_n",
    "char_center",
    "char_right",
    "char_width",
    "char_top",
    "char_middle",
    "char_bottom",
    "char_height",
    "char_x",
    "char_y",
}

EXPECTED_MATH_FUNCTIONS = {
    "math.floor",
    "math.ceil",
    "math.fabs",
    "math.sqrt",
    "math.sin",
    "math.cos",
    "math.radians",
}

EXPECTED_COLOR_FUNCTIONS = {
    "color.rgb_to_ass",
    "color.alpha",
    "color.interpolate",
    "color.hsv_to_rgb",
    "color.hsl_to_rgb",
}

EXPECTED_COORD_FUNCTIONS = {
    "coord.circular_spread",
    "coord.random_spread",
    "coord.polar",
}

EXPECTED_SHAPE_FUNCTIONS = {
    "shape.rotate",
    "shape.center_at",
    "shape.displace",
    "shape.split_clip",
}

EXPECTED_RANDOM_FUNCTIONS = {
    "random.choice",
    "random.choice_no_repeat",
    "random.random",
    "random.randint",
}

EXPECTED_EXPRESSION_OBJECTS = {
    "line",
    "word",
    "syl",
    "char",
    "loop",
    "style",
    "metadata",
    "assets",
}

EXPECTED_LINE_PROPERTIES = {
    "layer",
    "actor",
    "raw_text",
    "text",
    "trimmed_text",
    "start",
    "end",
    "dur",
    "mid",
    "i",
    "left",
    "center",
    "right",
    "width",
    "top",
    "middle",
    "bottom",
    "height",
    "x",
    "y",
    "syls",
}

EXPECTED_WORD_PROPERTIES = {
    "text",
    "trimmed_text",
    "start",
    "end",
    "dur",
    "kdur",
    "mid",
    "n",
    "i",
    "left",
    "center",
    "right",
    "width",
    "top",
    "middle",
    "bottom",
    "height",
    "x",
    "y",
}

EXPECTED_SYL_PROPERTIES = {
    "text",
    "trimmed_text",
    "start",
    "end",
    "dur",
    "kdur",
    "mid",
    "n",
    "i",
    "left",
    "center",
    "right",
    "width",
    "top",
    "middle",
    "bottom",
    "height",
    "x",
    "y",
    "tag",
    "inline_fx",
}

EXPECTED_CHAR_PROPERTIES = {
    "text",
    "trimmed_text",
    "i",
    "n",
    "left",
    "center",
    "right",
    "width",
    "top",
    "middle",
    "bottom",
    "height",
    "x",
    "y",
}

EXPECTED_LINE_STYLE_PROPERTIES = {
    "name",
    "primary_color",
    "secondary_color",
    "outline_color",
    "shadow_color",
    "outline",
}

EXPECTED_METADATA_PROPERTIES = {
    "res_x",
    "res_y",
}

EXPECTED_LOOP_PROPERTIES = {
    "i",
    "n",
}


class TestDeclarations:
    def test_registry_contains_expected_declarations(self) -> None:
        assert DECLARATIONS == {
            "template": TEMPLATE_DECLARATION,
            "mixin": MIXIN_DECLARATION,
            "code": CODE_DECLARATION,
        }

    def test_template_scopes_match_contract(self) -> None:
        assert TEMPLATE_DECLARATION.allowed_scopes == frozenset(
            {Scope.LINE, Scope.WORD, Scope.SYL, Scope.CHAR}
        )

    def test_code_scopes_match_contract(self) -> None:
        assert CODE_DECLARATION.allowed_scopes == frozenset(
            {Scope.SETUP, Scope.LINE, Scope.WORD, Scope.SYL}
        )

    def test_mixin_scopes_match_contract(self) -> None:
        assert MIXIN_DECLARATION.allowed_scopes == frozenset(
            {Scope.LINE, Scope.WORD, Scope.SYL, Scope.CHAR}
        )


class TestScopes:
    def test_all_shared_scopes_are_documented(self) -> None:
        assert set(SCOPE_SPECIFICATIONS) == set(Scope)

    def test_variable_groups_are_known(self) -> None:
        known_groups = {spec.group for spec in VARIABLE_SPECIFICATIONS.values()}

        for scope_specification in SCOPE_SPECIFICATIONS.values():
            assert scope_specification.variable_groups <= known_groups


class TestModifiers:
    def test_modifier_specs_use_canonical_keys(self) -> None:
        for key, spec in MODIFIER_SPECIFICATIONS.items():
            assert key == spec.keyword

    def test_modifier_aliases_are_unique(self) -> None:
        alias_pool: set[str] = set()
        for specification in MODIFIER_SPECIFICATIONS.values():
            for alias in specification.aliases:
                assert alias not in alias_pool
                assert alias not in MODIFIER_SPECIFICATIONS
                alias_pool.add(alias)

    def test_every_declared_template_modifier_is_documented(self) -> None:
        documented_keywords = set(MODIFIER_SPECIFICATIONS)
        documented_aliases = {
            alias
            for specification in MODIFIER_SPECIFICATIONS.values()
            for alias in specification.aliases
        }
        documented_tokens = documented_keywords | documented_aliases

        assert TEMPLATE_DECLARATION.allowed_modifiers <= documented_tokens
        assert CODE_DECLARATION.allowed_modifiers <= documented_tokens

    def test_modifier_scopes_are_valid_for_each_declaration(self) -> None:
        for specification in MODIFIER_SPECIFICATIONS.values():
            allowed_scopes = frozenset(
                scope
                for declaration_name in specification.applicable_to
                for scope in DECLARATIONS[declaration_name].allowed_scopes
            )
            assert specification.allowed_scopes <= allowed_scopes

    def test_modifier_scopes_overlap_each_applicable_declaration(self) -> None:
        for specification in MODIFIER_SPECIFICATIONS.values():
            for declaration_name in specification.applicable_to:
                declaration = DECLARATIONS[declaration_name]
                assert specification.allowed_scopes & declaration.allowed_scopes


class TestVariables:
    def test_variable_specs_use_matching_keys(self) -> None:
        for key, spec in VARIABLE_SPECIFICATIONS.items():
            assert key == spec.name

    def test_expected_variables_are_documented(self) -> None:
        documented = set(VARIABLE_SPECIFICATIONS)
        assert EXPECTED_TEMPLATE_VARIABLES <= documented
        assert EXPECTED_LINE_VARIABLES <= documented
        assert EXPECTED_WORD_VARIABLES <= documented
        assert EXPECTED_SYL_VARIABLES <= documented
        assert EXPECTED_CHAR_VARIABLES <= documented

    def test_each_scope_group_exposes_at_least_one_variable(self) -> None:
        counts_by_group: dict[str, int] = {}
        for specification in VARIABLE_SPECIFICATIONS.values():
            counts_by_group[specification.group] = (
                counts_by_group.get(specification.group, 0) + 1
            )

        for scope_specification in SCOPE_SPECIFICATIONS.values():
            for group_name in scope_specification.variable_groups:
                assert counts_by_group[group_name] > 0


class TestFunctions:
    def test_function_specs_use_matching_keys(self) -> None:
        for key, spec in FUNCTION_SPECIFICATIONS.items():
            assert key == spec.name

    def test_functions_reference_known_declarations(self) -> None:
        for specification in FUNCTION_SPECIFICATIONS.values():
            assert specification.applicable_to <= set(DECLARATIONS)

    def test_dotted_functions_reference_exposed_modules(self) -> None:
        for function_name in FUNCTION_SPECIFICATIONS:
            if "." not in function_name:
                continue
            module_name, _member_name = function_name.split(".", 1)
            assert module_name in EXPOSED_MODULES

    def test_exposed_math_contract_is_documented(self) -> None:
        assert EXPECTED_MATH_FUNCTIONS <= set(FUNCTION_SPECIFICATIONS)

    def test_exposed_color_contract_is_documented(self) -> None:
        assert EXPECTED_COLOR_FUNCTIONS <= set(FUNCTION_SPECIFICATIONS)

    def test_exposed_coord_contract_is_documented(self) -> None:
        assert EXPECTED_COORD_FUNCTIONS <= set(FUNCTION_SPECIFICATIONS)

    def test_exposed_shape_contract_is_documented(self) -> None:
        assert EXPECTED_SHAPE_FUNCTIONS <= set(FUNCTION_SPECIFICATIONS)

    def test_exposed_random_contract_is_documented(self) -> None:
        assert EXPECTED_RANDOM_FUNCTIONS <= set(FUNCTION_SPECIFICATIONS)

    def test_retime_contract_is_namespaced_template_only(self) -> None:
        retime = FUNCTION_SPECIFICATIONS["retime"]

        assert retime.signature.startswith("retime.<target>")
        assert retime.applicable_to == frozenset({"template"})

    def test_exposed_modules_are_unique(self) -> None:
        assert EXPOSED_MODULES == frozenset(
            {"color", "coord", "layer", "math", "random", "shape"}
        )


class TestExpressionObjects:
    def test_expression_objects_are_documented(self) -> None:
        assert EXPECTED_EXPRESSION_OBJECTS <= set(
            EXPRESSION_OBJECT_SPECIFICATIONS
        )

    def test_expression_object_specs_use_matching_keys(self) -> None:
        for key, spec in EXPRESSION_OBJECT_SPECIFICATIONS.items():
            assert key == spec.name

    def test_expression_object_scopes_are_real_scopes(self) -> None:
        for specification in EXPRESSION_OBJECT_SPECIFICATIONS.values():
            assert specification.available_scopes <= set(Scope)


class TestExpressionProperties:
    def test_expected_properties_are_documented(self) -> None:
        line_properties = {
            property_name
            for object_name, property_name in EXPRESSION_PROPERTY_SPECIFICATIONS
            if object_name == "line"
        }
        syl_properties = {
            property_name
            for object_name, property_name in EXPRESSION_PROPERTY_SPECIFICATIONS
            if object_name == "syl"
        }
        word_properties = {
            property_name
            for object_name, property_name in EXPRESSION_PROPERTY_SPECIFICATIONS
            if object_name == "word"
        }
        char_properties = {
            property_name
            for object_name, property_name in EXPRESSION_PROPERTY_SPECIFICATIONS
            if object_name == "char"
        }
        style_properties = {
            property_name
            for object_name, property_name in EXPRESSION_PROPERTY_SPECIFICATIONS
            if object_name == "style"
        }
        metadata_properties = {
            property_name
            for object_name, property_name in EXPRESSION_PROPERTY_SPECIFICATIONS
            if object_name == "metadata"
        }
        loop_properties = {
            property_name
            for object_name, property_name in EXPRESSION_PROPERTY_SPECIFICATIONS
            if object_name == "loop"
        }
        assert EXPECTED_LINE_PROPERTIES <= line_properties
        assert EXPECTED_WORD_PROPERTIES <= word_properties
        assert EXPECTED_SYL_PROPERTIES <= syl_properties
        assert EXPECTED_CHAR_PROPERTIES <= char_properties
        assert EXPECTED_LINE_STYLE_PROPERTIES <= style_properties
        assert EXPECTED_METADATA_PROPERTIES <= metadata_properties
        assert EXPECTED_LOOP_PROPERTIES <= loop_properties

    def test_property_scopes_are_subsets_of_object_scopes(self) -> None:
        for (
            object_name,
            _property_name,
        ), specification in EXPRESSION_PROPERTY_SPECIFICATIONS.items():
            object_specification = EXPRESSION_OBJECT_SPECIFICATIONS[object_name]
            assert (
                specification.available_scopes
                <= object_specification.available_scopes
            )

    def test_mapped_properties_reference_known_variables(self) -> None:
        for specification in EXPRESSION_PROPERTY_SPECIFICATIONS.values():
            if specification.source_variable is None:
                continue
            assert specification.source_variable in VARIABLE_SPECIFICATIONS
