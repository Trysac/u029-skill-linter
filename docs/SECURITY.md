# Security notes

## Threat model

`trysac-skill-linter` reads SKILL.md files and linked paths. It is read-only, never executes content and has no runtime dependencies.

Defended:

- Symlinked directories are not followed while walking (`os.walk(followlinks=False)`).
- A SKILL.md that is a symlink is reported (S000) and not read.
- Files larger than `max_file_bytes` (default 1,048,576 bytes) are reported as S000 without parsing; non-UTF-8 files are reported as S000.
- Link targets resolving outside the skill folder are reported as S008.
- Findings stop at `max_findings` (default 10,000); `lint_tree` visits at most 10,000 SKILL.md files.
- Messages quote at most 80 characters of file content.

Not defended:

- Link existence is checked with `Path.exists`; the linter does not guard against races with concurrent file changes.
- Link scanning is limited to inline links, with a bounded nesting depth and target length; reference-style links are not checked.
- The frontmatter parser rejects unsupported YAML constructs rather than interpreting them, so hostile input is not evaluated but can still produce many findings up to the cap.

To report a vulnerability, see [SECURITY.md](../SECURITY.md).
