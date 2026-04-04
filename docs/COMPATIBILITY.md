# Compatibility And Support Policy

This document defines the supported environments and public support boundary for `voice-dashboard`.

## 1. Supported Python Versions

`voice-dashboard` officially supports:

- Python `3.10`
- Python `3.11`
- Python `3.12`

These versions are covered by CI in `.github/workflows/ci.yml`.

Later Python releases may work, but they are not part of the current support contract until CI and release validation cover them explicitly.

## 2. Supported Operating Systems

Official support currently targets:

- macOS
- Linux

Windows is not currently a supported first-class runtime target. Issues and fixes may still be accepted, but Windows behavior is best-effort until it is covered by tests, install validation, and documented workflows.

## 3. Supported Install Channels

The supported public install paths are:

- `pipx install voice-dashboard`
- `python -m pip install voice-dashboard`
- `brew install leonwong282/tap/voice-dashboard`

Source installs from a checked-out repository are supported for contributors, but they are not the primary end-user distribution path.

## 4. Required Runtime Environment

Required:

- `MINIMAX_API_KEY` must be set before batch synthesis.

Optional, depending on workflow:

- `ffmpeg` is required for `--merge`
- a clipboard command is required for `--clipboard`
  - `pbpaste`
  - `wl-paste`
  - `xclip`
  - `xsel`
- a folder opener is required for `--open`
  - `open`
  - `xdg-open`

If these optional tools are missing, `ttsrun doctor` should explain the gap and the relevant commands should fail with a stable non-zero exit code.

## 5. Public CLI Stability

The following interfaces are treated as public and should remain stable unless a documented breaking release is planned:

- the `ttsrun` command entrypoint
- the command-oriented management surface:
  - `ttsrun doctor`
  - `ttsrun config path`
  - `ttsrun config show`
  - `ttsrun config example`
  - `ttsrun config init`
  - `ttsrun run <input_path>`
- documented exit code categories
- JSON summary output from `--json-summary`
- generated manifest structure that automation depends on

Deprecated compatibility flags may be removed in a future breaking release, but they should continue to emit migration guidance before removal.

## 6. Support Expectations

Maintainers aim to support:

- the latest published release
- the current `main` branch for contributors
- regressions in the documented install channels
- reproducible bugs in supported Python and OS combinations

Maintainers do not guarantee:

- support for outdated package versions after newer releases ship
- support for undocumented environment combinations
- support for hand-edited or externally mutated output directories beyond the documented overwrite rules
- immediate fixes for third-party service outages or MiniMax-side API changes

## 7. What To Include In Bug Reports

When reporting a bug, include:

- installed version from `ttsrun --version`
- install channel: `pipx`, `pip`, or `Homebrew`
- Python version
- OS and shell
- whether `ffmpeg` or clipboard tooling is involved
- the exact command used
- stderr output or relevant `manifest.json` / `errors.jsonl` excerpts

Use the GitHub issue templates when possible so reports arrive with enough context to reproduce the problem.
