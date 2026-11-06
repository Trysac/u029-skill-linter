"""Bundled rule table for the Agent Skills format.

Sources, checked on 2026-11-05:

* Agent Skills specification (agentskills.io/specification): ``name`` is required, 1-64 chars
  of a-z, 0-9 and ``-``, with no leading, trailing or consecutive ``-`` and equal to the parent
  directory name; ``description`` is required, 1-1024 chars; optional ``license``,
  ``compatibility`` (max 500 chars), ``metadata`` (one-level map) and ``allowed-tools``.
* Claude Agent Skills docs (platform.claude.com, Agent Skills overview): ``name`` and
  ``description`` contain no XML tags and ``name`` contains neither ``anthropic`` nor
  ``claude``. Keeping SKILL.md under 500 lines is best-practice guidance, hence a warning.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final, Literal

__all__ = [
    "BODY_MAX_LINES",
    "COMPATIBILITY_MAX_CHARS",
    "DESCRIPTION_MAX_CHARS",
    "NAME_MAX_CHARS",
    "NAME_RE",
    "RESERVED_NAME_WORDS",
    "RULES",
    "RULES_BY_ID",
    "TRIGGER_CUES",
    "XML_TAG_RE",
    "Rule",
    "Severity",
]

Severity = Literal["error", "warning"]


@dataclass(frozen=True)
class Rule:
    """One lint rule with a stable id."""

    id: str
    severity: Severity
    title: str
    source: str


_SPEC = "agentskills.io/specification"
_CLAUDE = "platform.claude.com, Agent Skills overview"
_TOOL = "this tool"

RULES: Final[tuple[Rule, ...]] = (
    Rule("S000", "error", "SKILL.md is unreadable, oversize or not valid UTF-8", _TOOL),
    Rule("S001", "error", "frontmatter fences missing or unsupported syntax", _SPEC),
    Rule("S002", "error", "required field name or description is missing", _SPEC),
    Rule("S003", "error", "name violates the format or differs from the folder", _SPEC),
    Rule("S004", "error", "description or compatibility exceeds its limit", _SPEC),
    Rule("S005", "warning", "description has no trigger cue", _CLAUDE),
    Rule("S006", "warning", "body exceeds the line budget", _CLAUDE),
    Rule("S007", "error", "relative link target does not exist", _TOOL),
    Rule("S008", "error", "relative link escapes the skill folder", _TOOL),
    Rule("S009", "error", "XML tag in name or description, or reserved word in name", _CLAUDE),
)

RULES_BY_ID: Final[dict[str, Rule]] = {rule.id: rule for rule in RULES}

NAME_MAX_CHARS: Final = 64
DESCRIPTION_MAX_CHARS: Final = 1024
COMPATIBILITY_MAX_CHARS: Final = 500
BODY_MAX_LINES: Final = 500
RESERVED_NAME_WORDS: Final = ("anthropic", "claude")
TRIGGER_CUES: Final = ("use when", "when the user", "trigger")

NAME_RE: Final = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
XML_TAG_RE: Final = re.compile(r"<[A-Za-z/][^>]{0,200}>")
