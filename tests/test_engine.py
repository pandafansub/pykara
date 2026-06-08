"""Unit and integration tests for engine execution."""

# pyright: reportPrivateUsage=false

from __future__ import annotations

import builtins
import random
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import CodeType
from typing import cast

import pytest

from pykara.data import Event, Metadata, Style
from pykara.data.events.karaoke import Syllable, Word
from pykara.declaration import Scope
from pykara.declaration.code import CodeBody, CodeModifiers
from pykara.declaration.mixin import MixinBody, MixinModifiers
from pykara.declaration.template import (
    LoopDescriptor,
    TemplateBody,
    TemplateModifiers,
)
from pykara.engine.engine import Engine, _CodeRunner
from pykara.engine.variable_context import Environment, GeneratedLine
from pykara.errors import (
    BoundMethodInExpressionError,
    IncludeCollisionError,
    InvalidIncludeError,
    ReservedNameError,
    TemplateCodeError,
    TemplateRuntimeError,
    UnknownStyleReferenceError,
    UnknownVariableError,
)
from pykara.parsing import (
    CodeDeclaration,
    MixinDeclaration,
    ParsedDeclarations,
    TemplateDeclaration,
)
from pykara.processing.font_metrics import TextMeasurement
from pykara.processing.line_preprocessor import LinePreprocessor
from pykara.specification.expressions import EXPRESSION_PROPERTY_SPECIFICATIONS


def template_declarations_for_scope(
    scope: Scope,
    declaration: TemplateDeclaration,
) -> ParsedDeclarations:
    if scope is Scope.LINE:
        return ParsedDeclarations(line=[declaration])
    if scope is Scope.WORD:
        return ParsedDeclarations(word=[declaration])
    if scope is Scope.SYL:
        return ParsedDeclarations(syl=[declaration])
    if scope is Scope.CHAR:
        return ParsedDeclarations(char=[declaration])
    raise AssertionError(f"unexpected template scope: {scope}")


@dataclass(slots=True)
class FakeExtentsProvider:
    widths: dict[str, float]

    def measure(self, style: Style, text: str) -> TextMeasurement:
        del style
        return TextMeasurement(
            width=self.widths.get(text, float(len(text) * 10)),
            height=20.0,
            descent=4.0,
            extlead=0.0,
        )


@dataclass(slots=True)
class CountingExtentsProvider:
    widths: dict[str, float]
    calls: int = 0

    def measure(self, style: Style, text: str) -> TextMeasurement:
        del style
        self.calls += 1
        return TextMeasurement(
            width=self.widths.get(text, float(len(text) * 10)),
            height=20.0,
            descent=4.0,
            extlead=0.0,
        )


@dataclass(slots=True)
class StyleAwareExtentsProvider:
    widths: dict[tuple[str, str], float]

    def measure(self, style: Style, text: str) -> TextMeasurement:
        return TextMeasurement(
            width=self.widths.get((style.name, text), float(len(text) * 10)),
            height=20.0,
            descent=4.0,
            extlead=0.0,
        )


def make_style(name: str = "Default") -> Style:
    return Style(
        name=name,
        fontname="Arial",
        fontsize=40.0,
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
    style: str = "Default",
    text: str = r"{\k20}go{\k30}al",
) -> Event:
    return Event(
        text=text,
        effect="karaoke",
        style=style,
        layer=0,
        start_time=1000,
        end_time=1500,
        comment=False,
        actor="Singer",
        margin_l=0,
        margin_r=0,
        margin_t=0,
        margin_b=0,
    )


def make_single_syllable_event() -> Event:
    return Event(
        text=r"{\k50}go",
        effect="karaoke",
        style="Default",
        layer=0,
        start_time=1000,
        end_time=1500,
        comment=False,
        actor="Singer",
        margin_l=0,
        margin_r=0,
        margin_t=0,
        margin_b=0,
    )


def make_positioned_syllable(
    text: str = "go",
    *,
    index: int = 0,
    style: Style | None = None,
    left: float = 100.0,
    width: float | None = None,
    x: float | None = None,
    tag: str = "",
    inline_fx: str = "",
) -> Syllable:
    resolved_width = float(len(text) * 10) if width is None else width
    trimmed = text.strip()
    prespace = text[: len(text) - len(text.lstrip(" \t"))]
    postspace = text[len(text.rstrip(" \t")) :]
    right = left + resolved_width
    center = left + resolved_width / 2
    return Syllable(
        index=index,
        raw_text=text,
        text=text,
        trimmed_text=trimmed,
        prespace=prespace,
        postspace=postspace,
        start_time=0,
        end_time=100,
        duration=100,
        kdur=10.0,
        tag=tag,
        inline_fx=inline_fx,
        highlights=[],
        style=style,
        width=resolved_width,
        height=20.0,
        prespacewidth=float(len(prespace) * 10),
        postspacewidth=float(len(postspace) * 10),
        left=left,
        center=center,
        right=right,
        top=0.0,
        middle=10.0,
        bottom=20.0,
        x=center if x is None else x,
        y=10.0,
    )


def make_leading_blank_syllable_event() -> Event:
    return Event(
        text=r"{\k23}{\k22}ka",
        effect="karaoke",
        style="Default",
        layer=0,
        start_time=1000,
        end_time=1450,
        comment=False,
        actor="Singer",
        margin_l=0,
        margin_r=0,
        margin_t=0,
        margin_b=0,
    )


def make_env() -> Environment:
    return Environment(
        styles={"Default": make_style()},
        declaration="code",
        rng=random.Random(1),  # noqa: S311
    )


def make_setup_env() -> Environment:
    env = make_env()
    env.active_code_scope = Scope.SETUP
    return env


class TestCodeRunnerCaching:
    def test_caches_compiled_code(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        runner = _CodeRunner()
        compile_calls = 0
        original_compile = builtins.compile

        def counting_compile(
            source: str,
            filename: str,
            mode: str,
            flags: int = 0,
            dont_inherit: bool = False,
            optimize: int = -1,
            _feature_version: int = -1,
        ) -> CodeType:
            nonlocal compile_calls
            if mode == "exec" and not flags:
                compile_calls += 1
            return original_compile(
                source,
                filename,
                mode,
                flags=flags,
                dont_inherit=dont_inherit,
                optimize=optimize,
                _feature_version=_feature_version,
            )

        monkeypatch.setattr(builtins, "compile", counting_compile)

        env = make_env()
        runner.run("value = 1", env)
        runner.run("value = 1", env)

        assert env.user_namespace["value"] == 1
        assert compile_calls == 1

    def test_caches_expanded_char_syllables_per_environment(self) -> None:
        extents = CountingExtentsProvider({"g": 10.0, "o": 10.0})
        preprocessor = LinePreprocessor(extents)
        engine = Engine(preprocessor, seed=1)
        env = Environment(
            styles={"Default": make_style()},
            declaration="template",
        )
        syllable = preprocessor.preprocess(
            make_single_syllable_event(),
            engine._karaoke_parser.parse(make_single_syllable_event()),
            Metadata(res_x=1920, res_y=1080),
            make_style(),
        ).syllables[0]
        calls_before = extents.calls

        first = engine._iter_char_syllables(env, syllable)
        second = engine._iter_char_syllables(env, syllable)

        assert first == second
        assert extents.calls - calls_before == 2


def build_engine() -> Engine:
    extents = FakeExtentsProvider(
        {
            "goal": 40.0,
            "": 0.0,
            "go": 20.0,
            "al": 20.0,
            "g": 10.0,
            "o": 10.0,
            "a": 10.0,
            "l": 10.0,
        }
    )
    return Engine(LinePreprocessor(extents), seed=1)


class TestCodeRunner:
    def test_executes_valid_code_and_persists_namespace(self) -> None:
        runner = _CodeRunner()
        env = make_env()

        runner.run("helper = 7", env)

        assert env.user_namespace["helper"] == 7

    def test_allows_reassigning_existing_user_namespace_values(self) -> None:
        runner = _CodeRunner()
        env = make_env()

        runner.run("value = 1", env)
        runner.run("value = value + 1", env)

        assert env.user_namespace["value"] == 2

    def test_reseeds_random_when_dunderseed_is_assigned(self) -> None:
        runner = _CodeRunner()
        env = make_env()

        runner.run("__seed__ = 7", env)

        assert env.rng.randint(1, 100) == 42

    def test_plain_name_does_not_reseed_random(self) -> None:
        runner = _CodeRunner()
        env = make_env()

        runner.run("seed = 7", env)

        assert env.user_namespace["seed"] == 7
        assert env.rng.randint(1, 100) == 18

    def test_legacy_single_underscore_name_does_not_reseed_random(
        self,
    ) -> None:
        runner = _CodeRunner()
        env = make_env()
        legacy_name = "_" + "seed"

        runner.run(f"{legacy_name} = 7", env)

        assert env.user_namespace[legacy_name] == 7
        assert env.rng.randint(1, 100) == 18

    def test_does_not_reapply_dunderseed_when_other_code_runs(self) -> None:
        runner = _CodeRunner()
        env = make_env()

        runner.run("__seed__ = 7", env)
        assert env.rng.randint(1, 100) == 42
        runner.run("value = 1", env)

        assert env.rng.randint(1, 100) == 20

    def test_raises_template_code_error_on_syntax_failure(self) -> None:
        runner = _CodeRunner()

        with pytest.raises(TemplateCodeError):
            runner.run("def broken(: pass", make_env())

    def test_raises_template_code_error_when_compile_rejects_ast(
        self,
    ) -> None:
        runner = _CodeRunner()

        with pytest.raises(TemplateCodeError):
            runner.run("return 1", make_env())

    def test_raises_template_runtime_error_on_execution_failure(self) -> None:
        runner = _CodeRunner()

        with pytest.raises(TemplateRuntimeError):
            runner.run("1 / 0", make_env())

    def test_reraises_bound_method_expression_errors(self) -> None:
        runner = _CodeRunner()
        env = make_env()
        env.user_namespace["BoundMethodInExpressionError"] = (
            BoundMethodInExpressionError
        )

        with pytest.raises(BoundMethodInExpressionError):
            runner.run(
                "raise BoundMethodInExpressionError('retime.syl', 'function')",
                env,
            )

    def test_rejects_assignment_to_reserved_name(self) -> None:
        runner = _CodeRunner()

        with pytest.raises(ReservedNameError, match="reserved name 'color'"):
            runner.run("color = assets.colors.purple[800]", make_env())

    def test_rejects_assignment_to_safe_builtin_name(self) -> None:
        runner = _CodeRunner()

        with pytest.raises(ReservedNameError, match="reserved name 'range'"):
            runner.run("range = 3", make_env())

    def test_allows_assignment_to_template_store_function_names_in_code(
        self,
    ) -> None:
        runner = _CodeRunner()
        env = make_env()

        runner.run("get = 1\nput = 2\nlock = 3", env)

        assert env.user_namespace["get"] == 1
        assert env.user_namespace["put"] == 2
        assert env.user_namespace["lock"] == 3

    def test_exposes_safe_builtins_in_code(self) -> None:
        runner = _CodeRunner()
        env = make_env()

        runner.run(
            "values = list(range(4))\n"
            "pairs = list(zip(values, reversed(values)))\n"
            "unique = set([1, 1, 2])\n"
            "total = sum(values) + len(pairs) + len(unique)",
            env,
        )

        assert env.user_namespace["values"] == [0, 1, 2, 3]
        assert env.user_namespace["pairs"] == [
            (0, 3),
            (1, 2),
            (2, 1),
            (3, 0),
        ]
        assert env.user_namespace["unique"] == {1, 2}
        assert env.user_namespace["total"] == 12

    def test_collects_assigned_names_from_complex_python_bindings(
        self,
    ) -> None:
        runner = _CodeRunner()

        names = runner._assigned_names(
            "decorator = lambda value: value\n"
            "class Base: pass\n"
            "@decorator\n"
            "class Built(Base, metaclass=type): pass\n"
            "@decorator\n"
            "async def coro() -> int:\n"
            "    return 1\n"
            "try:\n"
            "    raise ValueError()\n"
            "except ValueError as caught:\n"
            "    handled = caught\n"
            "values = [item for item in range(3) if item]\n"
            "unique = {item for item in range(3) if item}\n"
            "mapping = {key: value for key, value in [(1, 2)] if key}\n"
            "import os as operating_system\n"
        )

        assert {
            "decorator",
            "Base",
            "Built",
            "coro",
            "caught",
            "handled",
            "values",
            "unique",
            "mapping",
            "operating_system",
        } <= names

    def test_include_executes_python_file(
        self,
        tmp_path: Path,
    ) -> None:
        include_path = tmp_path / "common.py"
        include_path.write_text(
            "accent = '&H00FFFFFF'\n"
            "def label(value):\n"
            "    return f'[{value}]'\n",
            encoding="utf-8",
        )
        runner = _CodeRunner()
        env = make_setup_env()

        runner.run('include "common.py"', env, base_dir=tmp_path)

        assert env.user_namespace["accent"] == "&H00FFFFFF"
        label = cast(Callable[[str], str], env.user_namespace["label"])
        assert label("go") == "[go]"

    def test_include_accepts_multiple_string_literal_paths(
        self,
        tmp_path: Path,
    ) -> None:
        (tmp_path / "base.py").write_text("base = 1\n", encoding="utf-8")
        (tmp_path / "colors.py").write_text(
            "color_name = 'red'\n",
            encoding="utf-8",
        )
        runner = _CodeRunner()
        env = make_setup_env()

        runner.run(
            'include "base.py", r"colors.py"',
            env,
            base_dir=tmp_path,
        )

        assert env.user_namespace["base"] == 1
        assert env.user_namespace["color_name"] == "red"

    def test_include_rejects_reserved_names(self, tmp_path: Path) -> None:
        include_path = tmp_path / "bad.py"
        include_path.write_text("color = 'bad'\n", encoding="utf-8")
        runner = _CodeRunner()

        with pytest.raises(ReservedNameError, match="reserved name 'color'"):
            runner.run('include "bad.py"', make_setup_env(), base_dir=tmp_path)

    def test_include_rejects_ass_code_collision(
        self,
        tmp_path: Path,
    ) -> None:
        include_path = tmp_path / "common.py"
        include_path.write_text("accent = 'red'\n", encoding="utf-8")
        runner = _CodeRunner()
        env = make_setup_env()

        runner.run('include "common.py"', env, base_dir=tmp_path)

        with pytest.raises(IncludeCollisionError, match="accent"):
            runner.run("accent = 'blue'", env)

    def test_include_rejects_collision_with_existing_ass_code(
        self,
        tmp_path: Path,
    ) -> None:
        include_path = tmp_path / "common.py"
        include_path.write_text("accent = 'red'\n", encoding="utf-8")
        runner = _CodeRunner()
        env = make_setup_env()
        runner.run("accent = 'blue'", env)

        with pytest.raises(IncludeCollisionError, match="accent"):
            runner.run('include "common.py"', env, base_dir=tmp_path)

    def test_include_rejects_duplicate_include_names(
        self,
        tmp_path: Path,
    ) -> None:
        (tmp_path / "one.py").write_text("accent = 'red'\n", encoding="utf-8")
        (tmp_path / "two.py").write_text("accent = 'blue'\n", encoding="utf-8")
        runner = _CodeRunner()

        with pytest.raises(IncludeCollisionError, match="accent"):
            runner.run(
                'include "one.py", "two.py"',
                make_setup_env(),
                base_dir=tmp_path,
            )

    def test_include_rejects_non_setup_scope(self, tmp_path: Path) -> None:
        (tmp_path / "common.py").write_text(
            "accent = 'red'\n",
            encoding="utf-8",
        )
        runner = _CodeRunner()
        env = make_env()
        env.active_code_scope = Scope.SYL

        with pytest.raises(InvalidIncludeError, match="code setup"):
            runner.run('include "common.py"', env, base_dir=tmp_path)


class TestEngineInternalBranches:
    def test_loop_expression_errors_are_wrapped(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            line=[
                TemplateDeclaration(
                    body=TemplateBody("loop"),
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(
                        no_text=True,
                        loops=(
                            LoopDescriptor(
                                name="i",
                                iterations="missing_name",
                            ),
                        ),
                    ),
                )
            ]
        )

        with pytest.raises(TemplateRuntimeError):
            engine.apply(
                [make_single_syllable_event()],
                declarations,
                Metadata(res_x=1920, res_y=1080),
                {"Default": make_style()},
            )

    def test_loop_expression_unexpected_errors_are_wrapped(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        engine = build_engine()

        class BrokenRenderer:
            def render(self, text: str, env: Environment) -> str:
                del text, env
                raise ValueError("broken renderer")

        monkeypatch.setattr(engine, "_renderer", BrokenRenderer())

        with pytest.raises(TemplateRuntimeError):
            engine._resolve_loop_iterations("broken", make_env())

    def test_loop_expression_must_resolve_positive(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            line=[
                TemplateDeclaration(
                    body=TemplateBody("loop"),
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(
                        no_text=True,
                        loops=(
                            LoopDescriptor(
                                name="i",
                                iterations="0",
                            ),
                        ),
                    ),
                )
            ]
        )

        with pytest.raises(TemplateRuntimeError):
            engine.apply(
                [make_single_syllable_event()],
                declarations,
                Metadata(res_x=1920, res_y=1080),
                {"Default": make_style()},
            )

    def test_current_reference_style_defaults_to_event_style(self) -> None:
        engine = build_engine()
        env = make_env()

        assert (
            engine._current_reference_style_name(make_event(), env) == "Default"
        )

    def test_styles_modifier_rejects_non_string_tuple_items(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            setup=[
                CodeDeclaration(
                    body=CodeBody('my_styles = ("Default", 123)'),
                    scope=Scope.SETUP,
                )
            ],
            line=[
                TemplateDeclaration(
                    body=TemplateBody("body"),
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(styles="my_styles"),
                )
            ],
        )

        with pytest.raises(TemplateRuntimeError):
            engine.apply(
                [make_event()],
                declarations,
                Metadata(res_x=1920, res_y=1080),
                {"Default": make_style()},
            )

    def test_char_syllables_are_empty_without_style(self) -> None:
        engine = build_engine()
        env = make_env()

        assert (
            engine._iter_char_syllables(
                env,
                make_positioned_syllable("go", style=None),
            )
            == ()
        )

    def test_empty_syllable_collection_has_no_words(self) -> None:
        assert build_engine()._iter_words(()) == []

    def test_word_template_no_blank_skips_blank_word(self) -> None:
        engine = build_engine()
        blank_syllable = make_positioned_syllable("  ", style=make_style())
        blank_word = Word(
            index=0,
            syllables=(blank_syllable,),
            raw_text="  ",
            text="  ",
            trimmed_text="",
            prespace="",
            postspace="  ",
            start_time=0,
            end_time=100,
            duration=100,
            kdur=10.0,
        )

        assert (
            engine._render_word_template(
                TemplateDeclaration(
                    body=TemplateBody("blank"),
                    scope=Scope.WORD,
                    modifiers=TemplateModifiers(no_blank=True),
                ),
                make_event(),
                ParsedDeclarations(),
                blank_word,
                make_env(),
            )
            == []
        )

    def test_unsplittable_untimed_syllable_is_preserved(self) -> None:
        engine = build_engine()
        syllable = make_positioned_syllable("solo", style=make_style())

        assert list(engine._split_untimed_word_syllable(syllable)) == [syllable]

    def test_syllable_x_scale_falls_back_to_one(self) -> None:
        engine = build_engine()
        zero_width_engine = Engine(
            LinePreprocessor(FakeExtentsProvider({"zero": 0.0})),
            seed=1,
        )

        assert (
            engine._resolve_syllable_x_scale(
                make_positioned_syllable("", style=make_style())
            )
            == 1.0
        )
        assert (
            engine._resolve_syllable_x_scale(
                make_positioned_syllable("zero", style=None)
            )
            == 1.0
        )
        assert (
            zero_width_engine._resolve_syllable_x_scale(
                make_positioned_syllable("zero", style=make_style(), width=10.0)
            )
            == 1.0
        )

    def test_segment_anchor_keeps_source_alignment_edge(self) -> None:
        engine = build_engine()
        left_aligned = make_positioned_syllable(left=10.0, width=40.0, x=10.0)
        right_aligned = make_positioned_syllable(left=10.0, width=40.0, x=50.0)

        assert (
            engine._resolve_segment_anchor_x(left_aligned, 1.0, 2.0, 3.0) == 1.0
        )
        assert (
            engine._resolve_segment_anchor_x(right_aligned, 1.0, 2.0, 3.0)
            == 3.0
        )

    def test_mixin_filter_false_paths(self) -> None:
        engine = build_engine()
        env = make_env()
        env.line = GeneratedLine.from_event(make_event(), make_style())
        env.line.layer = 1
        env.syl = make_positioned_syllable(
            "go",
            style=make_style(),
            inline_fx="main",
        )
        template = TemplateDeclaration(
            body=TemplateBody("T"),
            scope=Scope.SYL,
            actor="lead",
            modifiers=TemplateModifiers(),
        )
        source_event = make_event()

        assert not engine._mixin_applies_to_template(
            mixin=MixinDeclaration(
                body=MixinBody("M"),
                scope=Scope.LINE,
                modifiers=MixinModifiers(),
            ),
            template=template,
            source_event=source_event,
            env=env,
        )
        assert not engine._mixin_applies_to_template(
            mixin=MixinDeclaration(
                body=MixinBody("M"),
                scope=Scope.SYL,
                style="Other",
                modifiers=MixinModifiers(),
            ),
            template=template,
            source_event=source_event,
            env=env,
        )
        assert not engine._mixin_applies_to_template(
            mixin=MixinDeclaration(
                body=MixinBody("M"),
                scope=Scope.SYL,
                modifiers=MixinModifiers(fx="alt"),
            ),
            template=template,
            source_event=source_event,
            env=env,
        )
        assert not engine._mixin_applies_to_template(
            mixin=MixinDeclaration(
                body=MixinBody("M"),
                scope=Scope.SYL,
                modifiers=MixinModifiers(when="False"),
            ),
            template=template,
            source_event=source_event,
            env=env,
        )

    def test_mixin_style_filter_uses_source_style_for_styles_templates(
        self,
    ) -> None:
        engine = build_engine()
        source_event = make_event()
        template = TemplateDeclaration(
            body=TemplateBody("T"),
            scope=Scope.SYL,
            modifiers=TemplateModifiers(styles="my_styles"),
        )

        assert engine._mixin_applies_to_style(
            mixin=MixinDeclaration(
                body=MixinBody("M"),
                scope=Scope.SYL,
                style="Default",
                modifiers=MixinModifiers(),
            ),
            template=template,
            source_event=source_event,
        )

    def test_mixin_conditions_can_fail_for_when_and_unless(self) -> None:
        engine = build_engine()
        env = make_env()

        assert not engine._passes_mixin_conditions(
            MixinDeclaration(
                body=MixinBody("M"),
                scope=Scope.LINE,
                modifiers=MixinModifiers(when="False"),
            ),
            env,
        )
        assert not engine._passes_mixin_conditions(
            MixinDeclaration(
                body=MixinBody("M"),
                scope=Scope.LINE,
                modifiers=MixinModifiers(unless="True"),
            ),
            env,
        )


class TestEngineIntegration:
    def test_dollar_variables_match_object_property_aliases(self) -> None:
        engine = build_engine()
        metadata = Metadata(res_x=1920, res_y=1080)
        styles = {"Default": make_style()}
        line_scopes = frozenset({Scope.LINE, Scope.WORD, Scope.SYL, Scope.CHAR})
        syl_scopes = frozenset({Scope.SYL, Scope.CHAR})
        scenarios = [
            ("baseline", line_scopes, ""),
            ("layer.set", line_scopes, "!layer.set(7)!"),
            ("retime.line", line_scopes, "!retime.line(-150,-50)!"),
            ("retime.preline", line_scopes, "!retime.preline(-150,-50)!"),
            ("retime.postline", line_scopes, "!retime.postline(-150,-50)!"),
            (
                "layer.set+retime.line",
                line_scopes,
                "!layer.set(7)!!retime.line(-150,-50)!",
            ),
            ("retime.syl", syl_scopes, "!retime.syl(-150,-50)!"),
            ("retime.presyl", syl_scopes, "!retime.presyl(-150,-50)!"),
            ("retime.postsyl", syl_scopes, "!retime.postsyl(-150,-50)!"),
            (
                "retime.start2syl",
                syl_scopes,
                "!retime.start2syl(-150,-50)!",
            ),
            ("retime.syl2end", syl_scopes, "!retime.syl2end(-150,-50)!"),
        ]
        separator = "<<<ALIAS>>>"

        for scenario_name, scenario_scopes, prefix in scenarios:
            for scope in scenario_scopes:
                for (
                    object_name,
                    property_name,
                ), spec in EXPRESSION_PROPERTY_SPECIFICATIONS.items():
                    if (
                        spec.source_variable is None
                        or scope not in spec.available_scopes
                    ):
                        continue
                    expression = f"{object_name}.{property_name}"
                    variable = spec.source_variable
                    declaration = TemplateDeclaration(
                        body=TemplateBody(
                            f"{prefix}!{expression}!{separator}${variable}"
                        ),
                        scope=scope,
                        modifiers=TemplateModifiers(no_text=True),
                    )
                    declarations = template_declarations_for_scope(
                        scope,
                        declaration,
                    )

                    results = engine.apply(
                        [make_event()],
                        declarations,
                        metadata,
                        styles,
                    )

                    for result in results:
                        expression_value, variable_value = result.text.split(
                            separator,
                            1,
                        )
                        assert expression_value == variable_value, (
                            f"{scenario_name}/{scope.value}: "
                            f"{expression}={expression_value!r} "
                            f"!= ${variable}={variable_value!r}"
                        )

    def test_template_variables_include_values_defined_by_code(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            line=[
                CodeDeclaration(
                    body=CodeBody("label = f'{line.i}:{line.text}'"),
                    scope=Scope.LINE,
                ),
                TemplateDeclaration(
                    body=TemplateBody("$label"),
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(no_text=True),
                ),
            ]
        )

        results = engine.apply(
            [make_event()],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == ["0:goal"]

    def test_cli_option_runs_before_code_dunderseed(self) -> None:
        engine = Engine(
            LinePreprocessor(FakeExtentsProvider({"goal": 40.0})),
            seed=42,
        )
        declarations = ParsedDeclarations(
            setup=[
                CodeDeclaration(
                    body=CodeBody(
                        "first = random.randint(1, 100); __seed__ = 7"
                    ),
                    scope=Scope.SETUP,
                )
            ],
            line=[
                TemplateDeclaration(
                    body=TemplateBody("$first:!random.randint(1, 100)!"),
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(no_text=True),
                )
            ],
        )

        results = engine.apply(
            [make_event()],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == ["82:42"]

    def test_scoped_code_can_reseed_random(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            line=[
                CodeDeclaration(
                    body=CodeBody("__seed__ = line.i + 5"),
                    scope=Scope.LINE,
                ),
                TemplateDeclaration(
                    body=TemplateBody("!random.randint(1, 100)!"),
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(no_text=True),
                ),
            ]
        )

        results = engine.apply(
            [make_event(), make_event()],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == ["80", "74"]

    def test_template_styles_modifier_uses_reference_style_metrics(
        self,
    ) -> None:
        engine = Engine(
            LinePreprocessor(
                StyleAwareExtentsProvider(
                    {
                        ("Default", "goal"): 40.0,
                        ("Alt", "goal"): 80.0,
                    }
                )
            ),
            seed=1,
        )
        event = make_event("Alt")
        declarations = ParsedDeclarations(
            setup=[
                CodeDeclaration(
                    body=CodeBody('my_styles = ("Alt",)'),
                    scope=Scope.SETUP,
                )
            ],
            line=[
                TemplateDeclaration(
                    body=TemplateBody("!style.name!:$line_width"),
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(
                        styles="my_styles",
                        no_text=True,
                    ),
                )
            ],
        )

        results = engine.apply(
            [event],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {
                "Default": make_style(),
                "Alt": make_style("Alt"),
            },
        )

        assert [(result.style, result.text) for result in results] == [
            ("Alt", "Alt:80")
        ]

    def test_styles_modifier_accepts_tuple_from_setup_code(self) -> None:
        engine = Engine(
            LinePreprocessor(
                StyleAwareExtentsProvider(
                    {
                        ("A", "goal"): 20.0,
                        ("B", "goal"): 60.0,
                    }
                )
            ),
            seed=1,
        )
        event = make_event("A")
        declarations = ParsedDeclarations(
            setup=[
                CodeDeclaration(
                    body=CodeBody('my_styles = ("A", "B")'),
                    scope=Scope.SETUP,
                )
            ],
            line=[
                TemplateDeclaration(
                    body=TemplateBody("!style.name!:$line_width"),
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(
                        styles="my_styles",
                        no_text=True,
                    ),
                )
            ],
        )

        results = engine.apply(
            [event],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {
                "Default": make_style(),
                "A": make_style("A"),
                "B": make_style("B"),
            },
        )

        assert [(result.style, result.text) for result in results] == [
            ("A", "A:20"),
        ]

    def test_styles_modifier_applies_only_to_events_with_listed_styles(
        self,
    ) -> None:
        engine = Engine(
            LinePreprocessor(
                StyleAwareExtentsProvider(
                    {
                        ("A", "goal"): 20.0,
                        ("B", "goal"): 60.0,
                        ("Default", "goal"): 100.0,
                    }
                )
            ),
            seed=1,
        )
        declarations = ParsedDeclarations(
            setup=[
                CodeDeclaration(
                    body=CodeBody('my_styles = ("A", "B")'),
                    scope=Scope.SETUP,
                )
            ],
            line=[
                CodeDeclaration(
                    body=CodeBody(
                        "if style.name not in my_styles:\n"
                        '    raise RuntimeError("unlisted style")'
                    ),
                    scope=Scope.LINE,
                    modifiers=CodeModifiers(styles="my_styles"),
                ),
                TemplateDeclaration(
                    body=TemplateBody("!style.name!:$line_width"),
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(
                        styles="my_styles",
                        no_text=True,
                    ),
                ),
            ],
        )

        results = engine.apply(
            [
                make_event("Default"),
                make_event("A"),
                make_event("B"),
                make_event("C"),
            ],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {
                "Default": make_style(),
                "A": make_style("A"),
                "B": make_style("B"),
                "C": make_style("C"),
            },
        )

        assert [(result.style, result.text) for result in results] == [
            ("A", "A:20"),
            ("B", "B:60"),
        ]

    def test_one_styles_template_uses_each_matching_line_values(
        self,
    ) -> None:
        engine = Engine(
            LinePreprocessor(
                StyleAwareExtentsProvider(
                    {
                        ("A", "red"): 30.0,
                        ("B", "blue"): 90.0,
                    }
                )
            ),
            seed=1,
        )
        declarations = ParsedDeclarations(
            setup=[
                CodeDeclaration(
                    body=CodeBody('my_styles = ("A", "B")'),
                    scope=Scope.SETUP,
                )
            ],
            line=[
                TemplateDeclaration(
                    body=TemplateBody("!style.name!:!line.text!:$line_width"),
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(
                        styles="my_styles",
                        no_text=True,
                    ),
                )
            ],
        )

        results = engine.apply(
            [
                make_event("A", text=r"{\k50}red"),
                make_event("B", text=r"{\k50}blue"),
            ],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {
                "A": make_style("A"),
                "B": make_style("B"),
            },
        )

        assert [(result.style, result.text) for result in results] == [
            ("A", "A:red:30"),
            ("B", "B:blue:90"),
        ]

    def test_styles_modifier_overrides_template_line_style_filter(
        self,
    ) -> None:
        engine = Engine(
            LinePreprocessor(
                StyleAwareExtentsProvider(
                    {
                        ("Romaji", "ro"): 30.0,
                        ("Kanji", "漢"): 50.0,
                    }
                )
            ),
            seed=1,
        )
        declarations = ParsedDeclarations(
            setup=[
                CodeDeclaration(
                    body=CodeBody('karaokeable = ("Romaji", "Kanji")'),
                    scope=Scope.SETUP,
                )
            ],
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("!style.name!:!syl.text!:$syl_width"),
                    scope=Scope.SYL,
                    style="Romaji",
                    actor="start",
                    modifiers=TemplateModifiers(
                        styles="karaokeable",
                        no_text=True,
                    ),
                )
            ],
            mixin_syl=[
                MixinDeclaration(
                    body=MixinBody("{mixed}"),
                    scope=Scope.SYL,
                    style="Romaji",
                    modifiers=MixinModifiers(for_actor="start"),
                )
            ],
        )

        results = engine.apply(
            [
                make_event("Romaji", text=r"{\k50}ro"),
                make_event("Kanji", text=r"{\k50}漢"),
            ],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {
                "Romaji": make_style("Romaji"),
                "Kanji": make_style("Kanji"),
            },
        )

        assert [(result.style, result.text) for result in results] == [
            ("Romaji", "Romaji:ro:30{mixed}"),
            ("Kanji", "Kanji:漢:50{mixed}"),
        ]

    def test_code_styles_modifier_uses_reference_style_context(self) -> None:
        engine = Engine(
            LinePreprocessor(
                StyleAwareExtentsProvider(
                    {
                        ("A", "goal"): 20.0,
                        ("B", "goal"): 60.0,
                    }
                )
            ),
            seed=1,
        )
        event = make_event("A")
        declarations = ParsedDeclarations(
            setup=[
                CodeDeclaration(
                    body=CodeBody('my_styles = ("A", "B")'),
                    scope=Scope.SETUP,
                )
            ],
            line=[
                CodeDeclaration(
                    body=CodeBody('current = f"{style.name}:{line.width}"'),
                    scope=Scope.LINE,
                    modifiers=CodeModifiers(styles="my_styles"),
                ),
                TemplateDeclaration(
                    body=TemplateBody("!current!"),
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(
                        styles="my_styles",
                        no_text=True,
                    ),
                ),
            ],
        )

        results = engine.apply(
            [event],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {
                "Default": make_style(),
                "A": make_style("A"),
                "B": make_style("B"),
            },
        )

        assert [result.text for result in results] == ["A:20"]

    def test_setup_code_styles_modifier_runs_for_each_reference_style(
        self,
    ) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            setup=[
                CodeDeclaration(
                    body=CodeBody('my_styles = ("A", "B")'),
                    scope=Scope.SETUP,
                ),
                CodeDeclaration(
                    body=CodeBody("seen = []"),
                    scope=Scope.SETUP,
                ),
                CodeDeclaration(
                    body=CodeBody("seen.append(style.name)"),
                    scope=Scope.SETUP,
                    modifiers=CodeModifiers(styles="my_styles"),
                ),
            ],
            line=[
                TemplateDeclaration(
                    body=TemplateBody("!','.join(seen)!"),
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(no_text=True),
                )
            ],
        )

        results = engine.apply(
            [make_event()],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {
                "Default": make_style(),
                "A": make_style("A"),
                "B": make_style("B"),
            },
        )

        assert [result.text for result in results] == ["A,B"]

    def test_setup_code_styles_modifier_restores_reference_style(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            setup=[
                CodeDeclaration(
                    body=CodeBody('my_styles = ("A", "B")'),
                    scope=Scope.SETUP,
                ),
                CodeDeclaration(
                    body=CodeBody("seen = []"),
                    scope=Scope.SETUP,
                ),
                CodeDeclaration(
                    body=CodeBody("seen.append(style.name)"),
                    scope=Scope.SETUP,
                    modifiers=CodeModifiers(styles="my_styles"),
                ),
                CodeDeclaration(
                    body=CodeBody("leaked = style.name"),
                    scope=Scope.SETUP,
                ),
            ],
        )

        with pytest.raises(TemplateRuntimeError):
            engine.apply(
                [make_event("A")],
                declarations,
                Metadata(res_x=1920, res_y=1080),
                {
                    "A": make_style("A"),
                    "B": make_style("B"),
                },
            )

    def test_code_line_can_define_styles_tuple_before_template_uses_it(
        self,
    ) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            line=[
                CodeDeclaration(
                    body=CodeBody('karaokeable = ("Romaji", "Kanji")'),
                    scope=Scope.LINE,
                    style="Romaji",
                ),
                TemplateDeclaration(
                    body=TemplateBody("!style.name!:!line.text!"),
                    scope=Scope.LINE,
                    style="Romaji",
                    modifiers=TemplateModifiers(
                        styles="karaokeable",
                        no_text=True,
                    ),
                ),
            ],
        )

        results = engine.apply(
            [
                make_event("Romaji", text=r"{\k50}ro"),
                make_event("Kanji", text=r"{\k50}漢"),
            ],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {
                "Romaji": make_style("Romaji"),
                "Kanji": make_style("Kanji"),
            },
        )

        assert [(result.style, result.text) for result in results] == [
            ("Romaji", "Romaji:ro"),
            ("Kanji", "Kanji:漢"),
        ]

    def test_code_line_all_can_define_styles_tuple_for_first_matching_event(
        self,
    ) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            line=[
                CodeDeclaration(
                    body=CodeBody('karaokeable = ("Romaji", "Kanji")'),
                    scope=Scope.LINE,
                ),
                TemplateDeclaration(
                    body=TemplateBody("!style.name!:!line.text!"),
                    scope=Scope.LINE,
                    style="Romaji",
                    modifiers=TemplateModifiers(
                        styles="karaokeable",
                        no_text=True,
                    ),
                ),
            ],
        )

        results = engine.apply(
            [make_event("Kanji", text=r"{\k50}漢")],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {
                "Romaji": make_style("Romaji"),
                "Kanji": make_style("Kanji"),
            },
        )

        assert [(result.style, result.text) for result in results] == [
            ("Kanji", "Kanji:漢"),
        ]

    def test_skips_declarations_with_mismatched_style_reference_and_condition(
        self,
    ) -> None:
        engine = build_engine()
        event = Event(
            text=r"{\k10}  {\k20}go",
            effect="karaoke",
            style="Default",
            layer=0,
            start_time=1000,
            end_time=1300,
            comment=False,
            actor="Singer",
            margin_l=0,
            margin_r=0,
            margin_t=0,
            margin_b=0,
        )
        declarations = ParsedDeclarations(
            setup=[
                CodeDeclaration(
                    body=CodeBody('other_styles = ("Alt",)'),
                    scope=Scope.SETUP,
                )
            ],
            line=[
                TemplateDeclaration(
                    body=TemplateBody("bad-line-reference"),
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(
                        styles="other_styles",
                        no_text=True,
                    ),
                ),
                TemplateDeclaration(
                    body=TemplateBody("L"),
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(no_text=True),
                ),
            ],
            word=[
                TemplateDeclaration(
                    body=TemplateBody("bad-word-style"),
                    scope=Scope.WORD,
                    style="Other",
                    modifiers=TemplateModifiers(),
                ),
                TemplateDeclaration(
                    body=TemplateBody("bad-word-reference"),
                    scope=Scope.WORD,
                    modifiers=TemplateModifiers(styles="other_styles"),
                ),
                CodeDeclaration(
                    body=CodeBody("last_word = word.trimmed_text"),
                    scope=Scope.WORD,
                ),
                TemplateDeclaration(
                    body=TemplateBody("bad-word-condition"),
                    scope=Scope.WORD,
                    modifiers=TemplateModifiers(when="False"),
                ),
                TemplateDeclaration(
                    body=TemplateBody("W!last_word!:"),
                    scope=Scope.WORD,
                    modifiers=TemplateModifiers(no_blank=True),
                ),
            ],
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("bad-syl-reference"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(styles="other_styles"),
                )
            ],
            char=[
                TemplateDeclaration(
                    body=TemplateBody("bad-char-style"),
                    scope=Scope.CHAR,
                    style="Other",
                    modifiers=TemplateModifiers(),
                ),
                TemplateDeclaration(
                    body=TemplateBody("bad-char-reference"),
                    scope=Scope.CHAR,
                    modifiers=TemplateModifiers(styles="other_styles"),
                ),
                TemplateDeclaration(
                    body=TemplateBody("bad-char-condition"),
                    scope=Scope.CHAR,
                    modifiers=TemplateModifiers(when="False"),
                ),
                TemplateDeclaration(
                    body=TemplateBody("C$char_i:"),
                    scope=Scope.CHAR,
                    modifiers=TemplateModifiers(
                        when="char.text.strip() != ''",
                    ),
                ),
            ],
        )

        results = engine.apply(
            [event],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {
                "Default": make_style(),
                "Alt": make_style("Alt"),
            },
        )

        assert [result.text for result in results] == [
            "L",
            "Wgo:  go",
            "C2:g",
            "C3:o",
        ]

    def test_styles_modifier_rejects_single_style_name(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            line=[
                TemplateDeclaration(
                    body=TemplateBody("body"),
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(styles="Default"),
                )
            ]
        )

        with pytest.raises(TemplateRuntimeError):
            engine.apply(
                [make_event()],
                declarations,
                Metadata(res_x=1920, res_y=1080),
                {"Default": make_style()},
            )

    def test_styles_modifier_raises_pykara_error_for_missing_style(
        self,
    ) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            setup=[
                CodeDeclaration(
                    body=CodeBody('my_styles = ("Missing",)'),
                    scope=Scope.SETUP,
                )
            ],
            line=[
                TemplateDeclaration(
                    body=TemplateBody("body"),
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(styles="my_styles"),
                )
            ],
        )

        with pytest.raises(UnknownStyleReferenceError):
            engine.apply(
                [make_event()],
                declarations,
                Metadata(res_x=1920, res_y=1080),
                {"Default": make_style()},
            )

    def test_mixin_injects_tags_before_matching_syllable_text(self) -> None:
        engine = build_engine()
        event = make_event()
        declarations = ParsedDeclarations(
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("S$syl_i:"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(),
                ),
            ],
            mixin_syl=[
                MixinDeclaration(
                    body=MixinBody("<!syl.text!>"),
                    scope=Scope.SYL,
                    modifiers=MixinModifiers(),
                )
            ],
        )

        results = engine.apply(
            [event],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == [
            "S0:<go>go",
            "S1:<al>al",
        ]

    def test_mixin_can_use_store_functions(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("T:"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(),
                ),
            ],
            mixin_syl=[
                MixinDeclaration(
                    body=MixinBody("!put('label', syl.text)!"),
                    scope=Scope.SYL,
                    modifiers=MixinModifiers(),
                ),
                MixinDeclaration(
                    body=MixinBody("<!get('label')!>"),
                    scope=Scope.SYL,
                    modifiers=MixinModifiers(),
                ),
            ],
        )

        results = engine.apply(
            [make_event()],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == [
            "T:go<go>go",
            "T:al<al>al",
        ]

    def test_mixin_can_use_safe_builtins(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("T:"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(),
                ),
            ],
            mixin_syl=[
                MixinDeclaration(
                    body=MixinBody("<!sum(range(len(syl.text)))!>"),
                    scope=Scope.SYL,
                    modifiers=MixinModifiers(),
                ),
            ],
        )

        results = engine.apply(
            [make_event()],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == [
            "T:<1>go",
            "T:<1>al",
        ]

    def test_mixin_can_read_value_locked_by_template(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            line=[
                TemplateDeclaration(
                    body=TemplateBody(
                        r"{\1c!lock('main', color.rgb_to_ass(255, 200, 0))!}"
                    ),
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(),
                ),
            ],
            mixin_line=[
                MixinDeclaration(
                    body=MixinBody(r"{\3c!get('main')!}"),
                    scope=Scope.LINE,
                    modifiers=MixinModifiers(),
                ),
            ],
        )

        results = engine.apply(
            [make_event()],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == [
            r"{\3c&H00C8FF&\1c&H00C8FF&}goal"
        ]

    def test_mixin_tags_are_merged_with_template_tags_by_default(
        self,
    ) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            syl=[
                TemplateDeclaration(
                    body=TemplateBody(r"{\an5}"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(),
                )
            ],
            mixin_syl=[
                MixinDeclaration(
                    body=MixinBody(r"{\blur2}"),
                    scope=Scope.SYL,
                    modifiers=MixinModifiers(),
                )
            ],
        )

        results = engine.apply(
            [make_event()],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == [
            r"{\an5\blur2}go",
            r"{\an5\blur2}al",
        ]

    def test_no_merge_keeps_mixin_and_template_tag_blocks_separate(
        self,
    ) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            syl=[
                TemplateDeclaration(
                    body=TemplateBody(r"{\an5}"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(no_merge=True),
                )
            ],
            mixin_syl=[
                MixinDeclaration(
                    body=MixinBody(r"{\blur2}"),
                    scope=Scope.SYL,
                    modifiers=MixinModifiers(),
                )
            ],
        )

        results = engine.apply(
            [make_event()],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == [
            r"{\an5}{\blur2}go",
            r"{\an5}{\blur2}al",
        ]

    def test_mixin_prepend_layer_and_actor_filters_template_output(
        self,
    ) -> None:
        engine = build_engine()
        event = make_event()
        declarations = ParsedDeclarations(
            line=[
                TemplateDeclaration(
                    body=TemplateBody("!layer.set(2)!T:"),
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(),
                    actor="lead",
                ),
                TemplateDeclaration(
                    body=TemplateBody("U:"),
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(),
                    actor="shadow",
                ),
            ],
            mixin_line=[
                MixinDeclaration(
                    body=MixinBody("P:"),
                    scope=Scope.LINE,
                    modifiers=MixinModifiers(
                        prepend=True,
                        layer=2,
                        for_actor="lead",
                    ),
                ),
                MixinDeclaration(
                    body=MixinBody("I:"),
                    scope=Scope.LINE,
                    modifiers=MixinModifiers(layer=2, for_actor="lead"),
                ),
                MixinDeclaration(
                    body=MixinBody("X:"),
                    scope=Scope.LINE,
                    modifiers=MixinModifiers(for_actor="missing"),
                ),
                MixinDeclaration(
                    body=MixinBody("A:"),
                    scope=Scope.LINE,
                    modifiers=MixinModifiers(layer=2),
                    actor="ignored",
                ),
            ],
        )

        results = engine.apply(
            [event],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == [
            "P:I:A:T:goal",
            "U:goal",
        ]
        assert [result.layer for result in results] == [2, 0]

    def test_template_uses_natural_layer_unless_relayer_changes_it(
        self,
    ) -> None:
        engine = build_engine()
        event = make_event()
        declarations = ParsedDeclarations(
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("A:"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(),
                    layer=4,
                ),
                TemplateDeclaration(
                    body=TemplateBody("!layer.set(7)!B:"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(),
                    layer=5,
                ),
            ]
        )

        results = engine.apply(
            [event],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == [
            "A:go",
            "B:go",
            "A:al",
            "B:al",
        ]
        assert [result.layer for result in results] == [4, 7, 4, 7]

    def test_applies_code_setup_line_syl_and_char_templates(self) -> None:
        engine = build_engine()
        event = make_event()
        declarations = ParsedDeclarations(
            setup=[
                CodeDeclaration(
                    body=CodeBody("prefix = 'P:'"),
                    scope=Scope.SETUP,
                )
            ],
            line=[
                TemplateDeclaration(
                    body=TemplateBody("!prefix!L$line_i-"),
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(no_text=True),
                )
            ],
            syl=[
                CodeDeclaration(
                    body=CodeBody("seen = syl.i"),
                    scope=Scope.SYL,
                ),
                TemplateDeclaration(
                    body=TemplateBody("S$syl_i:"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(),
                ),
            ],
            char=[
                TemplateDeclaration(
                    body=TemplateBody("C$char_n-$char_x:"),
                    scope=Scope.CHAR,
                    modifiers=TemplateModifiers(no_text=False),
                )
            ],
        )

        results = engine.apply(
            [event],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == [
            "P:L0-",
            "S0:go",
            "C4-945:g",
            "C4-955:o",
            "S1:al",
            "C4-965:a",
            "C4-975:l",
        ]
        assert all(result.effect == "fx" for result in results)

    def test_code_does_not_expose_store_functions(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            line=[
                CodeDeclaration(
                    body=CodeBody("put('main', 1)"),
                    scope=Scope.LINE,
                )
            ]
        )

        with pytest.raises(TemplateRuntimeError):
            engine.apply(
                [make_event()],
                declarations,
                Metadata(res_x=1920, res_y=1080),
                {"Default": make_style()},
            )

    def test_applies_word_templates_grouped_by_spaces(self) -> None:
        engine = build_engine()
        event = Event(
            text=r"{\k20}go{\k30} al{\k10}!",
            effect="karaoke",
            style="Default",
            layer=0,
            start_time=1000,
            end_time=1600,
            comment=False,
            actor="Singer",
            margin_l=0,
            margin_r=0,
            margin_t=0,
            margin_b=0,
        )
        declarations = ParsedDeclarations(
            word=[
                TemplateDeclaration(
                    body=TemplateBody(
                        "W$word_i/$word_n:$word_left-$word_right:"
                    ),
                    scope=Scope.WORD,
                    modifiers=TemplateModifiers(),
                )
            ]
        )

        results = engine.apply(
            [event],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == [
            "W0/2:930-950:go",
            "W1/2:960-990: al!",
        ]

    def test_applies_word_templates_to_plain_karaoke_words(self) -> None:
        engine = build_engine()
        event = Event(
            text="Foo bar boo bar nee sii",
            effect="karaoke",
            style="Default",
            layer=0,
            start_time=0,
            end_time=5000,
            comment=False,
            actor="Singer",
            margin_l=0,
            margin_r=0,
            margin_t=0,
            margin_b=0,
        )
        declarations = ParsedDeclarations(
            word=[
                TemplateDeclaration(
                    body=TemplateBody("W$word_i/$word_n:$word_center:"),
                    scope=Scope.WORD,
                    modifiers=TemplateModifiers(no_blank=True),
                )
            ]
        )

        results = engine.apply(
            [event],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == [
            "W0/6:860:Foo",
            "W1/6:900: bar",
            "W2/6:940: boo",
            "W3/6:980: bar",
            "W4/6:1020: nee",
            "W5/6:1060: sii",
        ]

    def test_syllable_scope_can_access_current_word(self) -> None:
        engine = build_engine()
        event = Event(
            text=r"{\k20}go{\k30} al{\k10}!",
            effect="karaoke",
            style="Default",
            layer=0,
            start_time=1000,
            end_time=1600,
            comment=False,
            actor="Singer",
            margin_l=0,
            margin_r=0,
            margin_t=0,
            margin_b=0,
        )
        declarations = ParsedDeclarations(
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("$word_i-$syl_i:"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(),
                )
            ]
        )

        results = engine.apply(
            [event],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == [
            "0-0:go",
            "1-1: al",
            "1-2:!",
        ]

    def test_word_scope_cannot_access_syllable_object(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            word=[
                CodeDeclaration(
                    body=CodeBody("bad = syl.i"),
                    scope=Scope.WORD,
                )
            ]
        )

        with pytest.raises(TemplateRuntimeError):
            engine.apply(
                [make_event()],
                declarations,
                Metadata(res_x=1920, res_y=1080),
                {"Default": make_style()},
            )

    def test_exposes_metadata_object_in_template_expressions(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            line=[
                TemplateDeclaration(
                    body=TemplateBody("!metadata.res_x!x!metadata.res_y!"),
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(no_text=True),
                )
            ]
        )

        results = engine.apply(
            [make_event()],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == ["1920x1080"]

    def test_exposes_syllable_tag_family_in_template_expressions(
        self,
    ) -> None:
        engine = build_engine()
        event = Event(
            text=r"{\k20}go{\kf30}al",
            effect="karaoke",
            style="Default",
            layer=0,
            start_time=1000,
            end_time=1500,
            comment=False,
            actor="Singer",
            margin_l=0,
            margin_r=0,
            margin_t=0,
            margin_b=0,
        )
        declarations = ParsedDeclarations(
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("!syl.tag!"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(no_text=True),
                )
            ]
        )

        results = engine.apply(
            [event],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == ["\\k", "\\kf"]

    def test_supports_when_unless_and_loop(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("W$loop_i/$loop_n"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(
                        when="syl.i == 0",
                        loops=(LoopDescriptor(name="i", iterations=2),),
                    ),
                ),
                TemplateDeclaration(
                    body=TemplateBody("U"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(unless="syl.i == 0"),
                ),
            ]
        )

        results = engine.apply(
            [make_single_syllable_event()],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == [
            "W0/2go",
            "W1/2go",
        ]

    def test_lock_keeps_value_across_loop_iterations(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("!lock('picked', $loop_i)!-$loop_i"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(
                        no_text=True,
                        loops=(LoopDescriptor(name="i", iterations=3),),
                    ),
                ),
            ]
        )

        results = engine.apply(
            [make_single_syllable_event()],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == [
            "0-0",
            "0-1",
            "0-2",
        ]

    def test_put_and_lock_reject_bare_key_names(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("!put(name, 123)!!lock(name, 123)!"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(no_text=True),
                ),
            ]
        )

        with pytest.raises(TemplateRuntimeError):
            engine.apply(
                [make_single_syllable_event()],
                declarations,
                Metadata(res_x=1920, res_y=1080),
                {"Default": make_style()},
            )

    def test_put_rejects_keys_locked_by_template(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("!lock('picked', 1)!!put('picked', 2)!"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(no_text=True),
                ),
            ]
        )

        with pytest.raises(TemplateRuntimeError):
            engine.apply(
                [make_single_syllable_event()],
                declarations,
                Metadata(res_x=1920, res_y=1080),
                {"Default": make_style()},
            )

    def test_supports_loop_expression_counts(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("L$loop_j_i/$loop_j_n:"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(
                        loops=(
                            LoopDescriptor(
                                name="j",
                                iterations="math.floor($syl_width / 10)",
                                explicit_name="j",
                            ),
                        ),
                    ),
                )
            ]
        )

        results = engine.apply(
            [make_single_syllable_event()],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == [
            "L0/2:go",
            "L1/2:go",
        ]

    def test_declarations_apply_only_to_matching_style_by_default(
        self,
    ) -> None:
        engine = build_engine()
        event = make_single_syllable_event()
        declarations = ParsedDeclarations(
            syl=[
                CodeDeclaration(
                    body=CodeBody("shared = 'A'"),
                    scope=Scope.SYL,
                    style="",
                ),
                TemplateDeclaration(
                    body=TemplateBody("M!shared!:"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(),
                    style="Default",
                ),
                TemplateDeclaration(
                    body=TemplateBody("S"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(),
                    style="Other",
                ),
            ]
        )

        results = engine.apply(
            [event],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == ["MA:go"]

    def test_reassigns_line_code_variables_for_each_line(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            line=[
                CodeDeclaration(
                    body=CodeBody("value = line.i"),
                    scope=Scope.LINE,
                ),
                TemplateDeclaration(
                    body=TemplateBody("!value!"),
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(no_text=True),
                ),
            ]
        )

        results = engine.apply(
            [make_event(), make_single_syllable_event()],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == ["0", "1"]

    def test_line_code_uses_current_source_line_timing(self) -> None:
        engine = build_engine()
        second_event = Event(
            text=r"{\k50}go",
            effect="karaoke",
            style="Default",
            layer=0,
            start_time=2000,
            end_time=2600,
            comment=False,
            actor="Singer",
            margin_l=0,
            margin_r=0,
            margin_t=0,
            margin_b=0,
        )
        declarations = ParsedDeclarations(
            line=[
                CodeDeclaration(
                    body=CodeBody(
                        "prev_end = line.start - 1000 if line.i == 0 "
                        "else last_end;"
                        " gap = line.start - prev_end;"
                        " last_end = line.end"
                    ),
                    scope=Scope.LINE,
                ),
                TemplateDeclaration(
                    body=TemplateBody("!gap!"),
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(no_text=True),
                ),
            ]
        )

        results = engine.apply(
            [make_event(), second_event],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == ["1000", "500"]

    def test_line_code_functions_capture_current_line_namespace(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            line=[
                CodeDeclaration(
                    body=CodeBody(
                        "label = 'ready'\n"
                        "def describe(): return f'{line.start}:{label}'"
                    ),
                    scope=Scope.LINE,
                ),
                TemplateDeclaration(
                    body=TemplateBody("!describe()!"),
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(no_text=True),
                ),
            ]
        )

        results = engine.apply(
            [make_event(), make_single_syllable_event()],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == [
            "1000:ready",
            "1000:ready",
        ]

    def test_setup_code_does_not_gain_line_namespace_later(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            setup=[
                CodeDeclaration(
                    body=CodeBody("def describe(): return line.start"),
                    scope=Scope.SETUP,
                )
            ],
            line=[
                TemplateDeclaration(
                    body=TemplateBody("!describe()!"),
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(no_text=True),
                )
            ],
        )

        with pytest.raises(TemplateRuntimeError):
            engine.apply(
                [make_event()],
                declarations,
                Metadata(res_x=1920, res_y=1080),
                {"Default": make_style()},
            )

    def test_processes_karaoke_effect_lines_without_k_tags(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            line=[
                TemplateDeclaration(
                    body=TemplateBody("L"),
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(no_text=True),
                )
            ]
        )
        plain_karaoke_event = Event(
            text="plain text",
            effect="karaoke",
            style="Default",
            layer=0,
            start_time=1000,
            end_time=1500,
            comment=False,
            actor="Singer",
            margin_l=0,
            margin_r=0,
            margin_t=0,
            margin_b=0,
        )

        results = engine.apply(
            [plain_karaoke_event],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == ["L"]

    def test_supports_multiple_named_loops_in_cartesian_order(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("A$loop_a_i-B$loop_b_i"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(
                        when="syl.i == 0",
                        loops=(
                            LoopDescriptor(
                                name="a",
                                iterations=2,
                                explicit_name="a",
                            ),
                            LoopDescriptor(
                                name="b",
                                iterations=3,
                                explicit_name="b",
                            ),
                        ),
                    ),
                )
            ]
        )

        results = engine.apply(
            [make_single_syllable_event()],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == [
            "A0-B0go",
            "A0-B1go",
            "A0-B2go",
            "A1-B0go",
            "A1-B1go",
            "A1-B2go",
        ]

    def test_supports_single_loop_object_in_expressions(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("!loop.i!/!loop.n!:"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(
                        loops=(
                            LoopDescriptor(
                                name="i",
                                iterations=3,
                            ),
                        ),
                    ),
                )
            ]
        )

        results = engine.apply(
            [make_single_syllable_event()],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == [
            "0/3:go",
            "1/3:go",
            "2/3:go",
        ]

    def test_supports_named_loop_object_in_expressions(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("!loop.x.i!/!loop.x.n!:"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(
                        loops=(
                            LoopDescriptor(
                                name="x",
                                iterations=3,
                                explicit_name="x",
                            ),
                        ),
                    ),
                )
            ]
        )

        results = engine.apply(
            [make_single_syllable_event()],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == [
            "0/3:go",
            "1/3:go",
            "2/3:go",
        ]

    def test_supports_multiple_named_loop_objects_in_expressions(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("!loop.a.i!-!loop.b.i!:"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(
                        loops=(
                            LoopDescriptor(
                                name="a",
                                iterations=2,
                                explicit_name="a",
                            ),
                            LoopDescriptor(
                                name="b",
                                iterations=2,
                                explicit_name="b",
                            ),
                        ),
                    ),
                )
            ]
        )

        results = engine.apply(
            [make_single_syllable_event()],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == [
            "0-0:go",
            "0-1:go",
            "1-0:go",
            "1-1:go",
        ]

    def test_loop_i_property_is_invalid_with_multiple_loops(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("!loop.i!"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(
                        loops=(
                            LoopDescriptor(
                                name="a",
                                iterations=2,
                                explicit_name="a",
                            ),
                            LoopDescriptor(
                                name="b",
                                iterations=2,
                                explicit_name="b",
                            ),
                        ),
                    ),
                )
            ]
        )

        with pytest.raises(TemplateRuntimeError):
            engine.apply(
                [make_single_syllable_event()],
                declarations,
                Metadata(res_x=1920, res_y=1080),
                {"Default": make_style()},
            )

    def test_loop_flat_variable_is_not_expression_api(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("!loop_x_i!"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(
                        loops=(
                            LoopDescriptor(
                                name="x",
                                iterations=2,
                                explicit_name="x",
                            ),
                        ),
                    ),
                )
            ]
        )

        with pytest.raises(TemplateRuntimeError):
            engine.apply(
                [make_single_syllable_event()],
                declarations,
                Metadata(res_x=1920, res_y=1080),
                {"Default": make_style()},
            )

    def test_loop_i_is_invalid_when_multiple_loops_are_visible(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("$loop_i"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(
                        when="syl.i == 0",
                        loops=(
                            LoopDescriptor(
                                name="a",
                                iterations=2,
                                explicit_name="a",
                            ),
                            LoopDescriptor(
                                name="b",
                                iterations=2,
                                explicit_name="b",
                            ),
                        ),
                    ),
                )
            ]
        )

        with pytest.raises(UnknownVariableError):
            engine.apply(
                [make_event()],
                declarations,
                Metadata(res_x=1920, res_y=1080),
                {"Default": make_style()},
            )

    def test_line_loop_does_not_make_syl_loop_i_ambiguous(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            line=[
                TemplateDeclaration(
                    body=TemplateBody("L$loop_i"),
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(
                        no_text=True,
                        loops=(LoopDescriptor(name="i", iterations=2),),
                    ),
                )
            ],
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("S$loop_i:"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(
                        no_text=False,
                        loops=(LoopDescriptor(name="i", iterations=2),),
                    ),
                )
            ],
        )

        results = engine.apply(
            [make_single_syllable_event()],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == [
            "L0",
            "L1",
            "S0:go",
            "S1:go",
        ]

    def test_independent_line_loops_do_not_duplicate_syl_templates(
        self,
    ) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            line=[
                TemplateDeclaration(
                    body=TemplateBody("L$loop_glow_i"),
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(
                        no_text=True,
                        loops=(
                            LoopDescriptor(
                                name="glow",
                                iterations=2,
                                explicit_name="glow",
                            ),
                        ),
                    ),
                ),
                TemplateDeclaration(
                    body=TemplateBody("R$loop_rib_i"),
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(
                        no_text=True,
                        loops=(
                            LoopDescriptor(
                                name="rib",
                                iterations=2,
                                explicit_name="rib",
                            ),
                        ),
                    ),
                ),
            ],
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("S:"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(no_text=False),
                )
            ],
        )

        results = engine.apply(
            [make_single_syllable_event()],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == [
            "L0",
            "L1",
            "R0",
            "R1",
            "S:go",
        ]

    def test_syl_loop_does_not_make_char_loop_i_ambiguous(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("S$loop_i:"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(
                        when="syl.i == 0",
                        loops=(LoopDescriptor(name="i", iterations=2),),
                    ),
                )
            ],
            char=[
                TemplateDeclaration(
                    body=TemplateBody("C$loop_i-$char_x:"),
                    scope=Scope.CHAR,
                    modifiers=TemplateModifiers(
                        no_text=False,
                        when="syl.i == 0",
                        loops=(LoopDescriptor(name="i", iterations=2),),
                    ),
                )
            ],
        )

        results = engine.apply(
            [make_single_syllable_event()],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == [
            "S0:go",
            "S1:go",
            "C0-955:g",
            "C1-955:g",
            "C0-965:o",
            "C1-965:o",
        ]

    def test_honors_no_blank_modifier(self) -> None:
        engine = build_engine()
        blank_event = Event(
            text=r"{\k20}  {\k30}go",
            effect="karaoke",
            style="Default",
            layer=0,
            start_time=1000,
            end_time=1500,
            comment=False,
            actor="Singer",
            margin_l=0,
            margin_r=0,
            margin_t=0,
            margin_b=0,
        )
        declarations = ParsedDeclarations(
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("X"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(no_blank=True),
                )
            ]
        )

        results = engine.apply(
            [blank_event],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == ["Xgo"]

    def test_renders_leading_blank_syllable_without_no_blank(self) -> None:
        engine = build_engine()
        blank_event = make_leading_blank_syllable_event()
        declarations = ParsedDeclarations(
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("S$syl_i:"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(),
                )
            ]
        )

        results = engine.apply(
            [blank_event],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == ["S0:", "S1:ka"]

    def test_no_blank_skips_leading_blank_syllable(self) -> None:
        engine = build_engine()
        blank_event = make_leading_blank_syllable_event()
        declarations = ParsedDeclarations(
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("S$syl_i:"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(no_blank=True),
                )
            ]
        )

        results = engine.apply(
            [blank_event],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == ["S0:ka"]

    def test_no_blank_reindexes_syllables_and_line_syls(self) -> None:
        engine = build_engine()
        blank_event = make_leading_blank_syllable_event()
        declarations = ParsedDeclarations(
            syl=[
                TemplateDeclaration(
                    body=TemplateBody(
                        "$syl_i/$syl_n:$syl_center:!line.syls[$syl_i].center!"
                    ),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(no_blank=True),
                )
            ]
        )

        results = engine.apply(
            [blank_event],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == ["0/1:960:960.0ka"]

    def test_no_blank_reindexes_conditions_for_first_visible_syllable(
        self,
    ) -> None:
        engine = build_engine()
        blank_event = make_leading_blank_syllable_event()
        declarations = ParsedDeclarations(
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("F"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(
                        no_blank=True,
                        when="syl.i == 0",
                    ),
                )
            ]
        )

        results = engine.apply(
            [blank_event],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == ["Fka"]

    def test_honors_line_no_blank_modifier(self) -> None:
        engine = build_engine()
        blank_event = Event(
            text=r"{\k20}  ",
            effect="karaoke",
            style="Default",
            layer=0,
            start_time=1000,
            end_time=1200,
            comment=False,
            actor="Singer",
            margin_l=0,
            margin_r=0,
            margin_t=0,
            margin_b=0,
        )
        declarations = ParsedDeclarations(
            line=[
                TemplateDeclaration(
                    body=TemplateBody("X"),
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(no_blank=True),
                )
            ]
        )

        results = engine.apply(
            [blank_event],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert results == []

    def test_honors_fx_modifier(self) -> None:
        engine = build_engine()
        fx_event = Event(
            text=r"{\k20\-flash}go{\k30}al",
            effect="karaoke",
            style="Default",
            layer=0,
            start_time=1000,
            end_time=1500,
            comment=False,
            actor="Singer",
            margin_l=0,
            margin_r=0,
            margin_t=0,
            margin_b=0,
        )
        declarations = ParsedDeclarations(
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("F"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(fx="flash"),
                )
            ]
        )

        results = engine.apply(
            [fx_event],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == ["Fgo", "Fal"]

    def test_multi_highlight_is_processed_once_per_merged_syllable(
        self,
    ) -> None:
        engine = build_engine()
        event = Event(
            text=r"{\k10}go{\k20}#al",
            effect="karaoke",
            style="Default",
            layer=0,
            start_time=1000,
            end_time=1300,
            comment=False,
            actor="Singer",
            margin_l=0,
            margin_r=0,
            margin_t=0,
            margin_b=0,
        )
        declarations = ParsedDeclarations(
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("M"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(),
                )
            ]
        )

        results = engine.apply(
            [event],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == ["Mgo"]

    def test_renders_namespaced_retime_target(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("!retime.syl(10, 20)!S"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(no_text=True),
                )
            ]
        )

        results = engine.apply(
            [make_event()],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [(result.start_time, result.end_time) for result in results] == [
            (1010, 1220),
            (1210, 1520),
        ]

    def test_render_namespace_reuse_preserves_template_side_effects(
        self,
    ) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            syl=[
                TemplateDeclaration(
                    body=TemplateBody(
                        "!layer.set(3)!"
                        "!put('picked', random.randint(1, 10))!"
                        "!get('picked')!-!line.layer!-"
                        "!retime.syl(10, 20)!S"
                    ),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(no_text=True),
                )
            ]
        )

        results = engine.apply(
            [make_event()],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [result.text for result in results] == ["33-3-S", "1010-3-S"]
        assert [result.layer for result in results] == [3, 3]
        assert [(result.start_time, result.end_time) for result in results] == [
            (1010, 1220),
            (1210, 1520),
        ]

    def test_renders_line_preset_over_chars(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            char=[
                TemplateDeclaration(
                    body=TemplateBody("!retime.line.ltr(-300, 0)!C"),
                    scope=Scope.CHAR,
                    modifiers=TemplateModifiers(no_text=True),
                )
            ]
        )

        results = engine.apply(
            [make_event()],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [(result.start_time, result.end_time) for result in results] == [
            (700, 1500),
            (800, 1500),
            (900, 1500),
            (1000, 1500),
        ]

    def test_renders_start_to_syllable_preset_over_line_chars(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            char=[
                TemplateDeclaration(
                    body=TemplateBody("!retime.start2syl.ltr(-300, 0)!C"),
                    scope=Scope.CHAR,
                    modifiers=TemplateModifiers(no_text=True),
                )
            ]
        )

        results = engine.apply(
            [make_event()],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [(result.start_time, result.end_time) for result in results] == [
            (700, 1000),
            (800, 1000),
            (900, 1200),
            (1000, 1200),
        ]

    def test_renders_syllable_to_end_preset_over_line_chars(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            char=[
                TemplateDeclaration(
                    body=TemplateBody("!retime.syl2end.ltr(0, 300)!C"),
                    scope=Scope.CHAR,
                    modifiers=TemplateModifiers(no_text=True),
                )
            ]
        )

        results = engine.apply(
            [make_event()],
            declarations,
            Metadata(res_x=1920, res_y=1080),
            {"Default": make_style()},
        )

        assert [(result.start_time, result.end_time) for result in results] == [
            (1200, 1500),
            (1200, 1600),
            (1500, 1700),
            (1500, 1800),
        ]

    def test_rejects_preset_in_line_scope(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            line=[
                TemplateDeclaration(
                    body=TemplateBody("!retime.line.ltr(-300, 0)!L"),
                    scope=Scope.LINE,
                    modifiers=TemplateModifiers(no_text=True),
                )
            ]
        )

        with pytest.raises(TemplateRuntimeError):
            engine.apply(
                [make_event()],
                declarations,
                Metadata(res_x=1920, res_y=1080),
                {"Default": make_style()},
            )

    def test_rejects_multiple_retime_calls_per_template(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("!retime.line()!!retime.syl()!S"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(no_text=True),
                )
            ]
        )

        with pytest.raises(TemplateRuntimeError):
            engine.apply(
                [make_event()],
                declarations,
                Metadata(res_x=1920, res_y=1080),
                {"Default": make_style()},
            )

    def test_raises_on_callable_saved_by_put(self) -> None:
        engine = build_engine()
        declarations = ParsedDeclarations(
            syl=[
                TemplateDeclaration(
                    body=TemplateBody("!put('bad', layer.set)!"),
                    scope=Scope.SYL,
                    modifiers=TemplateModifiers(no_text=True),
                )
            ]
        )

        with pytest.raises(TemplateRuntimeError):
            engine.apply(
                [make_event()],
                declarations,
                Metadata(res_x=1920, res_y=1080),
                {"Default": make_style()},
            )
