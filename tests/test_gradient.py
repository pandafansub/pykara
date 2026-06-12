"""Tests for the gradient namespace and expansion pipeline."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol, cast

import pytest

from pykara.data import Event, Metadata
from pykara.declaration import Scope
from pykara.declaration.mixin import MixinBody, MixinModifiers
from pykara.declaration.template import (
    LoopDescriptor,
    TemplateBody,
    TemplateModifiers,
)
from pykara.engine import GeneratedLine
from pykara.engine.functions import FUNCTION_REGISTRY
from pykara.errors import EngineError
from pykara.fbf.timeline import FrameRateSource
from pykara.motion import GRADIENT_PLACEHOLDER, GradientRequest
from pykara.motion.common import EventExpander, QueuedEventExpansion
from pykara.parsing import (
    MixinDeclaration,
    ParsedDeclarations,
    TemplateDeclaration,
)
from tests.effect_support import (
    build_engine,
    make_event,
    make_generated_line,
    make_style,
)


class _GradientNamespace(Protocol):
    def make(
        self,
        colors: object,
        step: object = 2,
        direction: object = "top-bottom",
        **kwargs: object,
    ) -> str: ...


def gradient_namespace(env: DummyEnv) -> _GradientNamespace:
    namespace = FUNCTION_REGISTRY.build_namespace(env, "template")
    return cast(_GradientNamespace, namespace["gradient"])


@dataclass(slots=True)
class DummyVars:
    line_x: int | None = 640
    line_y: int | None = 360
    line_left: int | None = 620
    line_center: int | None = 640
    line_right: int | None = 660
    line_top: int | None = 340
    line_bottom: int | None = 380
    char_left: int | None = None
    char_center: int | None = None
    char_right: int | None = None
    char_top: int | None = None
    char_middle: int | None = None
    char_bottom: int | None = None
    word_left: int | None = None
    word_center: int | None = None
    word_right: int | None = None
    word_top: int | None = None
    word_middle: int | None = None
    word_bottom: int | None = None
    syl_left: int | None = None
    syl_center: int | None = None
    syl_right: int | None = None
    syl_top: int | None = None
    syl_middle: int | None = None
    syl_bottom: int | None = None


@dataclass(slots=True)
class DummyEnv:
    metadata: Metadata | None = field(
        default_factory=lambda: Metadata(
            res_x=1280,
            res_y=720,
            raw={"PlaybackFPS": "24"},
        )
    )
    line: GeneratedLine | None = None
    vars: DummyVars = field(default_factory=DummyVars)
    word: object | None = None
    syl: object | None = None
    char: object | None = None


class DummyExpander(EventExpander):
    def expand(
        self,
        event: Event,
        framerate: FrameRateSource,
    ) -> list[Event]:
        del framerate
        return [event]


class TestGradientNamespace:
    def test_make_queues_gradient_request(self) -> None:
        env = DummyEnv(line=make_generated_line())
        result = gradient_namespace(env).make(["&H0000FF&", "&HFF0000&"])

        assert result.startswith(GRADIENT_PLACEHOLDER)
        assert env.line is not None
        assert len(env.line.expansion_requests) == 1
        queued_expansion = env.line.expansion_requests[0]
        assert queued_expansion.label == "gradient.make()"
        assert queued_expansion.phase == "gradient"
        assert isinstance(queued_expansion.expander, GradientRequest)

    def test_make_requires_framerate(self) -> None:
        env = DummyEnv(
            line=make_generated_line(),
            metadata=Metadata(res_x=1280, res_y=720),
        )
        gradient = gradient_namespace(env)

        with pytest.raises(
            EngineError,
            match=(
                r"gradient\.make\(\) requires explicit timecodes "
                r"or PlaybackFPS"
            ),
        ):
            gradient.make(["&H0000FF&", "&HFF0000&"])

    def test_make_validates_colors_step_and_direction(self) -> None:
        env = DummyEnv(line=make_generated_line())
        gradient = gradient_namespace(env)

        with pytest.raises(
            EngineError,
            match=r"gradient\.make\(\) expects a sequence of ASS colors",
        ):
            gradient.make("&H0000FF&")

        with pytest.raises(
            EngineError,
            match=r"gradient\.make\(\) requires at least two ASS colors",
        ):
            gradient.make(["&H0000FF&"])

        with pytest.raises(
            EngineError,
            match=r"gradient\.make\(\) step must be a positive number",
        ):
            gradient.make(["&H0000FF&", "&HFF0000&"], step=0)

        with pytest.raises(
            EngineError,
            match=r"gradient\.make\(\) direction must be one of",
        ):
            gradient.make(
                ["&H0000FF&", "&HFF0000&"],
                direction="diagonal",
            )

    def test_make_accepts_multiple_gradient_expansions_by_step(self) -> None:
        env = DummyEnv(line=make_generated_line())
        gradient = gradient_namespace(env)
        assert env.line is not None

        first = gradient.make(["&H0000FF&", "&HFF0000&"], step=16)
        second = gradient.make(["&H00FF00&", "&HFFFFFF&"], step=4)

        assert first != second
        assert [
            cast(GradientRequest, item.expander).step
            for item in env.line.expansion_requests
        ] == [4, 16]

    def test_make_rejects_existing_move_tag(self) -> None:
        env = DummyEnv(
            line=GeneratedLine.from_event(
                make_event(r"{\move(0,0,100,100)\k20}go{\k30}al"),
                make_style(),
            )
        )

        with pytest.raises(
            EngineError,
            match=r"gradient\.make\(\) cannot be combined with \\move",
        ):
            gradient_namespace(env).make(["&H0000FF&", "&HFF0000&"])

    def test_make_coexists_with_motion_fbf_and_keeps_phase_order(self) -> None:
        env = DummyEnv(line=make_generated_line())
        assert env.line is not None
        env.line.expansion_requests.append(
            QueuedEventExpansion(
                label="motion.fbf.arc()",
                phase="motion_fbf",
                expander=DummyExpander(),
            )
        )

        gradient_namespace(env).make(["&H0000FF&", "&HFF0000&"])

        assert [item.phase for item in env.line.expansion_requests] == [
            "motion_fbf",
            "gradient",
        ]


class TestGradientEngineIntegration:
    def test_gradient_expands_into_clip_slices(self) -> None:
        engine = build_engine()
        template = TemplateDeclaration(
            body=TemplateBody(
                r"{\1c!gradient.make(['&H0000FF&','&HFF0000&'], step=8)!}"
            ),
            scope=Scope.LINE,
            modifiers=TemplateModifiers(),
        )

        result = engine.apply(
            [make_event()],
            ParsedDeclarations(line=[template]),
            Metadata(
                res_x=1280,
                res_y=720,
                raw={"PlaybackFPS": "24"},
            ),
            {"Default": make_style()},
        )

        assert len(result) >= 2
        assert all(r"\clip(" in event.text for event in result)
        assert all(GRADIENT_PLACEHOLDER not in event.text for event in result)
        assert len({event.text for event in result}) > 1

    def test_gradient_implicit_line_position_uses_style_margins(self) -> None:
        engine = build_engine()
        template = TemplateDeclaration(
            body=TemplateBody(
                r"{\1c!gradient.make(['&H0000FF&','&HFF0000&'], step=100)!}"
            ),
            scope=Scope.LINE,
            modifiers=TemplateModifiers(),
        )

        result = engine.apply(
            [make_event()],
            ParsedDeclarations(line=[template]),
            Metadata(
                res_x=1280,
                res_y=720,
                raw={"PlaybackFPS": "24"},
            ),
            {"Default": make_style()},
        )

        assert result
        assert all(r"\pos(640,710)" in event.text for event in result)

    def test_gradient_bakes_supported_transforms_before_slicing(self) -> None:
        engine = build_engine()
        template = TemplateDeclaration(
            body=TemplateBody(
                r"{\1c!gradient.make(['&H0000FF&','&HFF0000&'], step=100)!"
                r"\fs20\t(0,500,\fs40)}"
            ),
            scope=Scope.LINE,
            modifiers=TemplateModifiers(),
        )

        result = engine.apply(
            [make_event()],
            ParsedDeclarations(line=[template]),
            Metadata(
                res_x=1280,
                res_y=720,
                raw={"PlaybackFPS": "24"},
            ),
            {"Default": make_style()},
        )

        assert len(result) >= 10
        assert all(r"\t(" not in event.text for event in result)
        font_sizes: set[str] = set()
        for event in result:
            match = re.search(r"\\fs([0-9.]+)", event.text)
            assert match is not None
            font_sizes.add(match.group(1))
        assert len(font_sizes) > 1

    def test_gradient_rejects_move_and_clip_conflicts(self) -> None:
        engine = build_engine()
        move_template = TemplateDeclaration(
            body=TemplateBody(
                r"{\move(0,0,100,100)!gradient.make(['&H0000FF&','&HFF0000&'])!}"
            ),
            scope=Scope.LINE,
            modifiers=TemplateModifiers(),
        )
        clip_template = TemplateDeclaration(
            body=TemplateBody(
                r"{\clip(0,0,10,10)!gradient.make(['&H0000FF&','&HFF0000&'])!}"
            ),
            scope=Scope.LINE,
            modifiers=TemplateModifiers(),
        )

        with pytest.raises(
            EngineError,
            match=r"gradient\.make\(\) cannot be combined with \\move",
        ):
            engine.apply(
                [make_event()],
                ParsedDeclarations(line=[move_template]),
                Metadata(
                    res_x=1280,
                    res_y=720,
                    raw={"PlaybackFPS": "24"},
                ),
                {"Default": make_style()},
            )

        with pytest.raises(
            EngineError,
            match=(
                r"gradient\.make\(\) cannot be combined with "
                r"\\clip or \\iclip"
            ),
        ):
            engine.apply(
                [make_event()],
                ParsedDeclarations(line=[clip_template]),
                Metadata(
                    res_x=1280,
                    res_y=720,
                    raw={"PlaybackFPS": "24"},
                ),
                {"Default": make_style()},
            )

    def test_gradient_can_follow_motion_fbf_expansion(self) -> None:
        engine = build_engine()
        template = TemplateDeclaration(
            body=TemplateBody(
                r"{\1c!gradient.make(['&H0000FF&','&HFF0000&'], step=12)!"
                r"!motion.fbf.arc(640,360,640,360,0,360,120,120)!}"
            ),
            scope=Scope.LINE,
            modifiers=TemplateModifiers(),
        )

        result = engine.apply(
            [make_event()],
            ParsedDeclarations(line=[template]),
            Metadata(
                res_x=1280,
                res_y=720,
                raw={"PlaybackFPS": "24"},
            ),
            {"Default": make_style()},
        )

        assert len(result) >= 20
        assert all(r"\clip(" in event.text for event in result)
        assert all(r"\pos(" in event.text for event in result)
        assert all(GRADIENT_PLACEHOLDER not in event.text for event in result)
        assert all(r"\t(" not in event.text for event in result)

    def test_multiple_gradients_share_smallest_step_priority(self) -> None:
        engine = build_engine()
        template = TemplateDeclaration(
            body=TemplateBody(
                r"{\1c!gradient.make(['&H0000FF&','&HFF0000&'], step=16)!"
                r"\3c!gradient.make(['&H00FF00&','&HFFFFFF&'], step=8)!}"
            ),
            scope=Scope.LINE,
            modifiers=TemplateModifiers(),
        )

        result = engine.apply(
            [make_event()],
            ParsedDeclarations(line=[template]),
            Metadata(
                res_x=1280,
                res_y=720,
                raw={"PlaybackFPS": "24"},
            ),
            {"Default": make_style()},
        )

        assert len(result) >= 2
        assert all(GRADIENT_PLACEHOLDER not in event.text for event in result)
        assert all(r"\1c&H" in event.text for event in result)
        assert all(r"\3c&H" in event.text for event in result)
        assert all(event.text.count(r"\clip(") == 1 for event in result)

    def test_gradient_can_combine_with_motion_shad_arc(self) -> None:
        engine = build_engine()
        template = TemplateDeclaration(
            body=TemplateBody(
                r"{\an5\4c!gradient.make(['&H0000FF&','&HFF0000&'], step=16)!"
                r"!motion.shad.arc(640,360,640,360,0,360,120,120)!}"
            ),
            scope=Scope.LINE,
            modifiers=TemplateModifiers(),
        )

        result = engine.apply(
            [make_event()],
            ParsedDeclarations(line=[template]),
            Metadata(
                res_x=1280,
                res_y=720,
                raw={"PlaybackFPS": "24"},
            ),
            {"Default": make_style()},
        )

        assert result
        assert all(r"\clip(" in event.text for event in result)
        assert all(r"\t(" not in event.text for event in result)
        assert len({event.text for event in result}) > 1

    def test_gradient_can_combine_with_motion_shad_jitter(self) -> None:
        engine = build_engine()
        template = TemplateDeclaration(
            body=TemplateBody(
                r"{\an5\4c!gradient.make(['&H0000FF&','&HFF0000&'], step=16)!"
                r"!motion.shad.jitter(20,20,20,20,100)!}"
            ),
            scope=Scope.LINE,
            modifiers=TemplateModifiers(),
        )

        result = engine.apply(
            [make_event()],
            ParsedDeclarations(line=[template]),
            Metadata(
                res_x=1280,
                res_y=720,
                raw={"PlaybackFPS": "24"},
            ),
            {"Default": make_style()},
        )

        assert result
        assert all(r"\clip(" in event.text for event in result)
        assert all(r"\t(" not in event.text for event in result)
        assert len({event.text for event in result}) > 1

    def test_gradient_can_be_used_in_mixin(self) -> None:
        engine = build_engine()
        template = TemplateDeclaration(
            body=TemplateBody(r"{\an5}"),
            scope=Scope.LINE,
            modifiers=TemplateModifiers(),
        )
        mixin = MixinDeclaration(
            body=MixinBody(r"{\1c!gradient.make(['&H0000FF&','&HFF0000&'])!}"),
            scope=Scope.LINE,
            modifiers=MixinModifiers(),
        )

        result = engine.apply(
            [make_event()],
            ParsedDeclarations(line=[template], mixin_line=[mixin]),
            Metadata(
                res_x=1280,
                res_y=720,
                raw={"PlaybackFPS": "24"},
            ),
            {"Default": make_style()},
        )

        assert len(result) >= 2
        assert all(r"\clip(" in event.text for event in result)
        assert all(GRADIENT_PLACEHOLDER not in event.text for event in result)

    def test_mixin_gradient_only_expands_matching_template_loop_layer(
        self,
    ) -> None:
        engine = build_engine()
        template = TemplateDeclaration(
            body=TemplateBody(r"!layer.set($loop_i + 1)!{\an5}"),
            scope=Scope.SYL,
            modifiers=TemplateModifiers(
                loops=(LoopDescriptor(name="i", iterations=2),)
            ),
        )
        mixin = MixinDeclaration(
            body=MixinBody(
                r"{\1c!gradient.make(['&H0000FF&','&HFF0000&'], step=8)!}"
            ),
            scope=Scope.SYL,
            modifiers=MixinModifiers(layer=2),
        )

        result = engine.apply(
            [make_event()],
            ParsedDeclarations(syl=[template], mixin_syl=[mixin]),
            Metadata(
                res_x=1280,
                res_y=720,
                raw={"PlaybackFPS": "24"},
            ),
            {"Default": make_style()},
        )

        layer_1 = [event for event in result if event.layer == 1]
        layer_2 = [event for event in result if event.layer == 2]

        assert len(layer_1) == 2
        assert len(layer_2) > len(layer_1)
        assert all(r"\clip(" not in event.text for event in layer_1)
        assert all(r"\clip(" in event.text for event in layer_2)
        assert all(GRADIENT_PLACEHOLDER not in event.text for event in result)
