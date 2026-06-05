"""Shared key-value store functions."""

from __future__ import annotations

from collections.abc import MutableMapping, MutableSet
from typing import ClassVar, Protocol, cast

from pykara.errors import BoundMethodInExpressionError, LockedStoreKeyError


class _StoreEnvironment(Protocol):
    store: MutableMapping[str, object]
    locked_store_keys: MutableSet[str]


def _raise_if_callable(function_name: str, key: str, value: object) -> None:
    if callable(value):
        raise BoundMethodInExpressionError(
            expression=f'{function_name}("{key}", ...)',
            result_type=type(value).__name__,
        )


class GetFunction:
    """Read one value from the shared store."""

    name: ClassVar[str] = "get"
    aliases: ClassVar[tuple[str, ...]] = ()
    applicable_to: ClassVar[frozenset[str]] = frozenset({"template"})

    def __call__(
        self,
        env: object,
        key: str,
        default_value: object = None,
    ) -> object:
        typed_env = cast(_StoreEnvironment, env)
        return typed_env.store.get(key, default_value)


class PutFunction:
    """Write one value into the shared store."""

    name: ClassVar[str] = "put"
    aliases: ClassVar[tuple[str, ...]] = ()
    applicable_to: ClassVar[frozenset[str]] = frozenset({"template"})

    def __call__(self, env: object, key: str, value: object) -> object:
        typed_env = cast(_StoreEnvironment, env)
        if key in typed_env.locked_store_keys:
            raise LockedStoreKeyError(key)
        _raise_if_callable("put", key, value)
        typed_env.store[key] = value
        return value


class LockFunction:
    """Write one value into the shared store and lock the key."""

    name: ClassVar[str] = "lock"
    aliases: ClassVar[tuple[str, ...]] = ()
    applicable_to: ClassVar[frozenset[str]] = frozenset({"template"})

    def __call__(self, env: object, key: str, value: object) -> object:
        typed_env = cast(_StoreEnvironment, env)
        if key not in typed_env.store:
            _raise_if_callable("lock", key, value)
            typed_env.store[key] = value
        typed_env.locked_store_keys.add(key)
        return typed_env.store[key]
