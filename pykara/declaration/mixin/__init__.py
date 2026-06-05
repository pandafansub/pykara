"""Public exports for mixin declarations."""

from pykara.declaration._shared import ModifierRegistry
from pykara.declaration.mixin.body import MixinBody
from pykara.declaration.mixin.modifiers import (
    ForModifier,
    LayerModifier,
    MixinFxModifier,
    MixinModifiers,
    MixinUnlessModifier,
    MixinWhenModifier,
    PrependModifier,
)

MIXIN_MODIFIER_REGISTRY: ModifierRegistry[MixinModifiers] = ModifierRegistry(
    default=MixinModifiers()
)

for _handler in (
    PrependModifier(),
    LayerModifier(),
    ForModifier(),
    MixinFxModifier(),
    MixinWhenModifier(),
    MixinUnlessModifier(),
):
    MIXIN_MODIFIER_REGISTRY.register(_handler)

__all__ = [
    "MIXIN_MODIFIER_REGISTRY",
    "ForModifier",
    "LayerModifier",
    "MixinBody",
    "MixinFxModifier",
    "MixinModifiers",
    "MixinUnlessModifier",
    "MixinWhenModifier",
    "PrependModifier",
]
