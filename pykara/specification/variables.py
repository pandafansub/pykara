"""Variable-level language contracts for template expressions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VariableSpecification:
    """Describe one variable exposed by the runtime variable context."""

    name: str
    type: str
    group: str
    description: str


def _variable(
    name: str,
    type_name: str,
    group: str,
    description: str,
) -> VariableSpecification:
    return VariableSpecification(name, type_name, group, description)


VARIABLE_SPECIFICATIONS: dict[str, VariableSpecification] = {
    "layer": _variable(
        "layer",
        "int",
        "template_vars",
        "Current generated line layer.",
    ),
    "actor": _variable(
        "actor",
        "str",
        "template_vars",
        "Current generated line actor.",
    ),
    "loop_i": _variable(
        "loop_i",
        "int",
        "template_vars",
        "Current iteration index when exactly one loop is visible.",
    ),
    "loop_n": _variable(
        "loop_n",
        "int",
        "template_vars",
        "Total iterations when exactly one loop is visible.",
    ),
    "line_start": _variable(
        "line_start", "int", "line_vars", "Line start time in ms."
    ),
    "line_end": _variable(
        "line_end", "int", "line_vars", "Line end time in ms."
    ),
    "line_dur": _variable(
        "line_dur", "int", "line_vars", "Total line duration in ms."
    ),
    "line_mid": _variable(
        "line_mid", "float", "line_vars", "Line temporal midpoint."
    ),
    "line_i": _variable(
        "line_i", "int", "line_vars", "Line index in the document."
    ),
    "line_left": _variable(
        "line_left", "int", "line_vars", "Line left X position."
    ),
    "line_center": _variable(
        "line_center", "int", "line_vars", "Line horizontal center."
    ),
    "line_right": _variable(
        "line_right", "int", "line_vars", "Line right X position."
    ),
    "line_width": _variable(
        "line_width", "int", "line_vars", "Line width in pixels."
    ),
    "line_top": _variable(
        "line_top", "int", "line_vars", "Line top Y position."
    ),
    "line_middle": _variable(
        "line_middle", "int", "line_vars", "Line vertical center."
    ),
    "line_bottom": _variable(
        "line_bottom", "int", "line_vars", "Line bottom Y position."
    ),
    "line_height": _variable(
        "line_height", "int", "line_vars", "Line height in pixels."
    ),
    "line_x": _variable(
        "line_x", "int", "line_vars", "Line anchor X position."
    ),
    "line_y": _variable(
        "line_y", "int", "line_vars", "Line anchor Y position."
    ),
    "word_start": _variable(
        "word_start", "int", "word_vars", "Word start time in ms."
    ),
    "word_end": _variable(
        "word_end", "int", "word_vars", "Word end time in ms."
    ),
    "word_dur": _variable(
        "word_dur", "int", "word_vars", "Word duration in ms."
    ),
    "word_kdur": _variable(
        "word_kdur",
        "float",
        "word_vars",
        "Word duration in centiseconds.",
    ),
    "word_mid": _variable(
        "word_mid", "float", "word_vars", "Word temporal midpoint."
    ),
    "word_n": _variable(
        "word_n", "int", "word_vars", "Total number of words in the line."
    ),
    "word_i": _variable(
        "word_i", "int", "word_vars", "Word index in the line."
    ),
    "word_left": _variable(
        "word_left", "int", "word_vars", "Word left X position."
    ),
    "word_center": _variable(
        "word_center", "int", "word_vars", "Word horizontal center."
    ),
    "word_right": _variable(
        "word_right", "int", "word_vars", "Word right X position."
    ),
    "word_width": _variable(
        "word_width", "int", "word_vars", "Word width in pixels."
    ),
    "word_top": _variable(
        "word_top", "int", "word_vars", "Word top Y position."
    ),
    "word_middle": _variable(
        "word_middle", "int", "word_vars", "Word vertical center."
    ),
    "word_bottom": _variable(
        "word_bottom", "int", "word_vars", "Word bottom Y position."
    ),
    "word_height": _variable(
        "word_height", "int", "word_vars", "Word height in pixels."
    ),
    "word_x": _variable(
        "word_x", "int", "word_vars", "Word anchor X position."
    ),
    "word_y": _variable(
        "word_y", "int", "word_vars", "Word anchor Y position."
    ),
    "syl_start": _variable(
        "syl_start", "int", "syl_vars", "Syllable start time in ms."
    ),
    "syl_end": _variable(
        "syl_end", "int", "syl_vars", "Syllable end time in ms."
    ),
    "syl_dur": _variable(
        "syl_dur", "int", "syl_vars", "Syllable duration in ms."
    ),
    "syl_kdur": _variable(
        "syl_kdur",
        "float",
        "syl_vars",
        "Syllable duration in centiseconds.",
    ),
    "syl_mid": _variable(
        "syl_mid", "float", "syl_vars", "Syllable temporal midpoint."
    ),
    "syl_n": _variable(
        "syl_n", "int", "syl_vars", "Total number of syllables in the line."
    ),
    "syl_i": _variable(
        "syl_i", "int", "syl_vars", "Syllable index in the line."
    ),
    "syl_left": _variable(
        "syl_left", "int", "syl_vars", "Syllable left X position."
    ),
    "syl_center": _variable(
        "syl_center", "int", "syl_vars", "Syllable horizontal center."
    ),
    "syl_right": _variable(
        "syl_right", "int", "syl_vars", "Syllable right X position."
    ),
    "syl_width": _variable(
        "syl_width", "int", "syl_vars", "Syllable width in pixels."
    ),
    "syl_top": _variable(
        "syl_top", "int", "syl_vars", "Syllable top Y position."
    ),
    "syl_middle": _variable(
        "syl_middle", "int", "syl_vars", "Syllable vertical center."
    ),
    "syl_bottom": _variable(
        "syl_bottom", "int", "syl_vars", "Syllable bottom Y position."
    ),
    "syl_height": _variable(
        "syl_height", "int", "syl_vars", "Syllable height in pixels."
    ),
    "syl_x": _variable(
        "syl_x", "int", "syl_vars", "Syllable anchor X position."
    ),
    "syl_y": _variable(
        "syl_y", "int", "syl_vars", "Syllable anchor Y position."
    ),
    "char_left": _variable(
        "char_left", "int", "char_vars", "Character left X position."
    ),
    "char_i": _variable(
        "char_i",
        "int",
        "char_vars",
        "Character index in the current line.",
    ),
    "char_n": _variable(
        "char_n",
        "int",
        "char_vars",
        "Total number of characters in the current line.",
    ),
    "char_center": _variable(
        "char_center", "int", "char_vars", "Character horizontal center."
    ),
    "char_right": _variable(
        "char_right", "int", "char_vars", "Character right X position."
    ),
    "char_width": _variable(
        "char_width", "int", "char_vars", "Character width in pixels."
    ),
    "char_top": _variable(
        "char_top", "int", "char_vars", "Character top Y position."
    ),
    "char_middle": _variable(
        "char_middle", "int", "char_vars", "Character vertical center."
    ),
    "char_bottom": _variable(
        "char_bottom", "int", "char_vars", "Character bottom Y position."
    ),
    "char_height": _variable(
        "char_height", "int", "char_vars", "Character height in pixels."
    ),
    "char_x": _variable(
        "char_x", "int", "char_vars", "Character anchor X position."
    ),
    "char_y": _variable(
        "char_y", "int", "char_vars", "Character anchor Y position."
    ),
}
