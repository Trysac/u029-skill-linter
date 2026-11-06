# Testing

## Running

```sh
uv run pytest --cov=skill_linter   # tests with coverage report
uv run python scripts/check.py      # every gate, as CI runs it
```

## Policy

- Branch coverage of `src/skill_linter` is gated at 80 %.
- Tests exercise the public API and the CLI, and assert return values, findings, exit codes and stderr messages.
- Each bug fix starts with a failing test that reproduces it.

## Layout

The suite is built on the acceptance literals of the specification: frontmatter fences and required fields (S001, S002), name rules (S003, S009), description limits and trigger cues (S004, S005, S009), the body line budget (S006), link resolution (S007, S008), output formats, exit codes, file size and encoding limits, and the findings cap.
