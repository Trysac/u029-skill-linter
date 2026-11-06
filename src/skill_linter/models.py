"""Immutable data types shared across the package."""

from __future__ import annotations

from dataclasses import dataclass

from .rules import BODY_MAX_LINES, DESCRIPTION_MAX_CHARS, TRIGGER_CUES, Severity

__all__ = ["Finding", "LintConfig"]


@dataclass(frozen=True)
class Finding:
    """One problem found in a SKILL.md file; ``line`` is a 1-based file line number."""

    path: str
    line: int
    rule: str
    severity: Severity
    message: str


@dataclass(frozen=True)
class LintConfig:
    """Limits and options of a lint run."""

    max_body_lines: int = BODY_MAX_LINES
    max_description: int = DESCRIPTION_MAX_CHARS
    trigger_cues: tuple[str, ...] = TRIGGER_CUES
    max_file_bytes: int = 1_048_576
    max_findings: int = 10_000
