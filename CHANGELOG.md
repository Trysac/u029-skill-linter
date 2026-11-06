# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Add `skill_linter`: lint agent skill folders (`SKILL.md`) with rules S000-S009 (frontmatter, name, description, trigger cue, body budget, link targets), `lint_skill`/`lint_tree` and a `python -m skill_linter` CLI with text and JSON output.
- Initial project structure from the factory utility template.
