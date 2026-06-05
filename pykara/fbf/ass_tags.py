"""ASS tag parsing, formatting, interpolation and state for FBF motion."""

from __future__ import annotations

import math
import re
from functools import lru_cache
from typing import cast

from pykara.data import Event
from pykara.errors import PykaraError

MoveTag = tuple[float, float, float, float, float | None, float | None]
FadTag = tuple[str, float, float]
FadeTag = tuple[str, float, float, float, float, float, float, float]
AnyFadeTag = FadTag | FadeTag
TagValue = float | str | list[float]
MotionStateValue = TagValue | MoveTag | AnyFadeTag | int
MotionState = dict[str, MotionStateValue]
LINE_DURATION_KEY = "_line_duration"


def math_clamp(value: float, lower: float, upper: float) -> float:
    return min(max(value, lower), upper)


def math_round(value: float, decimals: int = 3) -> float:
    factor = 10 ** math.floor(decimals)
    rounded = math.floor(value * factor + 0.5)
    integer = math.floor(rounded + 0.5)
    return rounded / factor if decimals >= 1 else integer


def math_lerp(t: float, start: float, end: float) -> float:
    t = math_clamp(t, 0.0, 1.0)
    return (1.0 - t) * start + t * end


COLOR_TAGS = {"c", "2c", "3c", "4c"}
ALPHA_TAGS = {"alpha", "1a", "2a", "3a", "4a"}
CLIP_TAGS = {"clip", "iclip"}
NUMERIC_TAGS = {
    "fs",
    "fscx",
    "fscy",
    "fsp",
    "bord",
    "shad",
    "frz",
    "be",
    "blur",
    "xbord",
    "ybord",
    "xshad",
    "yshad",
    "frx",
    "fry",
    "fax",
    "fay",
}


def interpolate_alpha(t: float, start: str, end: str) -> str:
    start_value = _parse_ass_alpha(start)
    end_value = _parse_ass_alpha(end)
    if start_value is None or end_value is None:
        return start
    return f"&H{round(math_lerp(t, start_value, end_value)):02X}&"


def interpolate_color(t: float, start: str, end: str) -> str:
    if start == end:
        return start
    start_triplet = _parse_ass_color(start)
    end_triplet = _parse_ass_color(end)
    if start_triplet is None or end_triplet is None:
        return start
    values = [
        round(
            math_lerp(
                t,
                start_triplet[index],
                end_triplet[index],
            )
        )
        for index in range(3)
    ]
    return f"&H{values[0]:02X}{values[1]:02X}{values[2]:02X}&"


def interpolate_shape(t: float, start: str, end: str) -> str:
    numbers_start = [float(value) for value in re.findall(r"-?\d[\d.]*", start)]
    numbers_end = [float(value) for value in re.findall(r"-?\d[\d.]*", end)]
    if len(numbers_start) != len(numbers_end):
        raise PykaraError(
            "clip shape interpolation requires matching point counts"
        )

    index = 0

    def replace_number(_match: re.Match[str]) -> str:
        nonlocal index
        value = math_round(
            math_lerp(t, numbers_start[index], numbers_end[index]), 2
        )
        index += 1
        return _format_ass_number(value)

    return re.sub(r"-?\d[\d.]*", replace_number, start)


def interpolate_value(
    tag_name: str,
    t: float,
    start_value: TagValue,
    end_value: TagValue,
) -> TagValue:
    if tag_name in COLOR_TAGS:
        return interpolate_color(t, str(start_value), str(end_value))
    if tag_name in ALPHA_TAGS:
        return interpolate_alpha(t, str(start_value), str(end_value))
    if tag_name in NUMERIC_TAGS:
        start_number = _numeric_tag_value(start_value)
        end_number = _numeric_tag_value(end_value)
        return math_round(math_lerp(t, start_number, end_number), 2)
    if tag_name in CLIP_TAGS:
        if (
            isinstance(start_value, list)
            and isinstance(end_value, list)
            and len(start_value) == 4
            and len(end_value) == 4
        ):
            return [
                math_round(
                    math_lerp(t, start_value[index], end_value[index]), 2
                )
                for index in range(4)
            ]
        return interpolate_shape(t, str(start_value), str(end_value))
    return start_value


def get_time_in_interval(
    current_time: float,
    start_time: float,
    end_time: float,
    accel: float = 1.0,
) -> float:
    if current_time < start_time:
        return 0.0
    if current_time >= end_time:
        return 1.0
    return (current_time - start_time) ** accel / (
        end_time - start_time
    ) ** accel


@lru_cache(maxsize=8192)
def _format_ass_number(value: float | int, decimals: int = 3) -> str:
    if isinstance(value, int):
        return str(value)
    rounded = math_round(float(value), decimals)
    if rounded == int(rounded):
        return str(int(rounded))
    text = f"{rounded:.{decimals}f}".rstrip("0").rstrip(".")
    return "0" if text == "-0" else text


@lru_cache(maxsize=1024)
def _parse_ass_alpha(value: str) -> int | None:
    match = re.search(_ALPHA_VALUE_PATTERN, value)
    if match is None:
        return None
    return int(match.group(1), 16)


@lru_cache(maxsize=2048)
def _parse_ass_color(value: str) -> tuple[int, int, int] | None:
    match = re.search(
        r"[Hh]([0-9A-Fa-f]{2})([0-9A-Fa-f]{2})([0-9A-Fa-f]{2})",
        value,
    )
    if match is None:
        return None
    return (
        int(match.group(1), 16),
        int(match.group(2), 16),
        int(match.group(3), 16),
    )


@lru_cache(maxsize=8192)
def parse_t_tag(inner: str) -> tuple[float | None, float | None, float, str]:
    match = re.match(
        r"^([-\d.]*),?([-\d.]*),?([-\d.]*),?(.+)$",
        inner.strip(),
        re.DOTALL,
    )
    if match is None:
        return None, None, 1.0, inner
    first, second, third, transform = match.groups()
    if first == "" and second == "" and third == "":
        return None, None, 1.0, transform
    if first != "" and second == "" and third == "":
        return None, None, float(first), transform
    if first != "" and second != "" and third == "":
        return float(first), float(second), 1.0, transform
    return float(first), float(second), float(third), transform


_ORDERED_TAGS = (
    "iclip",
    "clip",
    "alpha",
    "1a",
    "2a",
    "3a",
    "4a",
    "2c",
    "3c",
    "4c",
    "c",
    "xbord",
    "ybord",
    "xshad",
    "yshad",
    "fscx",
    "fscy",
    "fsp",
    "frz",
    "frx",
    "fry",
    "fax",
    "fay",
    "bord",
    "shad",
    "blur",
    "be",
    "fs",
)
_TAG_PATTERNS = {
    "fs": r"\\fs\s*([\d.]+)",
    "fscx": r"\\fscx\s*(-?[\d.eE+\-]+)",
    "fscy": r"\\fscy\s*(-?[\d.eE+\-]+)",
    "fsp": r"\\fsp\s*(-?[\d.eE+\-]+)",
    "frz": r"\\frz\s*(-?[\d.eE+\-]+)",
    "frx": r"\\frx\s*(-?[\d.eE+\-]+)",
    "fry": r"\\fry\s*(-?[\d.eE+\-]+)",
    "fax": r"\\fax\s*(-?[\d.eE+\-]+)",
    "fay": r"\\fay\s*(-?[\d.eE+\-]+)",
    "bord": r"\\bord\s*([\d.]+)",
    "shad": r"\\shad\s*([\d.]+)",
    "xbord": r"\\xbord\s*(-?[\d.eE+\-]+)",
    "ybord": r"\\ybord\s*(-?[\d.eE+\-]+)",
    "xshad": r"\\xshad\s*(-?[\d.eE+\-]+)",
    "yshad": r"\\yshad\s*(-?[\d.eE+\-]+)",
    "blur": r"\\blur\s*([\d.]+)",
    "be": r"\\be\s*([\d.]+)",
    "c": r"\\c\s*(&[Hh][0-9A-Fa-f]+&?)",
    "2c": r"\\2c\s*(&[Hh][0-9A-Fa-f]+&?)",
    "3c": r"\\3c\s*(&[Hh][0-9A-Fa-f]+&?)",
    "4c": r"\\4c\s*(&[Hh][0-9A-Fa-f]+&?)",
    "alpha": r"\\alpha\s*(&[Hh][0-9A-Fa-f]+&?)",
    "1a": r"\\1a\s*(&[Hh][0-9A-Fa-f]+&?)",
    "2a": r"\\2a\s*(&[Hh][0-9A-Fa-f]+&?)",
    "3a": r"\\3a\s*(&[Hh][0-9A-Fa-f]+&?)",
    "4a": r"\\4a\s*(&[Hh][0-9A-Fa-f]+&?)",
    "clip": r"\\clip\(([^)]+)\)",
    "iclip": r"\\iclip\(([^)]+)\)",
}
_PAREN_TAG_VALUE_TEMPLATE = r"\\{tag_name}\(([^)]*)\)"
_NUMBER_PATTERN = r"-?[\d.]+"
_ALPHA_VALUE_PATTERN = r"[Hh]([0-9A-Fa-f]{2})"
_INLINE_ALPHA_TAG_PATTERN = r"\\alpha&[Hh][0-9A-Fa-f]+&?"
_TEXT_BLOCK_PATTERN = re.compile(r"(\{[^}]*\})|([^{]+)")
_OVERRIDE_BLOCK_RE = re.compile(r"\{[^}]*\}")
_TRANSFORM_PREFIX = r"\t("
_POS_TAG_RE = re.compile(r"\\pos\([^)]*\)")
_MOVE_TAG_RE = re.compile(r"\\move\([^)]*\)")
_FAD_TAG_RE = re.compile(r"\\fad\([^)]*\)")
_FADE_TAG_RE = re.compile(r"\\fade\([^)]*\)")
_INLINE_ALPHA_TAG_RE = re.compile(_INLINE_ALPHA_TAG_PATTERN)
_COMPILED_TAG_PATTERNS = {
    tag_name: re.compile(pattern) for tag_name, pattern in _TAG_PATTERNS.items()
}


@lru_cache(maxsize=8192)
def _cached_tag_value_from_block(block: str, tag_name: str) -> str | None:
    pattern = _COMPILED_TAG_PATTERNS.get(tag_name)
    if pattern is None:
        return None
    value: str | None = None
    for match in pattern.finditer(block):
        value = match.group(1)
    return value


@lru_cache(maxsize=4096)
def _cached_all_tags_from_block(block: str) -> tuple[tuple[str, str], ...]:
    extracted: list[tuple[str, str]] = []
    for tag_name in _ORDERED_TAGS:
        value = _cached_tag_value_from_block(block, tag_name)
        if value is not None:
            extracted.append((tag_name, value))
    return tuple(extracted)


@lru_cache(maxsize=4096)
def _cached_split_text_blocks(text: str) -> tuple[tuple[str, str], ...]:
    blocks: list[tuple[str, str]] = []
    tags_acc = ""
    for match in _TEXT_BLOCK_PATTERN.finditer(text):
        if match.group(1) is not None:
            tags_acc += match.group(1)
            continue
        blocks.append((tags_acc, cast(str, match.group(2))))
        tags_acc = ""
    if tags_acc:
        blocks.append((tags_acc, ""))
    return tuple(blocks)


@lru_cache(maxsize=4096)
def _cached_extract_t_tags(tags_block: str) -> tuple[tuple[str, ...], str]:
    inner_content = (
        tags_block[1:-1] if tags_block.startswith("{") else tags_block
    )
    payloads: list[str] = []
    results: list[tuple[int, int, str]] = []
    index = 0
    while index < len(inner_content):
        start = inner_content.find(_TRANSFORM_PREFIX, index)
        if start == -1:
            break
        position = start + len(_TRANSFORM_PREFIX)
        depth = 1
        while position < len(inner_content) and depth > 0:
            if inner_content[position] == "(":
                depth += 1
            elif inner_content[position] == ")":
                depth -= 1
            position += 1
        results.append((start, position, inner_content[start:position]))
        index = position

    cleaned = inner_content
    for start, end, full_transform in reversed(results):
        payloads.append(full_transform[3:-1])
        cleaned = cleaned[:start] + cleaned[end:]

    return tuple(reversed(payloads)), "{" + cleaned + "}"


def get_tag_value_from_block(block: str, tag_name: str) -> str | None:
    return _cached_tag_value_from_block(block, tag_name)


def extract_all_tags_from_block(block: str) -> dict[str, str]:
    return dict(_cached_all_tags_from_block(block))


def _extract_all_tag_items_from_block(
    block: str,
) -> tuple[tuple[str, str], ...]:
    return _cached_all_tags_from_block(block)


def coerce_value(tag_name: str, raw: str) -> TagValue:
    if tag_name in NUMERIC_TAGS:
        return float(raw)
    if tag_name in CLIP_TAGS and re.search(r"[A-Za-z]", raw) is None:
        numbers = _parse_number_list(raw)
        if len(numbers) == 4:
            return numbers
    return raw


def split_text_blocks(text: str) -> list[tuple[str, str]]:
    return list(_cached_split_text_blocks(text))


def extract_t_tags(tags_block: str) -> tuple[list[str], str]:
    payloads, cleaned = _cached_extract_t_tags(tags_block)
    return list(payloads), cleaned


def remove_tag_from_block(tags_block: str, tag_name: str) -> str:
    inner = tags_block[1:-1] if tags_block.startswith("{") else tags_block
    pattern = _COMPILED_TAG_PATTERNS.get(tag_name)
    if pattern is None:
        return tags_block
    return "{" + pattern.sub("", inner) + "}"


def _format_tag_assignment(tag_name: str, value: TagValue) -> str:
    prefix = "\\" + tag_name
    if tag_name in CLIP_TAGS:
        if isinstance(value, list):
            joined = ",".join(
                _format_ass_number(component, 2) for component in value
            )
            return f"{prefix}({joined})"
        return f"{prefix}({value})"
    if tag_name in COLOR_TAGS or tag_name in ALPHA_TAGS:
        return f"{prefix}{value}"
    if isinstance(value, float):
        return f"{prefix}{_format_ass_number(value, 2)}"
    return f"{prefix}{value}"


def replace_tag_in_block(
    tags_block: str, tag_name: str, new_value: object
) -> str:
    block = remove_tag_from_block(tags_block, tag_name)
    formatted_value = cast(TagValue, new_value)
    return (
        "{"
        + block[1:-1]
        + _format_tag_assignment(tag_name, formatted_value)
        + "}"
    )


@lru_cache(maxsize=8192)
def _stripped_block_inner(tags_block: str, tag_names: tuple[str, ...]) -> str:
    inner = tags_block[1:-1] if tags_block.startswith("{") else tags_block
    for tag_name in tag_names:
        pattern = _COMPILED_TAG_PATTERNS.get(tag_name)
        if pattern is None:
            continue
        inner = pattern.sub("", inner)
    return inner


def _rebuild_block(
    tags_block: str,
    tag_names: tuple[str, ...],
    assignments: list[str],
    suffix: str = "",
) -> str:
    return (
        "{"
        + _stripped_block_inner(tags_block, tag_names)
        + "".join(assignments)
        + suffix
        + "}"
    )


def remove_fad_or_fade(tags_block: str) -> str:
    inner = tags_block[1:-1] if tags_block.startswith("{") else tags_block
    inner = _FAD_TAG_RE.sub("", inner)
    inner = _FADE_TAG_RE.sub("", inner)
    return "{" + inner + "}"


def remove_move(tags_block: str) -> str:
    inner = tags_block[1:-1] if tags_block.startswith("{") else tags_block
    return "{" + _MOVE_TAG_RE.sub("", inner) + "}"


def _parse_number_list(raw: str) -> list[float]:
    return [float(value) for value in re.findall(_NUMBER_PATTERN, raw)]


def _extract_parenthesized_numbers(
    block: str, tag_name: str
) -> list[float] | None:
    pattern = _PAREN_TAG_VALUE_TEMPLATE.format(tag_name=tag_name)
    match = re.search(pattern, block)
    if match is None:
        return None
    return _parse_number_list(match.group(1))


def _relative_step_window(
    step_start_ms: float,
    step_end_ms: float,
    line_start_ms: int,
) -> tuple[float, float, float]:
    step_start = round_line_time(step_start_ms - line_start_ms)
    step_end = round_line_time(step_end_ms - line_start_ms)
    return step_start, step_end, step_end - step_start


def alpha_from_tag(raw_alpha: str | None) -> float:
    if raw_alpha is None:
        return 0.0
    match = re.search(_ALPHA_VALUE_PATTERN, raw_alpha)
    if match is None:
        return 0.0
    return float(int(match.group(1), 16))


def _format_alpha(value: float) -> str:
    return f"&H{round(value):02X}&"


def _set_alpha(
    tags_block: str, alpha_value: str, transform_suffix: str = ""
) -> str:
    block_without_fade = remove_fad_or_fade(tags_block)
    inner = _INLINE_ALPHA_TAG_RE.sub("", block_without_fade[1:-1])
    return "{" + inner + rf"\alpha{alpha_value}{transform_suffix}" + "}"


def _line_with_text(event: Event, text: str) -> Event:
    return Event(
        text=text,
        effect=event.effect,
        style=event.style,
        layer=event.layer,
        start_time=event.start_time,
        end_time=event.end_time,
        comment=event.comment,
        actor=event.actor,
        margin_l=event.margin_l,
        margin_r=event.margin_r,
        margin_t=event.margin_t,
        margin_b=event.margin_b,
    )


def _normalize_move_times(
    line_duration: float,
    t1: float | None,
    t2: float | None,
) -> tuple[float, float]:
    if t1 is not None and t2 is not None and t1 > t2:
        t1, t2 = t2, t1
    elif t1 is None or t2 is None:
        t1, t2 = 0.0, 0.0
    if t1 <= 0 and t2 <= 0:
        return 0.0, line_duration
    return t1, t2


def _fad_from_numbers(numbers: list[float]) -> FadTag | None:
    if len(numbers) != 2:
        return None
    return ("fad", numbers[0], numbers[1])


def _fade_from_numbers(numbers: list[float]) -> FadeTag | None:
    if len(numbers) != 7:
        return None
    return (
        "fade",
        numbers[0],
        numbers[1],
        numbers[2],
        numbers[3],
        numbers[4],
        numbers[5],
        numbers[6],
    )


def _move_from_numbers(numbers: list[float]) -> MoveTag | None:
    if len(numbers) < 4:
        return None
    if len(numbers) >= 6:
        return (
            numbers[0],
            numbers[1],
            numbers[2],
            numbers[3],
            numbers[4],
            numbers[5],
        )
    return (numbers[0], numbers[1], numbers[2], numbers[3], None, None)


def _resolved_tag_value(
    tag_context: MotionState,
    tag_name: str,
    end_value: TagValue,
    progress: float,
) -> TagValue:
    start_value = cast(TagValue, tag_context.get(tag_name, end_value))
    return interpolate_value(tag_name, progress, start_value, end_value)


def set_pos(tags_block: str, x: float, y: float) -> str:
    inner = tags_block[1:-1] if tags_block.startswith("{") else tags_block
    inner = _POS_TAG_RE.sub("", inner)
    inner = _MOVE_TAG_RE.sub("", inner)
    inner += rf"\pos({_format_ass_number(x)},{_format_ass_number(y)})"
    return "{" + inner + "}"


def inject_pos(event: Event, x: float, y: float) -> Event:
    match = _OVERRIDE_BLOCK_RE.search(event.text)
    if match is not None:
        updated_text = (
            event.text[: match.start()]
            + set_pos(match.group(0), x, y)
            + event.text[match.end() :]
        )
        return _line_with_text(event, updated_text)
    return _line_with_text(event, set_pos("{}", x, y) + event.text)


def set_move(
    tags_block: str,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    t1: float,
    t2: float,
) -> str:
    inner = tags_block[1:-1] if tags_block.startswith("{") else tags_block
    inner = _POS_TAG_RE.sub("", inner)
    inner = _MOVE_TAG_RE.sub("", inner)
    inner += (
        rf"\move({_format_ass_number(x1)},{_format_ass_number(y1)},"
        rf"{_format_ass_number(x2)},{_format_ass_number(y2)},"
        rf"{_format_ass_number(t1)},{_format_ass_number(t2)})"
    )
    return "{" + inner + "}"


def get_tag_move(
    current_time: float,
    line_duration: float,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    t1: float | None,
    t2: float | None,
) -> tuple[float, float, float]:
    t1, t2 = _normalize_move_times(line_duration, t1, t2)
    t = get_time_in_interval(current_time, t1, t2)
    x = math_round((1.0 - t) * x1 + t * x2, 3)
    y = math_round((1.0 - t) * y1 + t * y2, 3)
    return x, y, t


def get_alpha_interpolation(
    current_time: float,
    t1: float,
    t2: float,
    t3: float,
    t4: float,
    a1: float,
    a2: float,
    a3: float,
) -> float:
    if current_time < t1:
        return a1
    if current_time < t2:
        fraction = (current_time - t1) / (t2 - t1)
        return a1 * (1 - fraction) + a2 * fraction
    if current_time < t3:
        return a2
    if current_time < t4:
        fraction = (current_time - t3) / (t4 - t3)
        return a2 * (1 - fraction) + a3 * fraction
    return a3


def get_tag_fade(
    current_time: float,
    line_duration: float,
    default_alpha: float,
    fade_data: AnyFadeTag,
) -> float:
    kind = fade_data[0]
    if kind == "fad":
        _, fade_in, fade_out = cast(FadTag, fade_data)
        alpha_1, alpha_2, alpha_3 = 255.0, 0.0, 255.0
        t1 = 0.0
        t2 = float(fade_in)
        t3 = line_duration - float(fade_out)
        t4 = line_duration
    else:
        (
            _,
            alpha_1,
            alpha_2,
            alpha_3,
            t1,
            t2,
            t3,
            t4,
        ) = cast(FadeTag, fade_data)

    return get_alpha_interpolation(
        current_time,
        float(t1),
        float(t2),
        float(t3),
        float(t4),
        float(alpha_1),
        default_alpha if default_alpha else float(alpha_2),
        float(alpha_3),
    )


def calc_accel(t1: float, t2: float, t3: float) -> float:
    denominator = t3 - t1
    if denominator == 0:
        return 1.0
    ratio = (t2 - t1) / denominator
    if ratio <= 0 or ratio >= 1:
        return 1.0
    try:
        accel = math.log(ratio) / math.log(0.5)
    except ValueError, ZeroDivisionError:
        return 1.0
    if math.isnan(accel) or math.isinf(accel):
        return 1.0
    return math_round(math_clamp(accel, 0.01, 100.0))


def round_line_time(value: float) -> float:
    return math.floor((value + 5) / 10) * 10


def _numeric_tag_value(value: TagValue) -> float:
    if isinstance(value, list):
        raise PykaraError(
            "numeric tag interpolation does not accept list values"
        )
    return float(value)


def _line_duration_from_state(tag_context: MotionState, fallback: float) -> int:
    value = tag_context.get(LINE_DURATION_KEY, int(fallback))
    return int(cast(int, value))


def collect_initial_data(text: str) -> MotionState:
    tag_context: MotionState = {}
    raw_blocks = re.findall(r"\{[^}]*\}", text)
    for raw_block in raw_blocks:
        _, clean_block = extract_t_tags(raw_block)
        block = clean_block[1:-1]
        for tag_name in _ORDERED_TAGS:
            value = get_tag_value_from_block(block, tag_name)
            if value is not None:
                tag_context[tag_name] = coerce_value(tag_name, value)

        move_numbers = _extract_parenthesized_numbers(block, "move")
        if move_numbers is not None:
            move = _move_from_numbers(move_numbers)
            if move is not None:
                tag_context["move"] = move

        pos_numbers = _extract_parenthesized_numbers(block, "pos")
        if pos_numbers is not None and len(pos_numbers) >= 2:
            tag_context["pos"] = pos_numbers[:2]

        fad_numbers = _extract_parenthesized_numbers(block, "fad")
        if fad_numbers is not None:
            parsed_fad = _fad_from_numbers(fad_numbers)
            if parsed_fad is not None:
                tag_context["fad"] = parsed_fad

        fade_numbers = _extract_parenthesized_numbers(block, "fade")
        if fade_numbers is not None:
            parsed_fade = _fade_from_numbers(fade_numbers)
            if parsed_fade is not None:
                tag_context["fade"] = parsed_fade

    return tag_context


def lerp_tag_transform(
    current_time: float,
    step: int,
    step_start_ms: float,
    step_end_ms: float,
    line_start_ms: int,
    line_duration: int,
    tag_context: MotionState,
    tags_block: str,
) -> str:
    while True:
        transform_payloads, tags_block = extract_t_tags(tags_block)
        if not transform_payloads:
            break
        payload = transform_payloads[0]
        remaining_payloads = transform_payloads[1:]
        start_time, end_time, accel, transform = parse_t_tag(payload)
        effective_start = start_time if start_time is not None else 0.0
        effective_end = (
            end_time if end_time is not None else float(line_duration)
        )
        inner_tags = _extract_all_tag_items_from_block(transform)
        inner_tag_names = tuple(tag_name for tag_name, _ in inner_tags)

        if step > 1:
            step_start, step_end, step_duration = _relative_step_window(
                step_start_ms, step_end_ms, line_start_ms
            )
            step_mid = (step_start + step_end) * 0.5
            t_start = get_time_in_interval(
                step_start, effective_start, effective_end, accel
            )
            t_mid = get_time_in_interval(
                step_mid, effective_start, effective_end, accel
            )
            t_end = get_time_in_interval(
                step_end, effective_start, effective_end, accel
            )
            accel_step = calc_accel(t_start, t_mid, t_end)

            current_fragments: list[str] = []
            end_fragments: list[str] = []
            for tag_name, raw_end_value in inner_tags:
                end_value = coerce_value(tag_name, raw_end_value)
                current_value = _resolved_tag_value(
                    tag_context, tag_name, end_value, t_start
                )
                step_end_value = _resolved_tag_value(
                    tag_context, tag_name, end_value, t_end
                )
                tag_context[tag_name] = step_end_value
                current_fragments.append(
                    _format_tag_assignment(tag_name, current_value)
                )
                end_fragments.append(
                    _format_tag_assignment(tag_name, step_end_value)
                )

            if end_fragments:
                transform_start = max(effective_start - step_start, 0)
                transform_end = min(effective_end - step_start, step_duration)
                shortened = (
                    rf"\gt({_format_ass_number(transform_start)},"
                    rf"{_format_ass_number(transform_end)},"
                    rf"{_format_ass_number(accel_step)},"
                    + "".join(end_fragments)
                    + ")"
                )
                tags_block = _rebuild_block(
                    tags_block, inner_tag_names, current_fragments, shortened
                )
            else:
                tags_block = _rebuild_block(
                    tags_block, inner_tag_names, current_fragments
                )
        else:
            t = get_time_in_interval(
                current_time, effective_start, effective_end, accel
            )
            current_fragments: list[str] = []
            for tag_name, raw_end_value in inner_tags:
                result = _resolved_tag_value(
                    tag_context,
                    tag_name,
                    coerce_value(tag_name, raw_end_value),
                    t,
                )
                tag_context[tag_name] = result
                current_fragments.append(
                    _format_tag_assignment(tag_name, result)
                )
            tags_block = _rebuild_block(
                tags_block, inner_tag_names, current_fragments
            )

        for remaining in remaining_payloads:
            tags_block = "{" + tags_block[1:-1] + rf"\t({remaining})" + "}"

    if step > 1:
        tags_block = tags_block.replace(r"\gt(", r"\t(")
    return tags_block


def lerp_tag_move(
    current_time: float,
    step: int,
    step_start_ms: float,
    step_end_ms: float,
    line_start_ms: int,
    tag_context: MotionState,
    tags_block: str,
) -> str:
    if "move" not in tag_context:
        return tags_block
    move = tag_context["move"]
    if not isinstance(move, tuple) or len(move) != 6:
        return tags_block
    x1, y1, x2, y2, t1_move, t2_move = move
    line_duration = _line_duration_from_state(
        tag_context, step_end_ms - line_start_ms
    )
    normalized_t1, normalized_t2 = _normalize_move_times(
        line_duration, t1_move, t2_move
    )

    if step > 1:
        step_start, step_end, step_duration = _relative_step_window(
            step_start_ms, step_end_ms, line_start_ms
        )
        rx1, ry1, progress_start = get_tag_move(
            step_start,
            line_duration,
            x1,
            y1,
            x2,
            y2,
            normalized_t1,
            normalized_t2,
        )
        rx2, ry2, progress_end = get_tag_move(
            step_end,
            line_duration,
            x1,
            y1,
            x2,
            y2,
            normalized_t1,
            normalized_t2,
        )
        if progress_start == 0 and progress_end == 0:
            tag_context["pos"] = [rx1, ry1]
            del tag_context["move"]
            return set_pos(tags_block, rx1, ry1)
        if progress_start == 1 and progress_end == 1:
            tag_context["pos"] = [rx2, ry2]
            del tag_context["move"]
            return set_pos(tags_block, rx2, ry2)
        move_start = max(normalized_t1 - step_start, 0)
        move_end = min(normalized_t2 - step_start, step_duration)
        tag_context["move"] = (rx1, ry1, rx2, ry2, move_start, move_end)
        tag_context["pos"] = [rx1, ry1]
        return set_move(tags_block, rx1, ry1, rx2, ry2, move_start, move_end)

    x, y, _ = get_tag_move(
        current_time,
        line_duration,
        x1,
        y1,
        x2,
        y2,
        normalized_t1,
        normalized_t2,
    )
    tag_context["pos"] = [x, y]
    del tag_context["move"]
    return set_pos(tags_block, x, y)


def lerp_tag_fade(
    current_time: float,
    step: int,
    step_start_ms: float,
    step_end_ms: float,
    line_start_ms: int,
    line_duration: int,
    tag_context: MotionState,
    tags_block: str,
) -> str:
    fade_data = tag_context.get("fad") or tag_context.get("fade")
    if fade_data is None or not isinstance(fade_data, tuple):
        return tags_block
    typed_fade_data = cast(AnyFadeTag, fade_data)
    base_alpha = alpha_from_tag(
        get_tag_value_from_block(tags_block[1:-1], "alpha")
    )

    if step > 1:
        step_start, step_end, _ = _relative_step_window(
            step_start_ms, step_end_ms, line_start_ms
        )
        alpha_start = get_tag_fade(
            step_start, line_duration, base_alpha, typed_fade_data
        )
        alpha_end = get_tag_fade(
            step_end, line_duration, base_alpha, typed_fade_data
        )
        tags_block = _set_alpha(
            tags_block,
            _format_alpha(alpha_start),
            rf"\t(\alpha{_format_alpha(alpha_end)})",
        )
    else:
        alpha_value = get_tag_fade(
            current_time, line_duration, base_alpha, typed_fade_data
        )
        tags_block = _set_alpha(tags_block, _format_alpha(alpha_value))

    tag_context.pop("fad", None)
    tag_context.pop("fade", None)
    return tags_block
