# P3 Checklist

This checklist turns Milestone P3 in `docs/ROADMAP.md` into concrete execution items.

## 1. Test Hardening

- Add subprocess-based CLI integration tests for:
  - `ttsrun --help`
  - `ttsrun --version`
  - `ttsrun doctor`
  - `ttsrun config path`
  - `ttsrun run <file>`
- Add config edge-case tests for:
  - invalid JSON config
  - missing config file
  - legacy config path fallback
  - XDG-style config path resolution
- Add dependency-failure tests for:
  - missing `ffmpeg`
  - unsupported clipboard backend
  - missing `MINIMAX_API_KEY`
- Add tests for `scripts/verify_public_install.py` retry behavior.
- Verify CI runs the new integration coverage.

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
