# Project record

## Objective

Agent skills live as SKILL.md files whose frontmatter description decides when the model loads them, yet nothing checks them in CI. skill-lint validates skill folders against the published Agent Skills format with stable rule ids and machine-readable output.

## Scope

- In scope: rules S000 to S009; `lint_skill` and `lint_tree`; a `python -m skill_linter` CLI with text or JSON output, `--strict`, `--max-body-lines` and `--max-findings`; a stdlib-only frontmatter subset parser and link scanner.
- Out of scope: auto-fix, LLM scoring, marketplace manifests, reference-style links, validation of `allowed-tools` values.

## Timeline

| Date | Event |
|---|---|
| 2026 | Repository created from the factory utility template. |

## Effort metrics

Measured values only; a value that has not been measured stays "pending measurement".

| Metric | Value |
|---|---|
| Tokens (input / output) | pending measurement |
| Hours (human) | pending measurement |
| Cost (USD) | pending measurement |
