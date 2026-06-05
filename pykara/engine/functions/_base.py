"""Shared function registry infrastructure for the execution environment."""

from __future__ import annotations

from collections.abc import Callable
from types import SimpleNamespace
from typing import ClassVar, Protocol, cast, runtime_checkable


class Function(Protocol):
    """Protocol implemented by every callable exposed to template code."""

    name: ClassVar[str]
    aliases: ClassVar[tuple[str, ...]] = ()
    applicable_to: ClassVar[frozenset[str]]


@runtime_checkable
class BoundNamespaceFunction(Function, Protocol):
    """Function that exposes an env-bound object instead of a callable."""

    def build_bound(self, env: object) -> object: ...


class FunctionRegistry:
    """Keep a runtime-extensible mapping of names and aliases to functions."""

    def __init__(self) -> None:
        self._functions: dict[str, Function] = {}

    def register(self, function: Function) -> None:
        """Register one function under its name and aliases."""
        self._functions[function.name] = function
        for alias in function.aliases:
            self._functions[alias] = function

    def build_namespace(
        self,
        env: object,
        declaration: str,
    ) -> dict[str, object]:
        """Return env-bound callables available to the requested declaration."""
        namespace: dict[str, object] = {}
        for name, function in self._functions.items():
            if declaration not in function.applicable_to:
                continue
            if hasattr(function, "build_bound"):
                bound = cast(
                    BoundNamespaceFunction,
                    function,
                ).build_bound(env)
            else:
                bound = self._bind(function, env)
            if "." not in name:
                namespace[name] = bound
                continue

            namespace_name, member_name = name.split(".", 1)
            container = namespace.setdefault(namespace_name, SimpleNamespace())
            if not isinstance(container, SimpleNamespace):
                continue
            setattr(container, member_name, bound)
        return namespace

    def _bind(self, function: Function, env: object) -> Callable[..., object]:
        callable_function = cast(Callable[..., object], function)

        def bound(*args: object, **kwargs: object) -> object:
            return callable_function(env, *args, **kwargs)

        return bound
