"""Layer namespace helpers."""

from __future__ import annotations

from typing import ClassVar, Protocol, cast


class _LayerLine(Protocol):
    layer: int


class _LayerEnvironment(Protocol):
    line: _LayerLine


class LayerSetFunction:
    """Set the layer on the generated line."""

    name: ClassVar[str] = "layer.set"
    aliases: ClassVar[tuple[str, ...]] = ()
    applicable_to: ClassVar[frozenset[str]] = frozenset({"template", "code"})

    def __call__(self, env: object, value: int) -> None:
        typed_env = cast(_LayerEnvironment, env)
        typed_env.line.layer = value
        return None
