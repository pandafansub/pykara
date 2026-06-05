"""Public exports for code declarations."""

from pykara.declaration._shared import ModifierRegistry
from pykara.declaration.code.body import CodeBody
from pykara.declaration.code.modifiers import CodeModifiers, CodeStylesModifier

CODE_MODIFIER_REGISTRY: ModifierRegistry[CodeModifiers] = ModifierRegistry(
    default=CodeModifiers()
)

for _handler in (CodeStylesModifier(),):
    CODE_MODIFIER_REGISTRY.register(_handler)

__all__ = [
    "CODE_MODIFIER_REGISTRY",
    "CodeBody",
    "CodeModifiers",
    "CodeStylesModifier",
]
