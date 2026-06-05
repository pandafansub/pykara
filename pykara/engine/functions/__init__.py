"""Public exports for execution namespace functions."""

from pykara.engine.functions._base import Function, FunctionRegistry
from pykara.engine.functions.color import (
    AssAlphaFunction,
    AssColorFunction,
    HslToRgbFunction,
    HsvToRgbFunction,
    InterpolateColorFunction,
)
from pykara.engine.functions.geometry import (
    CircularSpreadFunction,
    PolarFunction,
    RandomSpreadFunction,
    ShapeCenterAtFunction,
    ShapeDisplaceFunction,
    ShapeRotateFunction,
    ShapeSplitClipFunction,
)
from pykara.engine.functions.gradient import GradientFunction
from pykara.engine.functions.layer import LayerSetFunction
from pykara.engine.functions.motion import MotionFunction
from pykara.engine.functions.retime import RETIME_MODES, RetimeFunction
from pykara.engine.functions.store import GetFunction, LockFunction, PutFunction

FUNCTION_REGISTRY = FunctionRegistry()
for _function in (
    RetimeFunction(),
    MotionFunction(),
    GradientFunction(),
    LayerSetFunction(),
    GetFunction(),
    PutFunction(),
    LockFunction(),
    AssColorFunction(),
    AssAlphaFunction(),
    InterpolateColorFunction(),
    HsvToRgbFunction(),
    HslToRgbFunction(),
    PolarFunction(),
    CircularSpreadFunction(),
    RandomSpreadFunction(),
    ShapeRotateFunction(),
    ShapeCenterAtFunction(),
    ShapeDisplaceFunction(),
    ShapeSplitClipFunction(),
):
    FUNCTION_REGISTRY.register(_function)

__all__ = [
    "FUNCTION_REGISTRY",
    "RETIME_MODES",
    "AssAlphaFunction",
    "AssColorFunction",
    "CircularSpreadFunction",
    "Function",
    "FunctionRegistry",
    "GetFunction",
    "GradientFunction",
    "HslToRgbFunction",
    "HsvToRgbFunction",
    "InterpolateColorFunction",
    "LayerSetFunction",
    "LockFunction",
    "MotionFunction",
    "PolarFunction",
    "PutFunction",
    "RandomSpreadFunction",
    "RetimeFunction",
    "ShapeCenterAtFunction",
    "ShapeDisplaceFunction",
    "ShapeRotateFunction",
    "ShapeSplitClipFunction",
]
