"""Markdown inline link extraction in linear time (no Markdown library)."""

from __future__ import annotations

import re
from collections.abc import Iterator, Sequence
from urllib.parse import unquote

__all__ = ["iter_link_targets", "normalize_target"]

_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
_BACKTICKS_RE = re.compile(r"`+")
_SCHEME_RE = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*:")
_LINK_RE = re.compile(
    r"\[(?:[^\[\]]|\[[^\[\]]*\]){0,1000}\]"
    r"\(\s*(?P<target><[^<>\n]{1,2000}>|(?:[^\s()<>]|\([^\s()]*\)){1,2000})"
    r"""(?:\s+(?:"[^"]*"|'[^']*'))?\s*\)"""
)


def _mask_code_spans(line: str) -> str:
    """Blank out inline code spans (same-length backtick runs) in linear time."""
    if "`" not in line:
        return line
    runs = [(m.start(), m.end()) for m in _BACKTICKS_RE.finditer(line)]
    following = [-1] * len(runs)
    last_seen: dict[int, int] = {}
    for index in range(len(runs) - 1, -1, -1):
        length = runs[index][1] - runs[index][0]
        following[index] = last_seen.get(length, -1)
        last_seen[length] = index
    chars = list(line)
    index = 0
    while index < len(runs):
        closer = following[index]
        if closer == -1:
            index += 1
            continue
        for position in range(runs[index][0], runs[closer][1]):
            chars[position] = " "
        index = closer + 1
    return "".join(chars)


def iter_link_targets(lines: Sequence[str], first_line: int) -> Iterator[tuple[int, str]]:
    """Yield ``(line_number, raw_target)`` for inline links and images in ``lines``.

    Fenced code blocks (``` or ~~~) and inline code spans are skipped. ``first_line`` is the
    file line number of ``lines[0]``. The raw target may still carry ``<...>`` brackets.
    """
    fence: tuple[str, int] | None = None
    for offset, line in enumerate(lines):
        match = _FENCE_RE.match(line)
        if fence is None:
            if match and not (match.group(1)[0] == "`" and "`" in match.group(2)):
                fence = (match.group(1)[0], len(match.group(1)))
                continue
        else:
            if (
                match
                and match.group(1)[0] == fence[0]
                and len(match.group(1)) >= fence[1]
                and not match.group(2).strip()
            ):
                fence = None
            continue
        for found in _LINK_RE.finditer(_mask_code_spans(line)):
            yield first_line + offset, found.group("target")


def normalize_target(raw: str) -> str | None:
    """Return the relative filesystem path a raw link target points to, or ``None``.

    Targets with a scheme, or starting with ``#`` or ``/``, are not local relative links and
    give ``None``. Query and fragment are stripped and ``%xx`` escapes are decoded.
    """
    target = raw[1:-1] if raw.startswith("<") and raw.endswith(">") else raw
    if not target or target[0] in "#/" or _SCHEME_RE.match(target):
        return None
    cut = min((i for i in (target.find("?"), target.find("#")) if i >= 0), default=len(target))
    return unquote(target[:cut]) or None
