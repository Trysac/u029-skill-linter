# Architecture

## Purpose

`trysac-skill-linter` is a small, dependency-free Python library and CLI that lints agent skill folders (SKILL.md) against the Agent Skills format.

## Shape

```text
skill_linter.__init__  -> public API (lint_skill, lint_tree, Finding, LintConfig, RULES)
skill_linter.linter    -> discovery, bounded reading, rule evaluation
skill_linter.frontmatter -> stdlib parser for the YAML subset
skill_linter.links     -> linear inline link extraction
skill_linter.rules     -> bundled rule table
skill_linter.__main__  -> python -m skill_linter CLI
```

- **Public API**: the names listed in `__all__` of `src/skill_linter/__init__.py`.
- **Errors**: the lint functions report problems as findings. `SkillLintError` is raised only by the CLI path.
- **Side effects**: the linter reads files (read-only) and never executes content. Logging goes to `getLogger(__name__)` with a NullHandler.

## Decisions

Architecture decisions are recorded in [decisions/](decisions/) as numbered ADRs.
