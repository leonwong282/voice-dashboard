# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Development guide at `docs/DEVELOPMENT.md` with bootstrap, lint, test, and build commands.
- GitHub Actions CI workflow for linting, tests, and package build validation.
- Product roadmap at `docs/ROADMAP.md`, covering the path from repository-local utility to distributable CLI product.
- `--version`, `--doctor`, `--print-config-path`, and `--init-config` management commands.
- Command-oriented CLI workflows with `ttsrun doctor`, `ttsrun config ...`, and `ttsrun run ...`.
- Category-specific exit codes for config, input, authentication, API, and dependency failures.
- `--quiet`, `--verbose`, and `--json-summary` output controls for scripting and automation.
- CLI smoke checks in `make smoke` and GitHub Actions to validate the installed `ttsrun` command.

### Changed
- Upgraded Python packaging metadata in `pyproject.toml` and moved to a single version source.
- Documentation language policy clarified: README is bilingual (English + Traditional Chinese), while usage documentation is maintained in English.
- Added repository ignore rules for generated build artifacts and local outputs.
- Split source install and contributor install guidance so user-facing docs no longer default to editable mode.
- Expanded clipboard support beyond macOS by detecting supported clipboard commands at runtime.
- Progress output now goes to stderr so stdout can stay clean for explicit command output.
- Documentation now treats subcommands as the primary management interface while keeping legacy flags as a compatibility layer.

## [0.1.0] - 2026-04-03

### Added
- Initial `voice-dashboard` Python package metadata and CLI entrypoint `ttsrun`.
- English usage guide at `docs/USAGE.md` with workflows, output rules, config examples, and option references.

### Changed
- Replaced generic template README content with project-specific documentation for `voice-dashboard`.
- Added and aligned badges in both README variants (Version, Python, License, CLI).
- Restored standard README footer sections: License, Author, Acknowledgments, Support.

### Removed
- Removed legacy documentation files:
  - `README-old.md`
  - `docs/USAGE-old.md`

[Unreleased]: https://github.com/leonwong282/voice-dashboard/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/leonwong282/voice-dashboard/releases/tag/v0.1.0
