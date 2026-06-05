"""Public exports for template declarations."""

from pykara.declaration._shared import ModifierRegistry
from pykara.declaration.template.body import TemplateBody
from pykara.declaration.template.modifiers import (
    FxModifier,
    LoopDescriptor,
    LoopModifier,
    NoBlankModifier,
    NoMergeModifier,
    NoTextModifier,
    StylesModifier,
    TemplateModifiers,
    UnlessModifier,
    WhenModifier,
)

TEMPLATE_MODIFIER_REGISTRY: ModifierRegistry[TemplateModifiers] = (
    ModifierRegistry(default=TemplateModifiers())
)

for _handler in (
    LoopModifier(),
    NoBlankModifier(),
    NoMergeModifier(),
    NoTextModifier(),
    FxModifier(),
    StylesModifier(),
    WhenModifier(),
    UnlessModifier(),
):
    TEMPLATE_MODIFIER_REGISTRY.register(_handler)

__all__ = [
    "TEMPLATE_MODIFIER_REGISTRY",
    "FxModifier",
    "LoopDescriptor",
    "LoopModifier",
    "NoBlankModifier",
    "NoMergeModifier",
    "NoTextModifier",
    "StylesModifier",
    "TemplateBody",
    "TemplateModifiers",
    "UnlessModifier",
    "WhenModifier",
]
