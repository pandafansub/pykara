"""Parsing helpers for preset declarations."""

from __future__ import annotations

import ast
import io
import tokenize
from dataclasses import dataclass

from pykara.errors import PresetParseError


@dataclass(frozen=True, slots=True)
class PreservePresetStyles:
    """Keep declaration styles exactly as they appear in the preset."""


@dataclass(frozen=True, slots=True)
class PresetForStyles:
    """Apply every style-sensitive declaration to each target style."""

    styles: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PresetStyleMap:
    """Map preset style names to consumer style names."""

    styles: tuple[tuple[str, str], ...]


PresetStyleTarget = PreservePresetStyles | PresetForStyles | PresetStyleMap


@dataclass(frozen=True, slots=True)
class PresetReference:
    """Normalized preset declaration arguments."""

    path: str
    target: PresetStyleTarget


@dataclass(frozen=True, slots=True)
class _Token:
    kind: int
    text: str


@dataclass(slots=True)
class _TokenReader:
    tokens: list[_Token]
    index: int = 0

    def done(self) -> bool:
        return self.index >= len(self.tokens)

    def consume_string(self, label: str) -> str:
        if self.done() or self.tokens[self.index].kind != tokenize.STRING:
            raise PresetParseError(f"{label} must be string literals")
        token = self.tokens[self.index]
        self.index += 1
        return _literal_string(token.text, label)

    def consume_name(self, name: str, message: str) -> None:
        if (
            self.done()
            or self.tokens[self.index].kind != tokenize.NAME
            or self.tokens[self.index].text != name
        ):
            raise PresetParseError(message)
        self.index += 1

    def consume_comma(self, message: str) -> None:
        if (
            self.done()
            or self.tokens[self.index].kind != tokenize.OP
            or self.tokens[self.index].text != ","
        ):
            raise PresetParseError(message)
        self.index += 1


def parse_preset_reference(source: str) -> PresetReference:
    """Parse a preset declaration body."""

    reader = _TokenReader(_significant_tokens(source))
    if reader.done():
        raise PresetParseError("expected preset path")

    path = reader.consume_string("preset path")

    if reader.done():
        return PresetReference(path, PreservePresetStyles())

    first = reader.tokens[reader.index]
    if first.kind != tokenize.NAME:
        raise PresetParseError("expected 'for' or 'map' after preset path")
    if first.text == "for":
        reader.index += 1
        return PresetReference(path, _parse_for_target(reader))
    if first.text == "map":
        reader.index += 1
        return PresetReference(path, _parse_map_target(reader))
    raise PresetParseError("expected 'for' or 'map' after preset path")


def _parse_for_target(reader: _TokenReader) -> PresetForStyles:
    if reader.done():
        raise PresetParseError("expected style name after 'for'")

    styles = [reader.consume_string("style names after 'for'")]
    while not reader.done():
        reader.consume_comma("expected ',' between style names")
        if reader.done():
            raise PresetParseError("expected style name after ','")
        styles.append(reader.consume_string("style names after 'for'"))
    return PresetForStyles(tuple(styles))


def _parse_map_target(reader: _TokenReader) -> PresetStyleMap:
    if reader.done():
        raise PresetParseError("expected style mapping after 'map'")

    mappings: list[tuple[str, str]] = []
    while not reader.done():
        mappings.append(
            (
                reader.consume_string("source style names in 'map'"),
                _consume_mapped_style(reader),
            )
        )

        if reader.done():
            return PresetStyleMap(tuple(mappings))
        reader.consume_comma("expected ',' between style mappings")
        if reader.done():
            raise PresetParseError("expected style mapping after ','")

    return PresetStyleMap(tuple(mappings))


def _consume_mapped_style(reader: _TokenReader) -> str:
    reader.consume_name("to", "expected 'to' in style mapping")
    return reader.consume_string("target style names in 'map'")


def _significant_tokens(source: str) -> list[_Token]:
    try:
        generated = tokenize.generate_tokens(io.StringIO(source).readline)
        return [
            _Token(token.type, token.string)
            for token in generated
            if token.type
            not in {
                tokenize.ENCODING,
                tokenize.ENDMARKER,
                tokenize.NEWLINE,
                tokenize.NL,
            }
        ]
    except tokenize.TokenError as error:
        raise PresetParseError(str(error)) from error


def _literal_string(source: str, label: str) -> str:
    try:
        value = ast.literal_eval(source)
    except (SyntaxError, ValueError) as error:
        raise PresetParseError(f"{label} must be string literals") from error
    if not isinstance(value, str):
        raise PresetParseError(f"{label} must be string literals")
    return value
