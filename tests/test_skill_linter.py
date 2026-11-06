"""Tests for the skill_linter public API and command line interface."""

from __future__ import annotations

import json
import os
import runpy
import sys
from pathlib import Path

import pytest

import skill_linter.__main__ as cli
import skill_linter.linter as linter_module
from skill_linter import RULES, Finding, LintConfig, SkillLintError, lint_skill, lint_tree
from skill_linter.frontmatter import parse_frontmatter
from skill_linter.links import iter_link_targets, normalize_target
from skill_linter.textutil import quote

GOOD = "---\nname: a\ndescription: Use when x\n---\n"
needs_symlink = pytest.mark.skipif(not hasattr(os, "symlink"), reason="no symlink support")

OK_LINKS = (
    '[a](refs/ok.md "T")\n'
    "[a](<refs/ok file.md>)\n"
    "[a](refs/ok.md#part)\n"
    "[a](refs/ok%20file.md)\n"
    "[a](refs/ok(1).md)\n"
    "![img](refs/ok.md)\n"
    "[a](refs/ok.md?x=1)\n"
)

IGNORED_LINKS = (
    "```\n[a](refs/missing.md)\n```\n"
    "~~~\n[a](refs/missing.md)\n~~~\n"
    "`[a](refs/missing.md)`\n"
    "[a](https://x.y)\n"
    "[a](#top)\n"
    "[a](mailto:a@b)\n"
    "[a](/abs/path.md)\n"
)


def write_skill(root: Path, folder: str, text: str) -> Path:
    """Create ``root/folder/SKILL.md`` with exact bytes and return the folder."""
    directory = root / folder
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "SKILL.md").write_bytes(text.encode("utf-8"))
    return directory


def rules_of(findings: list[Finding]) -> list[str]:
    return [finding.rule for finding in findings]


def make_refs(skill: Path) -> None:
    refs = skill / "refs"
    refs.mkdir(exist_ok=True)
    for name in ("ok.md", "ok file.md", "ok(1).md"):
        (refs / name).write_text("ok", encoding="utf-8")


# --- frontmatter fences and required fields -------------------------------------------


@pytest.mark.parametrize("text", ["name: a\n", "---\nname: a\n"])
def test_fence_problems_are_s001(tmp_path: Path, text: str) -> None:
    skill = write_skill(tmp_path, "a", text)
    findings = lint_skill(skill)
    assert [(f.rule, f.severity, f.line) for f in findings] == [("S001", "error", 1)]
    assert cli.main([str(skill)]) == 1


def test_empty_file_is_s001(tmp_path: Path) -> None:
    skill = write_skill(tmp_path, "a", "")
    assert [(f.rule, f.line) for f in lint_skill(skill)] == [("S001", 1)]


def test_missing_description_is_s002(tmp_path: Path) -> None:
    skill = write_skill(tmp_path, "a", "---\nname: a\n---\n")
    findings = lint_skill(skill)
    assert [(f.rule, f.line) for f in findings] == [("S002", 1)]
    assert cli.main([str(skill)]) == 1


def test_missing_name_and_blank_description_are_s002(tmp_path: Path) -> None:
    skill = write_skill(tmp_path, "a", "---\ndescription: ' '\n---\n")
    assert rules_of(lint_skill(skill)) == ["S002", "S002"]


def test_non_scalar_name_is_s001(tmp_path: Path) -> None:
    skill = write_skill(tmp_path, "a", "---\nname:\n  k: v\ndescription: Use when x\n---\n")
    assert [(f.rule, f.line) for f in lint_skill(skill)] == [("S001", 2)]


def test_syntax_error_still_checks_the_body(tmp_path: Path) -> None:
    skill = write_skill(tmp_path, "a", "---\nname: [a]\n---\n[a](missing.md)\n")
    assert [(f.rule, f.line) for f in lint_skill(skill)] == [("S001", 2), ("S007", 4)]


def test_optional_fields(tmp_path: Path) -> None:
    text = GOOD.replace("---\n", "---\n", 1)[:-4] + "metadata: nope\n---\n"
    assert [(f.rule, f.line) for f in lint_skill(write_skill(tmp_path, "a", text))] == [("S001", 4)]
    text = GOOD[:-4] + "compatibility: " + "x" * 501 + "\n---\n"
    assert [(f.rule, f.line) for f in lint_skill(write_skill(tmp_path, "b", text))] == []
    text = text.replace("name: a", "name: b")
    assert [(f.rule, f.line) for f in lint_skill(write_skill(tmp_path, "b", text))] == [("S004", 4)]
    text = GOOD[:-4] + "compatibility: " + "x" * 500 + "\nmetadata:\n  k: v\n---\n"
    assert lint_skill(write_skill(tmp_path, "a", text)) == []


# --- names ------------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["My-Skill", "-a", "a--b", "ab-", "a" * 65])
def test_invalid_names_are_s003(tmp_path: Path, name: str) -> None:
    skill = write_skill(tmp_path, name, f"---\nname: {name}\ndescription: Use when x\n---\n")
    assert rules_of(lint_skill(skill)) == ["S003"]


def test_name_must_match_folder(tmp_path: Path) -> None:
    skill = write_skill(tmp_path, "pdf", "---\nname: pdf-tools\ndescription: Use when x\n---\n")
    findings = lint_skill(skill)
    assert [(f.rule, f.line) for f in findings] == [("S003", 2)]
    assert "does not match folder" in findings[0].message


def test_reserved_word_is_s009(tmp_path: Path) -> None:
    text = "---\nname: claude-pdf\ndescription: Use when x\n---\n"
    assert rules_of(lint_skill(write_skill(tmp_path, "claude-pdf", text))) == ["S009"]
    text = text.replace("claude-pdf", "my-anthropic")
    assert rules_of(lint_skill(write_skill(tmp_path, "my-anthropic", text))) == ["S009"]


def test_xml_tag_in_name_is_s003_and_s009(tmp_path: Path) -> None:
    skill = write_skill(tmp_path, "x", "---\nname: x<b>\ndescription: Use when x\n---\n")
    assert rules_of(lint_skill(skill)) == ["S003", "S009"]


def test_matching_name_is_clean(tmp_path: Path) -> None:
    text = "---\nname: pdf-tools\ndescription: Use when x\n---\n"
    assert lint_skill(write_skill(tmp_path, "pdf-tools", text)) == []


# --- description ------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("description", "expected"),
    [
        ("Use when " + "x" * 1016, ["S004"]),
        ("Use when " + "x" * 1015, []),
        ("Use when <b>bold</b>", ["S009"]),
        ("Use when a < b and b > c", []),
        ("Formats tables.", ["S005"]),
    ],
)
def test_description_rules(tmp_path: Path, description: str, expected: list[str]) -> None:
    skill = write_skill(tmp_path, "a", f"---\nname: a\ndescription: {description}\n---\n")
    assert rules_of(lint_skill(skill)) == expected


def test_trigger_cue_is_a_warning(tmp_path: Path) -> None:
    skill = write_skill(tmp_path, "a", "---\nname: a\ndescription: Formats tables.\n---\n")
    findings = lint_skill(skill)
    assert [(f.rule, f.severity, f.line) for f in findings] == [("S005", "warning", 3)]
    assert findings[0].message == "description has no trigger cue (e.g. 'use when')"


def test_trigger_cues_are_case_insensitive_and_configurable(tmp_path: Path) -> None:
    text = "---\nname: a\ndescription: USE WHEN reading\n---\n"
    assert lint_skill(write_skill(tmp_path, "a", text)) == []
    text = "---\nname: a\ndescription: Formats tables.\n---\n"
    skill = write_skill(tmp_path, "a", text)
    assert lint_skill(skill, LintConfig(trigger_cues=("formats",))) == []
    assert lint_skill(skill, LintConfig(trigger_cues=())) == []
    assert rules_of(lint_skill(skill, LintConfig(max_description=5))) == ["S004", "S005"]


def test_folded_and_literal_descriptions(tmp_path: Path) -> None:
    text = "---\nname: a\ndescription: >\n  Use when\n  reading\n---\n"
    assert lint_skill(write_skill(tmp_path, "a", text)) == []
    text = "---\nname: a\ndescription: |\n  Formats\n  tables\n---\n"
    assert rules_of(lint_skill(write_skill(tmp_path, "a", text))) == ["S005"]


# --- body budget ------------------------------------------------------------------------


def test_body_budget_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    write_skill(tmp_path, "a", GOOD + "x\n" * 501)
    monkeypatch.chdir(tmp_path)
    assert cli.main(["a"]) == 0
    captured = capsys.readouterr()
    assert captured.out == "a/SKILL.md:505: warning S006 body has 501 lines (max 500)\n"
    assert captured.err == ""


def test_body_at_budget_prints_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    write_skill(tmp_path, "a", GOOD + "x\n" * 500)
    monkeypatch.chdir(tmp_path)
    assert cli.main(["a"]) == 0
    captured = capsys.readouterr()
    assert (captured.out, captured.err) == ("", "")


def test_body_budget_is_configurable_and_handles_crlf_and_bom(tmp_path: Path) -> None:
    skill = write_skill(tmp_path, "a", GOOD + "x\nx\n")
    findings = lint_skill(skill, LintConfig(max_body_lines=1))
    assert [(f.rule, f.line, f.message) for f in findings] == [
        ("S006", 6, "body has 2 lines (max 1)")
    ]
    crlf = GOOD.replace("\n", "\r\n") + "x\r\n" * 501
    findings = lint_skill(write_skill(tmp_path, "b", crlf.replace("name: a", "name: b")))
    assert [(f.rule, f.line) for f in findings] == [("S006", 505)]
    assert lint_skill(write_skill(tmp_path, "a", "\ufeff" + GOOD)) == []


# --- links ------------------------------------------------------------------------------


def test_missing_link_is_s007_at_its_line(tmp_path: Path) -> None:
    skill = write_skill(tmp_path, "a", GOOD + "[a](refs/missing.md).\n")
    assert [(f.rule, f.line) for f in lint_skill(skill)] == [("S007", 5)]


def test_existing_links_are_clean(tmp_path: Path) -> None:
    skill = write_skill(tmp_path, "a", GOOD + OK_LINKS)
    make_refs(skill)
    assert lint_skill(skill) == []


def test_ignored_links_are_not_checked(tmp_path: Path) -> None:
    skill = write_skill(tmp_path, "a", GOOD + IGNORED_LINKS)
    assert lint_skill(skill) == []


@needs_symlink
@pytest.mark.parametrize(
    "link",
    ["[a](../x.md)\n", "[a](link.md)\n", "[a](%2Fetc%2Fpasswd)\n"],
)
def test_escaping_links_are_s008(tmp_path: Path, link: str) -> None:
    skill = write_skill(tmp_path, "a", GOOD + link)
    outside = tmp_path / "outside.md"
    outside.write_text("x", encoding="utf-8")
    (skill / "link.md").symlink_to(outside)
    assert [(f.rule, f.line) for f in lint_skill(skill)] == [("S008", 5)]


@needs_symlink
def test_symlink_loop_and_nul_targets_are_s007(tmp_path: Path) -> None:
    skill = write_skill(tmp_path, "a", GOOD + "[a](loop.md)\n[a](%00.md)\n")
    (skill / "loop.md").symlink_to("loop.md")
    assert [(f.rule, f.line) for f in lint_skill(skill)] == [("S007", 5), ("S007", 6)]


def test_adjacent_links_are_both_checked(tmp_path: Path) -> None:
    skill = write_skill(tmp_path, "a", GOOD + "see [a](x.md)[b](y.md), and [c](z.md).\n")
    assert rules_of(lint_skill(skill)) == ["S007", "S007", "S007"]


def test_fence_handling(tmp_path: Path) -> None:
    body = "```\n~~~\n[a](m.md)\n```\n[b](after.md)\n"
    assert [(f.rule, f.line) for f in lint_skill(write_skill(tmp_path, "a", GOOD + body))] == [
        ("S007", 8)
    ]
    body = "````\n```\n[a](m.md)\n````\n[b](after.md)\n"
    assert [(f.rule, f.line) for f in lint_skill(write_skill(tmp_path, "a", GOOD + body))] == [
        ("S007", 9)
    ]
    assert lint_skill(write_skill(tmp_path, "a", GOOD + "```\n[a](m.md)\n")) == []


def test_iter_link_targets_details() -> None:
    assert list(iter_link_targets(["[a](x.md)[b](y.md)"], 10)) == [(10, "x.md"), (10, "y.md")]
    assert list(iter_link_targets(["`[a](x.md)` and [b](y.md)"], 1)) == [(1, "y.md")]
    assert list(iter_link_targets(["``a ` b`` [c](z.md)"], 1)) == [(1, "z.md")]
    assert list(iter_link_targets(["a ` [b](y.md)"], 1)) == [(1, "y.md")]
    assert list(iter_link_targets(['[a](x.md "T")', "[a](x(1).md)"], 1)) == [
        (1, "x.md"),
        (2, "x(1).md"),
    ]
    assert list(iter_link_targets(["[a](<x y.md>)"], 1)) == [(1, "<x y.md>")]
    assert list(iter_link_targets(["```a``` [b](y.md)"], 1)) == [(1, "y.md")]
    assert list(iter_link_targets(["[a] (x.md)", "a](x.md)", "[a](x.md"], 1)) == []


@pytest.mark.parametrize(
    "line",
    ["[" * 50000, "](" * 50000, "`" * 50000 + "[a](x.md)", "[a" * 25000],
)
def test_pathological_lines_stay_linear(line: str) -> None:
    assert isinstance(list(iter_link_targets([line], 1)), list)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("refs/x.md", "refs/x.md"),
        ("<refs/x y.md>", "refs/x y.md"),
        ("refs/x.md#p", "refs/x.md"),
        ("refs/x.md?q=1", "refs/x.md"),
        ("refs/x%20y.md", "refs/x y.md"),
        ("#top", None),
        ("/abs", None),
        ("https://x.y", None),
        ("mailto:a@b", None),
        ("?q", None),
        ("<#x>", None),
    ],
)
def test_normalize_target(raw: str, expected: str | None) -> None:
    assert normalize_target(raw) == expected


# --- output formats and exit codes -----------------------------------------------------


def test_json_output_is_sorted_with_exact_keys(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_skill(tmp_path, "b", "---\nname: b\n---\n")
    write_skill(tmp_path, "a", "---\nname: a\ndescription: Formats tables.\n---\n")
    assert cli.main([str(tmp_path), "--format", "json"]) == 1
    rows = json.loads(capsys.readouterr().out)
    assert len(rows) == 2
    assert all(list(row) == ["path", "line", "rule", "severity", "message"] for row in rows)
    keys = [(row["path"], row["line"], row["rule"]) for row in rows]
    assert keys == sorted(keys)


def test_text_format_line(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    skill = write_skill(tmp_path, "a", "---\nname: a\ndescription: Formats tables.\n---\n")
    assert cli.main([str(skill)]) == 0
    path = (skill / "SKILL.md").as_posix()
    expected = f"{path}:3: warning S005 description has no trigger cue (e.g. 'use when')\n"
    assert capsys.readouterr().out == expected


def test_json_output_for_clean_skill(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    skill = write_skill(tmp_path, "a", GOOD)
    assert cli.main([str(skill), "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out) == []


def test_warnings_exit_zero_and_strict_exits_one(tmp_path: Path) -> None:
    skill = write_skill(tmp_path, "a", "---\nname: a\ndescription: Formats tables.\n---\n")
    assert cli.main([str(skill)]) == 0
    assert cli.main([str(skill), "--strict"]) == 1
    clean = write_skill(tmp_path, "c", GOOD.replace("name: a", "name: c"))
    assert cli.main([str(clean), "--strict"]) == 0


def test_missing_path_and_no_path_exit_two(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli.main([str(tmp_path / "nope")]) == 2
    assert capsys.readouterr().err.startswith("skill-lint: path not found")
    assert cli.main([]) == 2
    assert cli.main(["a\x00b"]) == 2
    assert cli.main(["--help"]) == 0
    assert cli.main(["x", "--max-body-lines", "-1"]) == 2
    assert cli.main(["x", "--max-body-lines", "abc"]) == 2


def test_other_file_and_io_errors_exit_two(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    other = tmp_path / "x.txt"
    other.write_text("x", encoding="utf-8")
    assert cli.main([str(other)]) == 2
    assert "not a folder or SKILL.md" in capsys.readouterr().err

    def boom(path: object) -> os.stat_result:
        raise PermissionError

    monkeypatch.setattr(cli, "_stat", boom)
    assert cli.main([str(tmp_path)]) == 2
    assert "cannot access path" in capsys.readouterr().err


def test_oversize_and_non_utf8_files_are_s000(tmp_path: Path) -> None:
    big = tmp_path / "big"
    big.mkdir()
    (big / "SKILL.md").write_bytes(b"x" * 1_048_577)
    findings = lint_skill(big)
    assert [(f.rule, f.severity, f.line) for f in findings] == [("S000", "error", 1)]
    assert cli.main([str(big)]) == 1
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "SKILL.md").write_bytes(b"---\nname: a\n\xff---\n")
    assert [(f.rule, f.line) for f in lint_skill(bad)] == [("S000", 1)]
    exact = tmp_path / "exact"
    exact.mkdir()
    (exact / "SKILL.md").write_bytes(b"x" * 1_048_576)
    assert rules_of(lint_skill(exact)) == ["S001"]


def test_missing_directory_and_unreadable_files_are_s000(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert rules_of(lint_skill(tmp_path)) == ["S000"]
    directory = tmp_path / "d"
    (directory / "SKILL.md").mkdir(parents=True)
    assert "not a regular file" in lint_skill(directory)[0].message
    skill = write_skill(tmp_path, "a", GOOD)

    def boom(self: Path, *args: object, **kwargs: object) -> None:
        raise PermissionError

    monkeypatch.setattr(Path, "open", boom)
    assert rules_of(lint_skill(skill)) == ["S000"]


@needs_symlink
def test_symlinked_skill_file_is_s000(tmp_path: Path) -> None:
    real = tmp_path / "real.md"
    real.write_text(GOOD, encoding="utf-8")
    folder = tmp_path / "a"
    folder.mkdir()
    (folder / "SKILL.md").symlink_to(real)
    findings = lint_skill(folder)
    assert [(f.rule, f.message) for f in findings] == [("S000", "SKILL.md is a symlink")]


def test_empty_directory_exits_zero(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main([str(tmp_path)]) == 0
    captured = capsys.readouterr()
    assert captured.err == "no SKILL.md found\n"
    assert captured.out == ""


# --- finding limit ----------------------------------------------------------------------


THREE_BROKEN = GOOD + "[a](r/1.md)\n[a](r/2.md)\n[a](r/3.md)\n"


def test_max_findings_truncates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    skill = write_skill(tmp_path, "a", THREE_BROKEN)
    assert len(lint_skill(skill, LintConfig(max_findings=2))) == 2
    assert len(lint_skill(skill, LintConfig(max_findings=3))) == 3
    monkeypatch.setattr(cli, "LintConfig", lambda: LintConfig(max_findings=2))
    assert cli.main([str(skill)]) == 1
    captured = capsys.readouterr()
    assert captured.err == "findings truncated at 2\n"
    assert len(captured.out.splitlines()) == 2


def test_max_findings_flag_and_no_false_truncation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    skill = write_skill(tmp_path, "a", THREE_BROKEN)
    assert cli.main([str(skill), "--max-findings", "3"]) == 1
    assert capsys.readouterr().err == ""
    assert cli.main([str(skill), "--max-findings", "1"]) == 1
    assert capsys.readouterr().err == "findings truncated at 1\n"
    assert cli.main([str(skill), "--max-body-lines", "0", "--max-findings", "10"]) == 1


def test_limit_is_shared_across_a_tree(tmp_path: Path) -> None:
    write_skill(tmp_path, "a", "---\nname: a\n---\n")
    write_skill(tmp_path, "b", "---\nname: b\n---\n")
    assert len(lint_tree(tmp_path, LintConfig(max_findings=1))) == 1
    assert len(lint_tree(tmp_path)) == 2


# --- tree walking and CLI paths -------------------------------------------------------


@needs_symlink
def test_lint_tree_walks_without_following_links(tmp_path: Path) -> None:
    write_skill(tmp_path, "skills/a", "---\nname: a\n---\n")
    write_skill(tmp_path, "skills/deep/er/b", "---\nname: b\n---\n")
    (tmp_path / "linked").symlink_to(tmp_path / "skills", target_is_directory=True)
    paths = {f.path for f in lint_tree(tmp_path)}
    assert paths == {
        (tmp_path / "skills/a/SKILL.md").as_posix(),
        (tmp_path / "skills/deep/er/b/SKILL.md").as_posix(),
    }


def test_lint_tree_file_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("a", "b", "c"):
        write_skill(tmp_path, name, GOOD.replace("name: a", f"name: {name}"))
    monkeypatch.setattr(linter_module, "MAX_SKILL_FILES", 2)
    assert len(linter_module.find_skill_dirs(tmp_path)) == 2
    assert lint_tree(tmp_path / "missing") == []


def test_cli_accepts_skill_file_and_deduplicates(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    skill = write_skill(tmp_path, "a", "---\nname: a\n---\n")
    assert cli.main([str(skill / "SKILL.md")]) == 1
    assert len(capsys.readouterr().out.splitlines()) == 1
    assert cli.main([str(skill), str(skill / "SKILL.md"), str(tmp_path)]) == 1
    assert len(capsys.readouterr().out.splitlines()) == 1


def test_module_entry_point(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["skill_linter", str(tmp_path)])
    monkeypatch.delitem(sys.modules, "skill_linter.__main__", raising=False)
    with pytest.raises(SystemExit) as excinfo:
        runpy.run_module("skill_linter", run_name="__main__")
    assert excinfo.value.code == 0


# --- frontmatter parser ------------------------------------------------------------------


def test_parse_scalars_and_blocks() -> None:
    lines = [
        "---",
        "# comment",
        "name: 'it''s' # trailing",
        'description: "a\\"b\\n"',
        "plain: value # note",
        "empty:",
        "folded: >",
        "  Use when",
        "  x",
        "",
        "literal: |",
        "  a",
        "    b",
        "",
        "  c",
        "metadata:",
        "  # nested comment",
        "  k: v",
        "  z: 'w'",
        "after: done",
        "---",
        "body",
    ]
    result = parse_frontmatter(lines)
    assert result.errors == ()
    assert result.fields == {
        "name": "it's",
        "description": 'a"b\n',
        "plain": "value",
        "empty": "",
        "folded": "Use when x",
        "literal": "a\n  b\n\nc",
        "metadata": {"k": "v", "z": "w"},
        "after": "done",
    }
    assert result.key_lines["after"] == 20
    assert result.body_start == 22


def test_parse_chomping_and_comment_only_values() -> None:
    result = parse_frontmatter(["---", "a: >-", "  x", "  y", "b: # c", "c: |+", "d: >", "---"])
    assert result.errors == ()
    assert result.fields == {"a": "x y", "b": "", "c": "", "d": ""}


def test_parse_fence_errors() -> None:
    assert parse_frontmatter([]).body_start is None
    assert parse_frontmatter(["---", "name: a"]).errors[0][0] == 1
    assert parse_frontmatter(["name: a"]).errors[0][0] == 1
    assert parse_frontmatter(["--- ", "name: a", "---  "]).errors == ()


@pytest.mark.parametrize(
    ("block", "line"),
    [
        (["name:a"], 2),
        (["name: a", "name: b"], 3),
        (["\tname: a"], 2),
        (["name: [a, b]"], 2),
        (["name: {a: b}"], 2),
        (["name: 'abc"], 2),
        (['name: "abc'], 2),
        (['name: "a\\qb"'], 2),
        (['name: "abc\\'], 2),
        (["name: 'a' b"], 2),
        (["metadata:", "  a:", "    b: c"], 4),
        (["metadata:", "  - x"], 3),
        (["metadata:", "  a: b", "  a: c"], 4),
        (["metadata:", "  a: >"], 3),
        (["description: >>"], 2),
        (["description: |x"], 2),
        (["  name: a"], 2),
        (["description: a", "  continued"], 3),
    ],
)
def test_unsupported_syntax_reports_its_line(block: list[str], line: int) -> None:
    result = parse_frontmatter(["---", *block, "---"])
    assert len(result.errors) == 1
    assert result.errors[0][0] == line
    assert result.errors[0][1].startswith("unsupported frontmatter syntax")
    assert result.body_start == len(block) + 3


# --- misc API -----------------------------------------------------------------------------


def test_rule_table() -> None:
    assert [rule.id for rule in RULES] == [f"S00{i}" for i in range(10)]
    assert {rule.id for rule in RULES if rule.severity == "warning"} == {"S005", "S006"}
    assert all(rule.source and rule.title for rule in RULES)


def test_error_type_and_quote() -> None:
    error = SkillLintError("io", "x" * 500)
    assert error.code == "io"
    assert len(str(error)) == 200
    assert quote("x" * 100) == "x" * 80 + "..."
    assert quote("a\nb") == "a?b"
    assert quote("short") == "short"


def test_long_content_is_quoted_in_messages(tmp_path: Path) -> None:
    name = "B" * 200
    skill = write_skill(tmp_path, "a", f"---\nname: {name}\ndescription: Use when x\n---\n")
    findings = lint_skill(skill)
    assert rules_of(findings) == ["S003"]
    assert "B" * 81 not in findings[0].message
