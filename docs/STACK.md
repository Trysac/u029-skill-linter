# Stack

## Used

| Tool | Why |
|---|---|
| Python >= 3.10 | Widest supported range that still allows modern typing syntax. |
| uv | Fast, reproducible environments and builds. |
| hatchling | Standards-based build backend; no setup.py. |
| ruff | Lint and format in one tool. |
| mypy (strict) | Type checking; the package ships `py.typed`. |
| pytest + pytest-cov | Test runner with coverage. |
| gitleaks | Secret scanning locally and in CI. |
| GitHub Actions + Dependabot | CI and dependency updates. |

Runtime dependencies: none. The package uses only the standard library.

## Discarded

| Tool | Why not |
|---|---|
| Poetry | uv covers the same needs with standard dependency groups. |
| black + isort + flake8 | Replaced by ruff. |
| tox / nox | The OS matrix lives in CI; locally `scripts/check.py` is enough. |
