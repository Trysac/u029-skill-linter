"""Lint engine: skill discovery, bounded file reading and rule evaluation."""

from __future__ import annotations

import logging
import os
import stat
from collections.abc import Iterable
from dataclasses import dataclass
from itertools import islice
from pathlib import Path

from .frontmatter import Frontmatter, parse_frontmatter
from .links import iter_link_targets, normalize_target
from .models import Finding, LintConfig
from .rules import (
    COMPATIBILITY_MAX_CHARS,
    NAME_MAX_CHARS,
    NAME_RE,
    RESERVED_NAME_WORDS,
    RULES_BY_ID,
    XML_TAG_RE,
)
from .textutil import quote

__all__ = [
    "DEFAULT_CONFIG",
    "MAX_SKILL_FILES",
    "SKILL_FILE",
    "LintResult",
    "find_skill_dirs",
    "lint_skill",
    "lint_tree",
    "run_lint",
]

logger = logging.getLogger(__name__)

SKILL_FILE = "SKILL.md"
MAX_SKILL_FILES = 10_000
DEFAULT_CONFIG = LintConfig()

_NAME_HINT = f"must be 1-{NAME_MAX_CHARS} chars of a-z, 0-9 and inner '-'"


@dataclass(frozen=True)
class LintResult:
    """Findings of a lint run, sorted by ``(path, line, rule)``.

    ``truncated`` is true when more findings existed than ``LintConfig.max_findings``.
    """

    findings: tuple[Finding, ...]
    truncated: bool


class _Sink:
    """Collects findings up to a limit and remembers whether more were dropped."""

    def __init__(self, limit: int) -> None:
        self.items: list[Finding] = []
        self.limit = limit
        self.overflow = False

    def add(self, finding: Finding) -> bool:
        if len(self.items) >= self.limit:
            self.overflow = True
            return False
        self.items.append(finding)
        return True


class _Reporter:
    """Builds findings for one SKILL.md file."""

    def __init__(self, path: str, sink: _Sink) -> None:
        self.path = path
        self.sink = sink

    def report(self, line: int, rule: str, message: str) -> bool:
        severity = RULES_BY_ID[rule].severity
        return self.sink.add(Finding(self.path, line, rule, severity, message))


class _Unreadable(Exception):
    """Internal signal carrying the S000 message."""


def find_skill_dirs(root: Path) -> list[Path]:
    """Return every folder under ``root`` that holds a SKILL.md, in sorted walk order.

    Symlinked directories are never followed and at most ``MAX_SKILL_FILES`` folders return.
    """
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames.sort()
        if SKILL_FILE in filenames:
            found.append(Path(dirpath))
            if len(found) >= MAX_SKILL_FILES:
                break
    return found


def run_lint(skill_dirs: Iterable[Path], config: LintConfig = DEFAULT_CONFIG) -> LintResult:
    """Lint several skill folders with one shared ``max_findings`` budget."""
    sink = _Sink(config.max_findings)
    folders = list(islice(skill_dirs, MAX_SKILL_FILES))
    for folder in folders:
        _lint_one(folder, config, sink)
        if sink.overflow:
            break
    findings = tuple(sorted(sink.items, key=lambda f: (f.path, f.line, f.rule)))
    logger.debug("linted %d folder(s), %d finding(s)", len(folders), len(findings))
    return LintResult(findings, sink.overflow)


def lint_skill(skill_dir: Path, config: LintConfig = DEFAULT_CONFIG) -> list[Finding]:
    """Lint ``skill_dir/SKILL.md`` and return its findings sorted by path, line and rule."""
    return list(run_lint([skill_dir], config).findings)


def lint_tree(root: Path, config: LintConfig = DEFAULT_CONFIG) -> list[Finding]:
    """Lint every SKILL.md under ``root`` (at most 10_000 files, symlinks not followed)."""
    return list(run_lint(find_skill_dirs(root), config).findings)


def _read_text(path: Path, limit: int) -> str:
    try:
        info = os.lstat(path)
    except OSError:
        raise _Unreadable("SKILL.md cannot be read") from None
    if stat.S_ISLNK(info.st_mode):
        raise _Unreadable("SKILL.md is a symlink")
    if not stat.S_ISREG(info.st_mode):
        raise _Unreadable("SKILL.md is not a regular file")
    if info.st_size > limit:
        raise _Unreadable(f"SKILL.md is {info.st_size} bytes (max {limit})")
    try:
        with path.open("rb") as handle:
            data = handle.read(limit + 1)
    except OSError:
        raise _Unreadable("SKILL.md cannot be read") from None
    if len(data) > limit:
        raise _Unreadable(f"SKILL.md is larger than {limit} bytes")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise _Unreadable("SKILL.md is not valid UTF-8") from None


def _split_lines(text: str) -> list[str]:
    lines = [line.removesuffix("\r") for line in text.split("\n")]
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def _safe_resolve(path: Path) -> Path | None:
    try:
        return path.resolve()
    except (OSError, RuntimeError):
        return None


def _lint_one(skill_dir: Path, config: LintConfig, sink: _Sink) -> None:
    skill_file = skill_dir / SKILL_FILE
    rep = _Reporter(skill_file.as_posix(), sink)
    try:
        text = _read_text(skill_file, config.max_file_bytes)
    except _Unreadable as exc:
        rep.report(1, "S000", str(exc))
        return
    lines = _split_lines(text)
    fm = parse_frontmatter(lines)
    for line, message in fm.errors:
        rep.report(line, "S001", message)
    if fm.body_start is None:
        return
    if not fm.errors:
        resolved = _safe_resolve(skill_dir)
        folder = resolved.name if resolved is not None else skill_dir.name
        _check_fields(fm, folder, config, rep)
    body = lines[fm.body_start - 1 :]
    if len(body) > config.max_body_lines:
        message = f"body has {len(body)} lines (max {config.max_body_lines})"
        rep.report(fm.body_start + config.max_body_lines, "S006", message)
    _check_links(body, fm.body_start, skill_dir, rep)


def _required(fm: Frontmatter, key: str, rep: _Reporter) -> str | None:
    value = fm.fields.get(key)
    if value is None or (isinstance(value, str) and not value.strip()):
        rep.report(1, "S002", f"missing required field '{key}'")
        return None
    if not isinstance(value, str):
        rep.report(fm.key_lines[key], "S001", f"'{key}' must be a plain string")
        return None
    return value


def _check_fields(fm: Frontmatter, folder: str, config: LintConfig, rep: _Reporter) -> None:
    name = _required(fm, "name", rep)
    description = _required(fm, "description", rep)
    if name is not None:
        _check_name(name, fm.key_lines["name"], folder, rep)
    if description is not None:
        _check_description(description, fm.key_lines["description"], config, rep)
    compat = fm.fields.get("compatibility")
    if isinstance(compat, str) and len(compat) > COMPATIBILITY_MAX_CHARS:
        message = f"compatibility has {len(compat)} chars (max {COMPATIBILITY_MAX_CHARS})"
        rep.report(fm.key_lines["compatibility"], "S004", message)
    metadata = fm.fields.get("metadata")
    if isinstance(metadata, str) and metadata.strip():
        rep.report(fm.key_lines["metadata"], "S001", "metadata must be a one-level map")


def _check_name(name: str, line: int, folder: str, rep: _Reporter) -> None:
    if len(name) > NAME_MAX_CHARS or NAME_RE.fullmatch(name) is None:
        rep.report(line, "S003", f"name {quote(name)} {_NAME_HINT}")
    elif name != folder:
        rep.report(line, "S003", f"name {quote(name)} does not match folder {quote(folder)}")
    if XML_TAG_RE.search(name):
        rep.report(line, "S009", "name contains an XML tag")
    lowered = name.lower()
    reserved = next((word for word in RESERVED_NAME_WORDS if word in lowered), None)
    if reserved is not None:
        rep.report(line, "S009", f"name contains reserved word '{reserved}'")


def _check_description(text: str, line: int, config: LintConfig, rep: _Reporter) -> None:
    if len(text) > config.max_description:
        message = f"description has {len(text)} chars (max {config.max_description})"
        rep.report(line, "S004", message)
    if XML_TAG_RE.search(text):
        rep.report(line, "S009", "description contains an XML tag")
    lowered = text.lower()
    if config.trigger_cues and not any(cue.lower() in lowered for cue in config.trigger_cues):
        cue = quote(config.trigger_cues[0])
        rep.report(line, "S005", f"description has no trigger cue (e.g. '{cue}')")


def _check_links(body: list[str], first_line: int, skill_dir: Path, rep: _Reporter) -> None:
    base = _safe_resolve(skill_dir)
    if base is None:
        return
    for line, raw in iter_link_targets(body, first_line):
        target = normalize_target(raw)
        if target is None:
            continue
        try:
            resolved = (base / target).resolve()
        except (OSError, RuntimeError, ValueError):
            rep.report(line, "S007", f"link target cannot be resolved: {quote(raw)}")
            continue
        if not resolved.is_relative_to(base):
            rep.report(line, "S008", f"link escapes the skill folder: {quote(raw)}")
        elif not os.path.exists(resolved):
            rep.report(line, "S007", f"link target not found: {quote(raw)}")
        if rep.sink.overflow:
            break
