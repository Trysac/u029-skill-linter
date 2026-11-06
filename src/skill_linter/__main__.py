"""Command line interface: ``python -m skill_linter PATH... [--format text|json] [--strict]``."""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import stat
import sys
from collections.abc import Sequence
from pathlib import Path

from .errors import SkillLintError
from .linter import MAX_SKILL_FILES, SKILL_FILE, find_skill_dirs, run_lint
from .models import Finding, LintConfig
from .textutil import quote

__all__ = ["main"]

_stat = os.stat


def _non_negative(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be an integer") from None
    if number < 0:
        raise argparse.ArgumentTypeError("must not be negative")
    return number


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="skill-lint",
        description="Lint agent skill folders (SKILL.md) against the Agent Skills format.",
    )
    parser.add_argument("paths", nargs="+", metavar="PATH", help="folder, tree or SKILL.md file")
    parser.add_argument("--format", choices=("text", "json"), default="text", dest="output_format")
    parser.add_argument("--strict", action="store_true", help="exit 1 on warnings as well")
    parser.add_argument("--max-body-lines", type=_non_negative, metavar="N", help="line budget")
    parser.add_argument("--max-findings", type=_non_negative, metavar="N", help="finding limit")
    return parser


def _collect_dirs(paths: Sequence[str]) -> list[Path]:
    dirs: list[Path] = []
    seen: set[str] = set()
    for raw in paths:
        path = Path(raw)
        try:
            mode = _stat(path).st_mode
        except (FileNotFoundError, NotADirectoryError):
            raise SkillLintError("usage", f"path not found: {quote(raw)}") from None
        except OSError:
            raise SkillLintError("io", f"cannot access path: {quote(raw)}") from None
        except ValueError:
            raise SkillLintError("usage", f"invalid path: {quote(raw)}") from None
        if stat.S_ISDIR(mode):
            found = find_skill_dirs(path)
        elif path.name == SKILL_FILE and stat.S_ISREG(mode):
            found = [path.parent]
        else:
            raise SkillLintError("usage", f"not a folder or {SKILL_FILE}: {quote(raw)}")
        for folder in found:
            key = folder.as_posix()
            if key not in seen:
                seen.add(key)
                dirs.append(folder)
        if len(dirs) >= MAX_SKILL_FILES:
            break
    return dirs[:MAX_SKILL_FILES]


def _as_json(findings: Sequence[Finding]) -> str:
    rows = [
        {
            "path": f.path,
            "line": f.line,
            "rule": f.rule,
            "severity": f.severity,
            "message": f.message,
        }
        for f in findings
    ]
    return json.dumps(rows)


def main(argv: list[str] | None = None) -> int:
    """Run the linter and return the exit code.

    ``0``: no errors (warnings only count with ``--strict``); ``1``: errors, or warnings with
    ``--strict``; ``2``: usage error or missing PATH.
    """
    try:
        args = _build_parser().parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2
    config = LintConfig()
    if args.max_body_lines is not None:
        config = dataclasses.replace(config, max_body_lines=args.max_body_lines)
    if args.max_findings is not None:
        config = dataclasses.replace(config, max_findings=args.max_findings)
    try:
        dirs = _collect_dirs(args.paths)
    except SkillLintError as exc:
        print(f"skill-lint: {exc}", file=sys.stderr)
        return 2
    if not dirs:
        print("no SKILL.md found", file=sys.stderr)
    result = run_lint(dirs, config)
    if args.output_format == "json":
        print(_as_json(result.findings))
    else:
        for f in result.findings:
            print(f"{f.path}:{f.line}: {f.severity} {f.rule} {f.message}")
    if result.truncated:
        print(f"findings truncated at {config.max_findings}", file=sys.stderr)
    failed = any(f.severity == "error" for f in result.findings)
    if args.strict and result.findings:
        failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
