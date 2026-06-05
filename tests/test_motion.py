"""Tests for the motion namespace and expansion pipeline."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol, cast

import pytest

from pykara.data import Event, Metadata
from pykara.declaration import Scope
from pykara.declaration.mixin import MixinBody, MixinModifiers
from pykara.declaration.template import TemplateBody, TemplateModifiers
from pykara.engine import GeneratedLine
from pykara.engine.functions import FUNCTION_REGISTRY
from pykara.errors import EngineError, TemplateRuntimeError
from pykara.fbf.timeline import FrameRateSource
from pykara.motion import (
    SHAD_AUTO_MARKER,
    SHAD_SETUP_FRAGMENT,
    ArcFbfRequest,
    BezierFbfRequest,
    JitterFbfRequest,
    SpringFbfRequest,
    WaveFbfRequest,
)
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


class _ShadNamespace(Protocol):
    def jitter(
        self,
        left: object,
        right: object,
        up: object,
        down: object,
        period: object,
        seed: object = 0,
    ) -> str: ...

    def arc(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        a1: float = 0.0,
        a2: float = 360.0,
        r1: float = 100.0,
        r2: float = 100.0,
    ) -> str: ...


class _FbfNamespace(Protocol):
    def jitter(
        self,
        left: object,
        right: object,
        up: object,
        down: object,
        period: object,
        seed: object = 0,
    ) -> str: ...

    def arc(self, *args: float) -> str: ...

    def bezier(self, *points: tuple[float, float]) -> str: ...

    def spring(self, *args: float) -> str: ...

    def wave(self, *args: float) -> str: ...


class _MotionNamespace(Protocol):
    shad: _ShadNamespace
    fbf: _FbfNamespace


def motion_namespace(env: DummyEnv) -> _MotionNamespace:
    namespace = FUNCTION_REGISTRY.build_namespace(env, "template")
    return cast(_MotionNamespace, namespace["motion"])


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
class DummyTimedElement:
    center: float = 320.0
    middle: float = 240.0
    x: float = 320.0
    y: float = 240.0


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
    word: DummyTimedElement | None = None
    syl: DummyTimedElement | None = None
    char: DummyTimedElement | None = None


class DummyExpander(EventExpander):
    def expand(
        self,
        event: Event,
        framerate: FrameRateSource,
    ) -> list[Event]:
        del framerate
        return [event]


class TestMotionNamespace:
    def test_registry_exposes_motion_namespace(self) -> None:
        env = DummyEnv(line=make_generated_line())

        namespace = FUNCTION_REGISTRY.build_namespace(env, "template")

        assert "motion" in namespace
        assert hasattr(namespace["motion"], "shad")
        assert hasattr(namespace["motion"], "fbf")

    def test_shad_namespace_does_not_expose_manual_init(self) -> None:
        env = DummyEnv(line=make_generated_line())
        motion = motion_namespace(env)

        assert not hasattr(motion.shad, "init")
        assert not hasattr(motion.shad, "setup")

    def test_shad_motion_rejects_multiple_auto_calls(self) -> None:
        env = DummyEnv(line=make_generated_line())
        motion = motion_namespace(env)
        motion.shad.arc(640, 360, 640, 360)

        with pytest.raises(
            EngineError,
            match=(
                r"motion\.shad\.jitter\(\) cannot be combined "
                r"with motion\.shad\.\*"
            ),
        ):
            motion.shad.jitter(1, 1, 1, 1, 100)

    def test_shad_jitter_builds_auto_marker_and_transforms(self) -> None:
        env = DummyEnv(line=make_generated_line())
        result = motion_namespace(env).shad.jitter(1, 2, 0, 1, 100, 7)

        assert result.startswith(SHAD_AUTO_MARKER)
        assert r"\t(0,0," in result

    def test_shad_jitter_rejects_invalid_inputs(self) -> None:
        env = DummyEnv(line=make_generated_line())
        motion = motion_namespace(env)

        with pytest.raises(
            EngineError,
            match=r"motion\.shad\.jitter\(\) expects integer",
        ):
            motion.shad.jitter(1, 1, 1, 1, 100, 0.5)

        with pytest.raises(
            EngineError,
            match=r"motion\.shad\.jitter\(\) period must be >= 0",
        ):
            motion.shad.jitter(1, 1, 1, 1, -1)

    def test_shad_positional_motion_rejects_existing_pos_and_move_tags(
        self,
    ) -> None:
        pos_env = DummyEnv(
            line=GeneratedLine.from_event(
                make_event(r"{\pos(640,360)\k20}go{\k30}al"),
                make_style(),
            )
        )
        move_env = DummyEnv(
            line=GeneratedLine.from_event(
                make_event(r"{\move(0,0,100,100)\k20}go{\k30}al"),
                make_style(),
            )
        )

        with pytest.raises(
            EngineError,
            match=(
                r"motion\.shad\.arc\(\) cannot be combined "
                r"with \\pos or \\move"
            ),
        ):
            motion_namespace(pos_env).shad.arc(640, 360, 640, 360)

        with pytest.raises(
            EngineError,
            match=(
                r"motion\.shad\.arc\(\) cannot be combined "
                r"with \\pos or \\move"
            ),
        ):
            motion_namespace(move_env).shad.arc(640, 360, 640, 360)

    def test_shad_jitter_allows_existing_pos_but_rejects_move_tags(
        self,
    ) -> None:
        pos_env = DummyEnv(
            line=GeneratedLine.from_event(
                make_event(r"{\pos(640,360)\k20}go{\k30}al"),
                make_style(),
            )
        )
        move_env = DummyEnv(
            line=GeneratedLine.from_event(
                make_event(r"{\move(0,0,100,100)\k20}go{\k30}al"),
                make_style(),
            )
        )

        pos_result = motion_namespace(pos_env).shad.jitter(1, 1, 1, 1, 100)
        assert pos_result.startswith(SHAD_AUTO_MARKER)
        with pytest.raises(
            EngineError,
            match=r"motion\.shad\.jitter\(\) cannot be combined with \\move",
        ):
            motion_namespace(move_env).shad.jitter(1, 1, 1, 1, 100)

    def test_fbf_effects_queue_requests(self) -> None:
        env = DummyEnv(line=make_generated_line())
        motion = motion_namespace(env)

        assert motion.fbf.jitter(3, 4, 5, 6, 100, 7) == ""
        assert env.line is not None
        assert env.line.expansion_requests == [
            QueuedEventExpansion(
                label="motion.fbf.jitter()",
                phase="motion_fbf",
                expander=JitterFbfRequest(
                    x=640.0,
                    y=360.0,
                    left=3,
                    right=4,
                    up=5,
                    down=6,
                    period=100,
                    seed=7,
                ),
            )
        ]

        env.line.expansion_requests.clear()
        motion.fbf.arc(100, 400, 800, 400, 0, 180, 50, 100)
        assert env.line.expansion_requests == [
            QueuedEventExpansion(
                label="motion.fbf.arc()",
                phase="motion_fbf",
                expander=ArcFbfRequest(
                    100,
                    400,
                    800,
                    400,
                    0,
                    180,
                    50,
                    100,
                ),
            )
        ]

        env.line.expansion_requests.clear()
        motion.fbf.bezier((100, 600), (500, 100), (900, 600))
        assert env.line.expansion_requests == [
            QueuedEventExpansion(
                label="motion.fbf.bezier()",
                phase="motion_fbf",
                expander=BezierFbfRequest(((100, 600), (500, 100), (900, 600))),
            )
        ]

        env.line.expansion_requests.clear()
        motion.fbf.spring(100, 400, 800, 400)
        assert env.line.expansion_requests == [
            QueuedEventExpansion(
                label="motion.fbf.spring()",
                phase="motion_fbf",
                expander=SpringFbfRequest(
                    100,
                    400,
                    800,
                    400,
                ),
            )
        ]

        env.line.expansion_requests.clear()
        motion.fbf.wave(100, 900, 400)
        assert env.line.expansion_requests == [
            QueuedEventExpansion(
                label="motion.fbf.wave()",
                phase="motion_fbf",
                expander=WaveFbfRequest(100, 900, 400),
            )
        ]

    def test_fbf_motion_keeps_gradient_phase_order(self) -> None:
        env = DummyEnv(line=make_generated_line())
        assert env.line is not None
        env.line.expansion_requests.append(
            QueuedEventExpansion(
                label="gradient.make()",
                phase="gradient",
                expander=DummyExpander(),
            )
        )

        motion_namespace(env).fbf.arc(100, 400, 800, 400)

        assert [item.phase for item in env.line.expansion_requests] == [
            "motion_fbf",
            "gradient",
        ]

    def test_fbf_motion_requires_framerate(self) -> None:
        env = DummyEnv(line=make_generated_line(), metadata=Metadata(1280, 720))
        motion = motion_namespace(env)

        with pytest.raises(
            EngineError,
            match=(
                r"motion\.fbf\.arc\(\) requires explicit timecodes "
                r"or PlaybackFPS"
            ),
        ):
            motion.fbf.arc(100, 400, 800, 400)

    def test_fbf_motion_rejects_multiple_expansions(self) -> None:
        env = DummyEnv(line=make_generated_line())
        motion = motion_namespace(env)

        motion.fbf.arc(100, 400, 800, 400)

        with pytest.raises(
            EngineError,
            match=r"motion\.fbf\.wave\(\) cannot be combined",
        ):
            motion.fbf.wave(100, 900, 400)

    def test_fbf_motion_rejects_existing_pos_and_move_tags(self) -> None:
        pos_env = DummyEnv(
            line=GeneratedLine.from_event(
                make_event(r"{\pos(640,360)\k20}go{\k30}al"),
                make_style(),
            )
        )
        move_env = DummyEnv(
            line=GeneratedLine.from_event(
                make_event(r"{\move(0,0,100,100)\k20}go{\k30}al"),
                make_style(),
            )
        )

        with pytest.raises(
            EngineError,
            match=(
                r"motion\.fbf\.arc\(\) cannot be combined "
                r"with \\pos or \\move"
            ),
        ):
            motion_namespace(pos_env).fbf.arc(100, 400, 800, 400)

        with pytest.raises(
            EngineError,
            match=(
                r"motion\.fbf\.arc\(\) cannot be combined "
                r"with \\pos or \\move"
            ),
        ):
            motion_namespace(move_env).fbf.arc(100, 400, 800, 400)

    def test_motion_backends_cannot_be_combined(self) -> None:
        env = DummyEnv(line=make_generated_line())
        motion = motion_namespace(env)

        motion.shad.jitter(1, 1, 1, 1, 100)

        with pytest.raises(
            EngineError,
            match=r"motion\.fbf\.arc\(\) cannot be combined with motion\.shad",
        ):
            motion.fbf.arc(100, 400, 800, 400)


class TestMotionEngineIntegration:
    def test_shad_motion_is_finalized_into_real_ass_tags(self) -> None:
        engine = build_engine()
        template = TemplateDeclaration(
            body=TemplateBody(
                r"{!motion.shad.arc(line.x,line.y,line.x,line.y,0,0,50,50)!}"
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

        assert len(result) == 1
        assert SHAD_AUTO_MARKER not in result[0].text
        assert SHAD_SETUP_FRAGMENT in result[0].text
        assert r"\4c&HFFFFFF&" in result[0].text
        assert r"\pos(690,710)" in result[0].text
        assert r"\t(0,0,\xshad0.001\yshad0)" in result[0].text
        assert r"\t(" in result[0].text

    def test_shad_motion_rejects_pos_and_move_added_by_template(self) -> None:
        engine = build_engine()
        pos_template = TemplateDeclaration(
            body=TemplateBody(
                r"{\pos(640,360)!motion.shad.arc(line.x,line.y,line.x,line.y,0,0,50,50)!}"
            ),
            scope=Scope.LINE,
            modifiers=TemplateModifiers(),
        )
        move_template = TemplateDeclaration(
            body=TemplateBody(
                r"{\move(0,0,100,100)!motion.shad.arc(line.x,line.y,line.x,line.y,0,0,50,50)!}"
            ),
            scope=Scope.LINE,
            modifiers=TemplateModifiers(),
        )

        with pytest.raises(
            TemplateRuntimeError,
            match=(
                r"motion\.shad\.arc\(\) cannot be combined "
                r"with \\pos or \\move"
            ),
        ):
            engine.apply(
                [make_event()],
                ParsedDeclarations(line=[pos_template]),
                Metadata(
                    res_x=1280,
                    res_y=720,
                    raw={"PlaybackFPS": "24"},
                ),
                {"Default": make_style()},
            )

        with pytest.raises(
            TemplateRuntimeError,
            match=(
                r"motion\.shad\.arc\(\) cannot be combined "
                r"with \\pos or \\move"
            ),
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

    def test_shad_jitter_allows_pos_added_by_template(self) -> None:
        engine = build_engine()
        template = TemplateDeclaration(
            body=TemplateBody(
                r"{\pos(640,360)"
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

        assert len(result) == 1
        assert r"\pos(640,360)" in result[0].text
        assert r"\t(0,0," in result[0].text

    def test_shad_jitter_rejects_move_added_by_template(self) -> None:
        engine = build_engine()
        template = TemplateDeclaration(
            body=TemplateBody(
                r"{\move(600,360,680,360)"
                r"!motion.shad.jitter(20,20,20,20,100)!}"
            ),
            scope=Scope.LINE,
            modifiers=TemplateModifiers(),
        )

        with pytest.raises(
            EngineError,
            match=r"motion\.shad\.jitter\(\) cannot be combined with \\move",
        ):
            engine.apply(
                [make_event()],
                ParsedDeclarations(line=[template]),
                Metadata(
                    res_x=1280,
                    res_y=720,
                    raw={"PlaybackFPS": "24"},
                ),
                {"Default": make_style()},
            )

    def test_fbf_motion_expands_one_template_into_many_events(self) -> None:
        engine = build_engine()
        template = TemplateDeclaration(
            body=TemplateBody(r"{!motion.fbf.wave(600,680,360,40,1.0)!}"),
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
        assert all(r"\pos(" in event.text for event in result)
        assert all(event.effect == "fx" for event in result)
        assert all(event.end_time > event.start_time for event in result)

    def test_fbf_motion_without_framerate_fails_through_engine(self) -> None:
        engine = build_engine()
        template = TemplateDeclaration(
            body=TemplateBody(r"{!motion.fbf.arc(100,400,800,400)!}"),
            scope=Scope.LINE,
            modifiers=TemplateModifiers(),
        )

        with pytest.raises(
            EngineError,
            match=(
                r"motion\.fbf\.arc\(\) requires explicit timecodes "
                r"or PlaybackFPS"
            ),
        ):
            engine.apply(
                [make_event()],
                ParsedDeclarations(line=[template]),
                Metadata(res_x=1280, res_y=720),
                {"Default": make_style()},
            )

    def test_fbf_motion_output_replaces_timing_with_static_pos(self) -> None:
        engine = build_engine()
        template = TemplateDeclaration(
            body=TemplateBody(
                r"{\bord0!motion.fbf.arc(640,360,640,360,0,180,50,50)!}"
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
        assert all(r"\pos(" in event.text for event in result)
        assert not any(r"\move(" in event.text for event in result)
        positions: set[str] = set()
        for event in result:
            match = re.search(r"\\pos\(([^)]*)\)", event.text)
            assert match is not None
            positions.add(match.group(1))
        assert len(positions) > 1

    def test_fbf_motion_rejects_pos_added_after_call(self) -> None:
        engine = build_engine()
        template = TemplateDeclaration(
            body=TemplateBody(
                r"{!motion.fbf.arc(640,360,640,360,0,180,50,50)!"
                r"\pos(640,360)}"
            ),
            scope=Scope.LINE,
            modifiers=TemplateModifiers(),
        )

        with pytest.raises(
            EngineError,
            match=(
                r"motion\.fbf\.\* cannot be combined "
                r"with \\pos or \\move"
            ),
        ):
            engine.apply(
                [make_event()],
                ParsedDeclarations(line=[template]),
                Metadata(
                    res_x=1280,
                    res_y=720,
                    raw={"PlaybackFPS": "24"},
                ),
                {"Default": make_style()},
            )

    def test_motion_cannot_be_used_in_mixin(self) -> None:
        engine = build_engine()
        template = TemplateDeclaration(
            body=TemplateBody(r"{\an5}"),
            scope=Scope.LINE,
            modifiers=TemplateModifiers(),
        )
        mixin = MixinDeclaration(
            body=MixinBody(r"{!motion.shad.jitter(1,1,1,1,100)!}"),
            scope=Scope.LINE,
            modifiers=MixinModifiers(),
        )

        with pytest.raises(
            EngineError,
            match=r"motion\.\* can only be used in template bodies",
        ):
            engine.apply(
                [make_event()],
                ParsedDeclarations(line=[template], mixin_line=[mixin]),
                Metadata(
                    res_x=1280,
                    res_y=720,
                    raw={"PlaybackFPS": "24"},
                ),
                {"Default": make_style()},
            )
