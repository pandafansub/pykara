"""Unit tests for support utility helpers."""

from __future__ import annotations

import pytest

from pykara.errors import PykaraError
from pykara.support import (
    clamp,
    headtail,
    interpolate,
    interpolate_color,
    trim,
    words,
)
from pykara.support.ass_tags import merge_adjacent_override_blocks


class TestMergeAdjacentOverrideBlocks:
    def test_merges_two_adjacent_override_blocks(self) -> None:
        assert (
            merge_adjacent_override_blocks(r"{\an5}{\blur2}go")
            == r"{\an5\blur2}go"
        )

    def test_merges_more_than_two_adjacent_override_blocks(self) -> None:
        assert (
            merge_adjacent_override_blocks(r"{\an5}{\blur2}{\bord1}go")
            == r"{\an5\blur2\bord1}go"
        )

    def test_leaves_drawing_text_between_blocks_unchanged(self) -> None:
        assert (
            merge_adjacent_override_blocks(r"{\p1}m 0 0 l 1 1{\p0}")
            == r"{\p1}m 0 0 l 1 1{\p0}"
        )

    def test_leaves_non_override_blocks_unchanged(self) -> None:
        assert (
            merge_adjacent_override_blocks(r"{comment}{\blur2}go")
            == r"{comment}{\blur2}go"
        )


class TestClamp:
    def test_returns_value_inside_range(self) -> None:
        assert clamp(5, 0, 10) == 5

    def test_returns_minimum_below_range(self) -> None:
        assert clamp(-1, 0, 10) == 0

    def test_returns_maximum_above_range(self) -> None:
        assert clamp(11, 0, 10) == 10


class TestInterpolate:
    def test_returns_minimum_when_percentage_is_zero(self) -> None:
        assert interpolate(0.0, 10.0, 20.0) == 10.0

    def test_returns_maximum_when_percentage_is_one(self) -> None:
        assert interpolate(1.0, 10.0, 20.0) == 20.0

    def test_returns_intermediate_value(self) -> None:
        assert interpolate(0.25, 10.0, 20.0) == 12.5

    def test_saturates_below_zero(self) -> None:
        assert interpolate(-0.5, 10.0, 20.0) == 10.0

    def test_saturates_above_one(self) -> None:
        assert interpolate(1.5, 10.0, 20.0) == 20.0


class TestInterpolateColor:
    def test_returns_first_color_at_zero_percentage(self) -> None:
        result = interpolate_color(0.0, "&H00FF0000", "&H0000FF00")

        assert result == "&HFF0000&"

    def test_returns_last_color_at_full_percentage(self) -> None:
        result = interpolate_color(1.0, "&H00FF0000", "&H0000FF00")

        assert result == "&H00FF00&"

    def test_returns_midpoint_color_at_half_percentage(self) -> None:
        result = interpolate_color(0.5, "&H00000000", "&H00FFFFFF")

        assert result == "&H808080&"

    def test_supports_override_color_format(self) -> None:
        result = interpolate_color(0.0, "&HFFFFFF&", "&H000000&")

        assert result == "&HFFFFFF&"

    def test_supports_html_hex_color_format(self) -> None:
        result = interpolate_color(0.0, "#FF8040", "#000000")

        assert result == "&H4080FF&"

    def test_supports_alpha_only_color_format(self) -> None:
        result = interpolate_color(0.0, "&HAB&", "&HCD&")

        assert result == "&H000000&"

    def test_supports_html_hex_color_with_short_tail(self) -> None:
        result = interpolate_color(0.0, "#AB", "#000000")

        assert result == "&H0000AB&"

    def test_raises_for_invalid_color_string(self) -> None:
        with pytest.raises(PykaraError, match="Invalid color string"):
            interpolate_color(0.5, "not-a-color", "&H00FFFFFF")


class TestTrim:
    def test_removes_outer_whitespace(self) -> None:
        assert trim(" \t hello world \n") == "hello world"

    def test_preserves_inner_whitespace(self) -> None:
        assert trim("  hello   world  ") == "hello   world"

    def test_returns_empty_string_when_only_whitespace(self) -> None:
        assert trim(" \t\n ") == ""


class TestHeadtail:
    def test_returns_empty_pair_for_empty_string(self) -> None:
        assert headtail("") == ("", "")

    def test_returns_single_word_with_empty_tail(self) -> None:
        assert headtail("template") == ("template", "")

    def test_splits_first_word_from_tail(self) -> None:
        assert headtail("template syl loop 2") == ("template", "syl loop 2")

    def test_ignores_leading_whitespace_like_python_split(self) -> None:
        assert headtail("  template   syl") == ("template", "syl")


class TestWords:
    def test_yields_no_words_for_empty_string(self) -> None:
        assert list(words("")) == []

    def test_yields_words_in_order(self) -> None:
        assert list(words("template syl loop 2")) == [
            "template",
            "syl",
            "loop",
            "2",
        ]

    def test_ignores_repeated_whitespace(self) -> None:
        assert list(words(" \t template   syl \n loop ")) == [
            "template",
            "syl",
            "loop",
        ]
