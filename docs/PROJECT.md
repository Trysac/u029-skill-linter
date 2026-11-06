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
| Tokens (input / output) | 334250 / 99289 |
| Hours (human) | pending measurement |
| Cost (USD) | 0.6840 |

## Factory run u029 (measured from API usage)

| Phase | Model | Batch | Input | Output | Cache write | Cache read | Cost (USD) |
|---|---|---|---|---|---|---|---|
| generation | claude-sonnet-5-5 | yes | 2615 | 91366 | 0 | 4246 | 0.4599 |
| fix-1 | claude-sonnet-5-5 | no | 4 | 280 | 5721 | 24501 | 0.0196 |
| fix-2 | claude-sonnet-5-5 | no | 8 | 2276 | 14511 | 69653 | 0.0660 |
| fix-3 | claude-sonnet-5-5 | no | 6 | 383 | 6101 | 39838 | 0.0231 |
| fix-4 | claude-sonnet-5-5 | no | 8 | 1072 | 8903 | 59977 | 0.0390 |
| docs | claude-haiku-5-5 | no | 133394 | 3912 | 0 | 0 | 0.0765 |

Total: $0.6840. Prices: Anthropic list prices.
