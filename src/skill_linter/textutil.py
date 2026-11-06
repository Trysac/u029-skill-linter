"""Small text helpers shared by the modules."""

from __future__ import annotations

__all__ = ["MAX_QUOTE", "quote"]

MAX_QUOTE = 80


def quote(text: str, limit: int = MAX_QUOTE) -> str:
    """Return at most ``limit`` characters of ``text`` that are safe to print on one line.

    Non-printable characters (including newlines) are replaced by ``?`` and a truncated
    value ends with ``...``.
    """
    clipped = text[:limit]
    safe = "".join(char if char.isprintable() else "?" for char in clipped)
    return safe + "..." if len(text) > limit else safe
