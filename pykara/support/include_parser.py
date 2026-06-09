"""Parsing helpers for code include declarations."""

from __future__ import annotations

import ast

from pykara.errors import IncludeParseError


def is_include_source(source: str) -> bool:
    """Return whether source is an include declaration."""

    stripped = source.strip()
    return stripped.startswith("include") and (
        stripped == "include" or stripped[7:8].isspace()
    )


def parse_include_paths(source: str) -> tuple[str, ...]:
    """Parse include declaration paths from one code body."""

    arguments = source.strip()[7:].strip()
    if not arguments:
        raise IncludeParseError("expected path after 'include'")

    try:
        tree = ast.parse(
            f"__pykara_include__({arguments})",
            filename="<pykara-include>",
            mode="eval",
        )
    except SyntaxError as error:
        raise IncludeParseError(str(error)) from error

    call = tree.body
    if not isinstance(call, ast.Call) or call.keywords:
        raise IncludeParseError("expected one or more string path arguments")

    paths: list[str] = []
    for argument in call.args:
        try:
            value = ast.literal_eval(argument)
        except (TypeError, ValueError) as error:
            raise IncludeParseError(
                "include paths must be string literals"
            ) from error
        if not isinstance(value, str):
            raise IncludeParseError("include paths must be string literals")
        paths.append(value)
    return tuple(paths)
