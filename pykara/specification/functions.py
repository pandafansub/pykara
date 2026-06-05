"""Function-level contracts for the execution namespace."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FunctionSpecification:
    """Describe one callable or dotted function available to templates."""

    name: str
    signature: str
    category: str
    description: str
    applicable_to: frozenset[str]


FUNCTION_SPECIFICATIONS: dict[str, FunctionSpecification] = {
    "retime": FunctionSpecification(
        "retime",
        "retime.<target>(start_offset: int = 0, end_offset: int = 0) -> None",
        "engine",
        (
            "Namespace with targets line, preline, postline, syl, presyl, "
            "postsyl, start2syl, and syl2end. Presets are available as "
            "retime.<target>.<preset>(start_offset, end_offset)."
        ),
        frozenset({"template"}),
    ),
    "motion": FunctionSpecification(
        "motion",
        "motion.shad.<effect>(...) -> str | motion.fbf.<effect>(...) -> str",
        "engine",
        (
            "Namespace with shadow-trick motion under motion.shad and "
            "frame-baked motion under motion.fbf. Effects include jitter, "
            "arc, bezier, spring, and wave."
        ),
        frozenset({"template"}),
    ),
    "gradient": FunctionSpecification(
        "gradient",
        "gradient.make(colors, step=2, direction='top-bottom') -> str",
        "engine",
        (
            "Queue one clip-based frame-baked gradient expansion for the "
            "current rendered line."
        ),
        frozenset({"template"}),
    ),
    "layer.set": FunctionSpecification(
        "layer.set",
        "layer.set(value: int) -> None",
        "engine",
        "Set the output line layer.",
        frozenset({"template", "code"}),
    ),
    "get": FunctionSpecification(
        "get",
        "get(key: str, default_value: object = None) -> object",
        "engine",
        "Read one value from the shared store.",
        frozenset({"template"}),
    ),
    "put": FunctionSpecification(
        "put",
        "put(key: str, value: object) -> object",
        "engine",
        "Store one value in the shared store.",
        frozenset({"template"}),
    ),
    "lock": FunctionSpecification(
        "lock",
        "lock(key: str, value: object) -> object",
        "engine",
        "Store one value and prevent later changes to the key.",
        frozenset({"template"}),
    ),
    "color.rgb_to_ass": FunctionSpecification(
        "color.rgb_to_ass",
        "color.rgb_to_ass(red: int, green: int, blue: int) -> str",
        "color",
        "Build an ASS color string in override format.",
        frozenset({"template", "code"}),
    ),
    "color.alpha": FunctionSpecification(
        "color.alpha",
        "color.alpha(alpha: int) -> str",
        "color",
        "Build an ASS alpha string.",
        frozenset({"template", "code"}),
    ),
    "color.interpolate": FunctionSpecification(
        "color.interpolate",
        (
            "color.interpolate("
            "progress: float, start_color: str, end_color: str"
            ") -> str"
        ),
        "color",
        "Interpolate between two colors at progress in [0, 1].",
        frozenset({"template", "code"}),
    ),
    "color.hsv_to_rgb": FunctionSpecification(
        "color.hsv_to_rgb",
        "color.hsv_to_rgb(hue: float, saturation: float, value: float)",
        "color",
        "Convert HSV components to RGB components.",
        frozenset({"template", "code"}),
    ),
    "color.hsl_to_rgb": FunctionSpecification(
        "color.hsl_to_rgb",
        (
            "color.hsl_to_rgb("
            "hue: float, saturation: float, luminance: float"
            ") -> tuple[int, int, int]"
        ),
        "color",
        "Convert HSL components to RGB byte components.",
        frozenset({"template", "code"}),
    ),
    "coord.polar": FunctionSpecification(
        "coord.polar",
        "coord.polar(angle: float, radius: float, axis: str | None = None)",
        "geometry",
        "Return screen-space polar coordinates, with positive angles upward.",
        frozenset({"template", "code"}),
    ),
    "coord.circular_spread": FunctionSpecification(
        "coord.circular_spread",
        "coord.circular_spread(n: int, rotate: int = 0)",
        "geometry",
        "Return unit-circle points in a spatially spread order.",
        frozenset({"template", "code"}),
    ),
    "coord.random_spread": FunctionSpecification(
        "coord.random_spread",
        (
            "coord.random_spread("
            "n: int, spread: int = 30, min_dist: float = 14, "
            "min_radius: float = 8, attempts: int = 300"
            ")"
        ),
        "geometry",
        "Return random points that are not too close to each other.",
        frozenset({"template", "code"}),
    ),
    "shape.rotate": FunctionSpecification(
        "shape.rotate",
        "shape.rotate(shape: str, angle: float, origin_x=0, origin_y=0)",
        "geometry",
        "Rotate every point in an ASS drawing shape.",
        frozenset({"template", "code"}),
    ),
    "shape.center_at": FunctionSpecification(
        "shape.center_at",
        "shape.center_at(shape: str, x: float = 0, y: float = 0) -> str",
        "geometry",
        "Move a shape so its bounding-box center is at x,y.",
        frozenset({"template", "code"}),
    ),
    "shape.displace": FunctionSpecification(
        "shape.displace",
        "shape.displace(shape: str, offset_x: float, offset_y: float) -> str",
        "geometry",
        "Displace every point in an ASS drawing shape.",
        frozenset({"template", "code"}),
    ),
    "shape.split_clip": FunctionSpecification(
        "shape.split_clip",
        "shape.split_clip(width: float, angle=0, x=0, y=0, height=None) -> str",
        "geometry",
        "Build a rotated split clipping shape centered at x,y.",
        frozenset({"template", "code"}),
    ),
    "math.floor": FunctionSpecification(
        "math.floor",
        "math.floor(x: float) -> int",
        "math",
        "Round down.",
        frozenset({"template", "code"}),
    ),
    "math.ceil": FunctionSpecification(
        "math.ceil",
        "math.ceil(x: float) -> int",
        "math",
        "Round up.",
        frozenset({"template", "code"}),
    ),
    "math.sqrt": FunctionSpecification(
        "math.sqrt",
        "math.sqrt(x: float) -> float",
        "math",
        "Return the square root of x.",
        frozenset({"template", "code"}),
    ),
    "math.fabs": FunctionSpecification(
        "math.fabs",
        "math.fabs(x: float) -> float",
        "math",
        "Return the absolute value of x as a float.",
        frozenset({"template", "code"}),
    ),
    "math.sin": FunctionSpecification(
        "math.sin",
        "math.sin(x: float) -> float",
        "math",
        "Return the sine of x in radians.",
        frozenset({"template", "code"}),
    ),
    "math.cos": FunctionSpecification(
        "math.cos",
        "math.cos(x: float) -> float",
        "math",
        "Return the cosine of x in radians.",
        frozenset({"template", "code"}),
    ),
    "math.radians": FunctionSpecification(
        "math.radians",
        "math.radians(x: float) -> float",
        "math",
        "Convert an angle from degrees to radians.",
        frozenset({"template", "code"}),
    ),
    "random.random": FunctionSpecification(
        "random.random",
        "random.random() -> float",
        "random",
        "Return the next pseudo-random float in the range [0.0, 1.0).",
        frozenset({"template", "code"}),
    ),
    "random.choice": FunctionSpecification(
        "random.choice",
        "random.choice(seq)",
        "random",
        "Return a pseudo-random element from the non-empty sequence seq.",
        frozenset({"template", "code"}),
    ),
    "random.choice_no_repeat": FunctionSpecification(
        "random.choice_no_repeat",
        "random.choice_no_repeat(seq)",
        "random",
        "Return a pseudo-random element, trying not to repeat the previous "
        "value returned by the same expression or code block.",
        frozenset({"template", "code"}),
    ),
    "random.randint": FunctionSpecification(
        "random.randint",
        "random.randint(a: int, b: int) -> int",
        "random",
        "Return a pseudo-random integer N such that a <= N <= b.",
        frozenset({"template", "code"}),
    ),
}

EXPOSED_MODULES: frozenset[str] = frozenset(
    {"color", "coord", "layer", "math", "random", "shape"}
)
