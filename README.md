# skill-linter

[![PyPI version](https://img.shields.io/pypi/v/trysac-skill-linter)](https://pypi.org/project/trysac-skill-linter/)
[![License: MIT](https://img.shields.io/pypi/l/trysac-skill-linter)](LICENSE)
[![CI](https://github.com/Trysac/u029-skill-linter/actions/workflows/ci.yml/badge.svg)](https://github.com/Trysac/u029-skill-linter/actions/workflows/ci.yml)

Lint agent skill folders (SKILL.md) against the Agent Skills format: frontmatter, name rules, description limits, trigger cues and broken links.

## Problem

Agent skills are SKILL.md files whose frontmatter description decides when the model loads them, but nothing checks them in CI. A name that differs from its folder, a vague or oversized description, or a link to a deleted reference file silently degrades the agent. skill-lint validates skill folders against the published format with stable rule ids and machine-readable output.

## Install

```sh
pip install trysac-skill-linter
# or
uv add trysac-skill-linter
```

Requires Python 3.10 or newer. No runtime dependencies.

## Usage

```python
from pathlib import Path

from skill_linter import lint_tree

for finding in lint_tree(Path("skills")):
    print(f"{finding.path}:{finding.line}: {finding.severity} {finding.rule} {finding.message}")
```

CLI: `python -m skill_linter skills --format json --strict`

## Public API

- `lint_skill(skill_dir: Path, config: LintConfig = LintConfig()) -> list[Finding]` lints one folder.
- `lint_tree(root: Path, config: LintConfig = LintConfig()) -> list[Finding]` lints every SKILL.md under `root` (symlinked directories are not followed, at most 10,000 files).
- `Finding(path, line, rule, severity, message)` is a frozen dataclass; severity is `error` or `warning`.
- `LintConfig(max_body_lines=500, max_description=1024, trigger_cues=('use when', 'when the user', 'trigger'), max_file_bytes=1_048_576, max_findings=10_000)`.
- `RULES` lists the rules S000 to S009.
- `SkillLintError(code)` is raised only by the CLI path; `code` is `usage` or `io`.

Rules: S000 unreadable, oversize or non-UTF-8 file; S001 frontmatter fences missing or unsupported syntax; S002 missing name or description; S003 name format or differs from folder; S004 description or compatibility over its limit; S005 no trigger cue (warning); S006 body over the line budget (warning); S007 missing link target; S008 link escapes the skill folder; S009 XML tag in name or description, or reserved word in name.

CLI exit codes: 0 no errors (warnings only count with `--strict`), 1 errors (or warnings with `--strict`), 2 usage error or missing PATH. Options: `--format text|json`, `--strict`, `--max-body-lines N`, `--max-findings N`.

Limits: the frontmatter parser supports only `key: value` scalars, quoted strings, folded `>` and literal `|` blocks, and one indented level for `metadata`; other syntax is reported as S001. Inline links only; reference-style links are not checked. Findings stop at `max_findings`.

## Why not markdownlint

markdownlint checks Markdown style, not the triggering contract of an agent skill.

## Security

See [docs/SECURITY.md](docs/SECURITY.md).

## Documentation

- [Architecture](docs/ARCHITECTURE.md) and [decisions](docs/decisions/)
- [Testing](docs/TESTING.md) and [security](docs/SECURITY.md)
- [Project record](docs/PROJECT.md) and [stack](docs/STACK.md)
- [Changelog](CHANGELOG.md) and [contributing guide](CONTRIBUTING.md)

## License

[MIT](LICENSE) (c) 2026 Miguel Gomez
