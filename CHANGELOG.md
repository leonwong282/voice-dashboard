# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.3] - 2026-04-04

### Added
- Automated Homebrew tap publishing from the tag-driven release workflow, targeting `leonwong282/homebrew-tap`.
- A macOS Homebrew install smoke step in the release workflow to verify `brew install leonwong282/tap/voice-dashboard`.

### Changed
- Homebrew documentation and install docs now describe the published shared tap instead of a future/manual tap process.

## [0.4.2] - 2026-04-04

### Added
- Development guide at `docs/DEVELOPMENT.md` with bootstrap, lint, test, and build commands.
- GitHub Actions CI workflow for linting, tests, and package build validation.
- Product roadmap at `docs/ROADMAP.md`, covering the path from repository-local utility to distributable CLI product.
- `--version`, `--doctor`, `--print-config-path`, and `--init-config` management commands.
- Command-oriented CLI workflows with `ttsrun doctor`, `ttsrun config ...`, and `ttsrun run ...`.
- Category-specific exit codes for config, input, authentication, API, and dependency failures.
- `--quiet`, `--verbose`, and `--json-summary` output controls for scripting and automation.
- CLI smoke checks in `make smoke` and GitHub Actions to validate the installed `ttsrun` command.
- XDG-style default config discovery for new users, while preserving existing legacy config files.
- Deprecation warnings for legacy management flags, with command-oriented replacements.
- Tag-driven release workflow for GitHub Releases and PyPI publishing.
- Maintainer release guide at `docs/RELEASING.md`.
- `make release-smoke` to validate the built wheel in a clean virtual environment before publishing.
- Homebrew packaging guide and formula template for future tap maintenance.
- Scripted public-install verification for published packages and a manual GitHub Actions smoke workflow.
- Homebrew formula renderer for turning release metadata into a concrete formula body.
- Automated post-publish install verification and Homebrew formula artifacts in the main release workflow.
- Release checksum assets and PyPI-driven Homebrew formula rendering in the tag workflow.

### Changed
- Upgraded Python packaging metadata in `pyproject.toml` and moved to a single version source.
- Documentation language policy clarified: README is bilingual (English + Traditional Chinese), while usage documentation is maintained in English.
- Added repository ignore rules for generated build artifacts and local outputs.
- Split source install and contributor install guidance so user-facing docs no longer default to editable mode.
- Expanded clipboard support beyond macOS by detecting supported clipboard commands at runtime.
- Progress output now goes to stderr so stdout can stay clean for explicit command output.
- Documentation now treats subcommands as the primary management interface while keeping legacy flags as a compatibility layer.
- Default output paths now follow a more product-like convention under `~/Documents/voice-dashboard` when available.
- Installation docs now describe the intended `pipx` and PyPI paths for public releases.
- Release workflow now verifies that the pushed tag version matches `voice_dashboard.__version__` before publishing.

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

[Unreleased]: https://github.com/leonwong282/voice-dashboard/compare/v0.4.3...HEAD
[0.4.3]: https://github.com/leonwong282/voice-dashboard/releases/tag/v0.4.3
[0.4.2]: https://github.com/leonwong282/voice-dashboard/releases/tag/v0.4.2
[0.1.0]: https://github.com/leonwong282/voice-dashboard/releases/tag/v0.1.0
