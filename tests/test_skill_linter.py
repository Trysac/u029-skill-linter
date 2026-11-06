"""Behavior tests for the public API of skill_linter."""

from __future__ import annotations

import pytest

import skill_linter


def test_normalize_trims_and_lowercases() -> None:
    assert skill_linter.normalize("  Hello World ") == "hello world"


@pytest.mark.parametrize("value", ["", "   ", "\t\n"])
def test_normalize_rejects_blank_input(value: str) -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        skill_linter.normalize(value)


def test_version_is_semver() -> None:
    parts = skill_linter.__version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)
