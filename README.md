# skill-linter

[![PyPI version](https://img.shields.io/pypi/v/trysac-skill-linter)](https://pypi.org/project/trysac-skill-linter/)
[![License: MIT](https://img.shields.io/pypi/l/trysac-skill-linter)](LICENSE)
[![CI](https://github.com/Trysac/u029-skill-linter/actions/workflows/ci.yml/badge.svg)](https://github.com/Trysac/u029-skill-linter/actions/workflows/ci.yml)

Lint agent skill folders (SKILL.md) against the Agent Skills format: frontmatter, name rules, description limits, trigger cues and broken links

## Problem

Describe in two or three sentences the concrete problem this utility solves, who hits it, and what
they do today without it. Replace this paragraph when the first real feature lands.

## Install

```sh
pip install trysac-skill-linter
# or
uv add trysac-skill-linter
```

Requires Python 3.10 or newer. No runtime dependencies.

## Usage

```python
import skill_linter

# normalize() trims surrounding whitespace and lower-cases the text.
print(skill_linter.normalize("  Hello World "))  # -> "hello world"

# Blank input is rejected explicitly instead of returning an empty string.
try:
    skill_linter.normalize("   ")
except ValueError as exc:
    print(f"rejected: {exc}")
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) and [decisions](docs/decisions/)
- [Testing](docs/TESTING.md) and [security](docs/SECURITY.md)
- [Project record](docs/PROJECT.md) and [stack](docs/STACK.md)
- [Changelog](CHANGELOG.md) and [contributing guide](CONTRIBUTING.md)

## License

[MIT](LICENSE) (c) 2026 Miguel Gomez
