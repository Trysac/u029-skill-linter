"""Lint agent skill folders (SKILL.md) against the Agent Skills format."""

from __future__ import annotations

import logging

from .errors import SkillLintError
from .linter import LintResult, lint_skill, lint_tree
from .models import Finding, LintConfig
from .rules import RULES, Rule

__all__ = [
    "RULES",
    "Finding",
    "LintConfig",
    "LintResult",
    "Rule",
    "SkillLintError",
    "__version__",
    "lint_skill",
    "lint_tree",
]

__version__ = "0.1.0"

logging.getLogger(__name__).addHandler(logging.NullHandler())
