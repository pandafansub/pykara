"""Shared execution scopes for declarations and specifications."""

from __future__ import annotations

from enum import StrEnum


class Scope(StrEnum):
    """Execution scope vocabulary shared by template and code declarations."""

    SETUP = "setup"
    LINE = "line"
    WORD = "word"
    SYL = "syl"
    CHAR = "char"
