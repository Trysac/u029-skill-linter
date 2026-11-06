"""Parser for the YAML subset used in SKILL.md frontmatter (standard library only).

Supported: ``key: value`` scalars (plain, single- or double-quoted), folded ``>`` and literal
``|`` blocks, and one indented level of ``key: value`` pairs (for ``metadata``). Everything
else is reported as unsupported syntax together with its line number.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .textutil import quote

__all__ = ["FieldValue", "Frontmatter", "parse_frontmatter"]

FieldValue = str | dict[str, str]

_FENCE = "---"
_KEY_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_.-]*):(?:[ \t]+(.*))?")
_NESTED_RE = re.compile(r"( +)([A-Za-z_][A-Za-z0-9_.-]*):(?:[ \t]+(.*))?")
_BLOCK_RE = re.compile(r"[>|][+-]?")
_UNSUPPORTED_START = "[{&*!%@`|>"
_ESCAPES = {'"': '"', "\\": "\\", "n": "\n", "t": "\t", "/": "/"}


@dataclass(frozen=True)
class Frontmatter:
    """Result of parsing the frontmatter block of a SKILL.md file.

    ``body_start`` is the 1-based line number of the first line after the closing fence, or
    ``None`` when the fences are missing. ``errors`` holds ``(line, message)`` pairs.
    """

    fields: Mapping[str, FieldValue]
    key_lines: Mapping[str, int]
    errors: tuple[tuple[int, str], ...]
    body_start: int | None


class _Unsupported(Exception):
    """Internal signal for syntax outside the supported subset."""

    def __init__(self, line: int, reason: str) -> None:
        super().__init__(reason)
        self.line = line
        self.reason = reason


def _fence_error(message: str) -> Frontmatter:
    return Frontmatter({}, {}, ((1, message),), None)


def parse_frontmatter(lines: Sequence[str]) -> Frontmatter:
    """Parse the frontmatter at the top of ``lines`` (file lines without line endings).

    Parsing stops at the first unsupported construct, which is reported in ``errors``.
    """
    if not lines or lines[0].rstrip() != _FENCE:
        return _fence_error("file must start with a '---' frontmatter fence")
    close = next((i for i in range(1, len(lines)) if lines[i].rstrip() == _FENCE), None)
    if close is None:
        return _fence_error("frontmatter is not closed by a '---' fence")
    fields: dict[str, FieldValue] = {}
    key_lines: dict[str, int] = {}
    errors: tuple[tuple[int, str], ...] = ()
    try:
        i = 1
        while i < close:
            i = _parse_entry(lines, i, close, fields, key_lines)
    except _Unsupported as exc:
        errors = ((exc.line, f"unsupported frontmatter syntax: {exc.reason}"),)
    return Frontmatter(fields, key_lines, errors, close + 2)


def _parse_entry(
    lines: Sequence[str],
    i: int,
    end: int,
    fields: dict[str, FieldValue],
    key_lines: dict[str, int],
) -> int:
    raw = lines[i]
    stripped = raw.strip()
    if not stripped or stripped.startswith("#"):
        return i + 1
    match = _KEY_RE.fullmatch(raw.rstrip())
    if match is None:
        raise _Unsupported(i + 1, f"cannot parse {quote(stripped)}")
    key = match.group(1)
    rest = (match.group(2) or "").strip()
    if key in fields:
        raise _Unsupported(i + 1, f"duplicate key '{key}'")
    key_lines[key] = i + 1
    if not rest:
        stop = _skip_indented(lines, i + 1, end)
        fields[key] = _parse_map(lines, i + 1, stop)
        return stop
    if _BLOCK_RE.fullmatch(rest):
        stop = _skip_indented(lines, i + 1, end)
        fields[key] = _fold(lines[i + 1 : stop], folded=rest[0] == ">")
        return stop
    fields[key] = _parse_scalar(rest, i + 1)
    return i + 1


def _skip_indented(lines: Sequence[str], start: int, end: int) -> int:
    index = start
    while index < end and (not lines[index].strip() or lines[index].startswith(" ")):
        index += 1
    return index


def _parse_map(lines: Sequence[str], start: int, stop: int) -> FieldValue:
    result: dict[str, str] = {}
    indent = -1
    for index in range(start, stop):
        line = lines[index]
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        match = _NESTED_RE.fullmatch(line.rstrip())
        if match is None or indent not in (-1, len(match.group(1))):
            raise _Unsupported(index + 1, f"cannot parse {quote(text)}")
        indent = len(match.group(1))
        nested_key = match.group(2)
        if nested_key in result:
            raise _Unsupported(index + 1, f"duplicate key '{nested_key}'")
        result[nested_key] = _parse_scalar(match.group(3) or "", index + 1)
    return result if result else ""


def _fold(block: Sequence[str], *, folded: bool) -> str:
    content = [line for line in block if line.strip()]
    if not content:
        return ""
    if folded:
        return " ".join(line.strip() for line in content)
    indent = min(len(line) - len(line.lstrip(" ")) for line in content)
    return "\n".join(line[indent:] if line.strip() else "" for line in block).strip("\n")


def _parse_scalar(text: str, line: int) -> str:
    if not text or text.startswith("#"):
        return ""
    if text[0] in ('"', "'"):
        return _parse_quoted(text, line)
    if text[0] in _UNSUPPORTED_START:
        raise _Unsupported(line, f"value starting with {text[0]!r} is not supported")
    cut = text.find(" #")
    return (text if cut < 0 else text[:cut]).strip()


def _parse_quoted(text: str, line: int) -> str:
    delimiter = text[0]
    buffer: list[str] = []
    i = 1
    while i < len(text):
        char = text[i]
        if char == delimiter:
            if delimiter == "'" and text[i + 1 : i + 2] == "'":
                buffer.append("'")
                i += 2
                continue
            tail = text[i + 1 :].strip()
            if tail and not tail.startswith("#"):
                raise _Unsupported(line, "unexpected text after quoted string")
            return "".join(buffer)
        if delimiter == '"' and char == "\\":
            replacement = _ESCAPES.get(text[i + 1 : i + 2])
            if replacement is None:
                raise _Unsupported(line, "unsupported escape sequence")
            buffer.append(replacement)
            i += 2
            continue
        buffer.append(char)
        i += 1
    raise _Unsupported(line, "unterminated quoted string")
