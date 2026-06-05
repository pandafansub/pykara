"""Ready-to-use named resources exposed to inline expressions."""

from __future__ import annotations

from pykara.errors import EngineError

from .colors import AssetColors
from .shapes import AssetShapes


class Assets:
    """Root asset catalog exposed to expressions."""

    __slots__ = ("colors", "shapes")

    def __init__(self) -> None:
        self.colors = AssetColors()
        self.shapes = AssetShapes()

    def __str__(self) -> str:
        raise EngineError(
            "assets is incomplete; choose assets.colors or assets.shapes"
        )


assets = Assets()

__all__ = ["AssetColors", "AssetShapes", "Assets", "assets"]
