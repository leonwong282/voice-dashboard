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

- Review and document request retry boundaries.
- Review and document timeout behavior.
- Make overwrite rules explicit for existing output directories.
- Ensure merge cleanup never removes artifacts after a partial failure.
- Verify exit codes remain stable for:
  - input errors
  - config errors
  - auth errors
  - dependency errors
  - API errors

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
