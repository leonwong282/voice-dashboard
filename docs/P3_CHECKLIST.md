# P3 Checklist

This checklist turns Milestone P3 in `docs/ROADMAP.md` into concrete execution items.

## 1. Test Hardening

- Done: add subprocess-based CLI integration tests for:
  - `ttsrun --help`
  - `ttsrun --version`
  - `ttsrun doctor`
  - `ttsrun config path`
  - `ttsrun config init`
  - `ttsrun config show`
  - `ttsrun run <file>` auth failure path
- Add config edge-case tests for:
  - Done: invalid JSON config
  - Done: missing config file
  - Done: legacy config path fallback
  - Done: XDG-style config path resolution
- Add dependency-failure tests for:
  - Done: missing `ffmpeg`
  - Done: unsupported clipboard backend
  - Done: missing `MINIMAX_API_KEY`
- Done: add tests for `scripts/verify_public_install.py` retry behavior.
- Done: CI already runs `pytest -q`, so the new integration coverage is part of the default test pipeline.

## 2. Operational Hardening

- Done: request retry boundaries are now configurable and documented through `--max-retries` / `max_retries`.
- Done: timeout behavior is now configurable and documented through `--request-timeout` / `request_timeout_seconds`.
- Done: overwrite rules are explicit for existing output directories; non-empty `--output-dir` now requires `--force-output-dir`.
- Done: merge cleanup now preserves artifacts safely by restoring segment files or keeping a backup directory when cleanup cannot finish.
- Verify exit codes remain stable for:
  - Done: input errors
  - Done: config errors
  - Done: auth errors
  - Done: dependency errors
  - Done: API errors

## 3. Maintainer Docs

- Add `docs/RELEASE_CHECKLIST.md`.
- Add a compatibility/support policy document.
- Add maintainer recovery steps for:
  - failed PyPI publish
  - failed Homebrew publish
  - failed GitHub Release creation
- Cross-link the new docs from `docs/RELEASING.md`.

## 4. Public Maintenance

- Add `.github/ISSUE_TEMPLATE/bug_report.yml`.
- Add `.github/ISSUE_TEMPLATE/feature_request.yml`.
- Decide whether to add `CONTRIBUTING.md` or expand `docs/DEVELOPMENT.md`.
- Clarify supported environments in docs:
  - Python versions
  - macOS / Linux support
  - external tools such as `ffmpeg`

## 5. Release Gate For 1.0.0

- CI passes with expanded tests.
- Release workflow passes without manual recovery.
- PyPI, `pipx`, and Homebrew install paths are all verified.
- Maintainer docs cover release, rollback, and recovery.
- Public support boundary is documented.
