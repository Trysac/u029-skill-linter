"""Typed error raised by the command line interface."""

from __future__ import annotations

from typing import Literal

__all__ = ["SkillLintError"]

MAX_MESSAGE = 200


class SkillLintError(Exception):
    """Base error of the library with a stable machine-readable ``code``.

    ``code`` is ``"usage"`` for invalid command line input and ``"io"`` when a path cannot be
    accessed. Only the command line interface raises it; the lint functions report problems
    as findings instead.
    """

    def __init__(self, code: Literal["usage", "io"], message: str) -> None:
        super().__init__(message[:MAX_MESSAGE])
        self.code: Literal["usage", "io"] = code
