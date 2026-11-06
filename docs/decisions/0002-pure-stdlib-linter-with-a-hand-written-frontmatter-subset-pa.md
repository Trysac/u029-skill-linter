# Pure-stdlib linter with a hand-written frontmatter subset parser and a bundled rule table

Status: accepted (generated, pending human review)

## Context

Agent skills are SKILL.md folders whose frontmatter description decides when a model loads them, and nothing checks them in CI. markdownlint covers style, not the triggering contract. The linter reads untrusted repository content in CI, so it must be read-only, bounded and free of runtime dependencies.

## Decision

Implement the linter with the standard library only. A small frontmatter parser accepts a documented YAML subset (scalars, quoted strings, folded and literal blocks, one nested level) and reports anything else as S001 with its line number, instead of embedding a full YAML parser. Format limits live in a bundled RULES table that cites the Agent Skills specification and the Claude docs with the check date. Link scanning uses a bounded, linear regex plus a linear code-span masker. Containment is checked with is_relative_to on resolved paths so symlinks cannot escape the skill folder. Files are size-capped, read through lstat (symlinked SKILL.md is rejected), and decoded strictly as UTF-8. Findings are immutable dataclasses sorted by (path, line, rule) and capped by max_findings across the whole run. Errors are typed (SkillLintError) and raised only by the CLI.

## Consequences

There are no dependencies and the behaviour is deterministic and auditable. Valid YAML outside the subset, such as flow collections, multi-line plain scalars or list values for allowed-tools, is rejected with S001 until the subset is extended. Reference-style links are not checked. Updating the format means editing one table and its tests. The CLI runs as python -m skill_linter because the build manifest is not changed by this task.
