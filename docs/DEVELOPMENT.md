# Development Guide

This guide covers the local contributor workflow for `voice-dashboard`.

## 1. Prerequisites

- Python 3.10 or newer
- `ffmpeg` if you want to exercise merge behavior manually

## 2. Bootstrap

Create a virtual environment at the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

This installs the package in editable mode plus the development toolchain defined in `pyproject.toml`.

## 3. Common Commands

Run all local quality gates:

```bash
make check
```

Run individual steps:

```bash
make lint
make test
make smoke
make build
make dist-sha256
make homebrew-formula SOURCE_URL=... SOURCE_SHA256=...
make release-smoke
```

If you prefer not to use `make`, the equivalent commands are:

```bash
python -m pyflakes voice.py voice_dashboard tests scripts
python -m pytest -q
ttsrun --help
MINIMAX_API_KEY=smoke-test-key ttsrun doctor
python -m build
python -m twine check dist/*
```

## 4. CLI Smoke Check

After the editable install succeeds, verify the CLI entrypoint:

```bash
ttsrun --help
ttsrun --version
MINIMAX_API_KEY=smoke-test-key ttsrun doctor
ttsrun config path
ttsrun config example
```

## 5. Repository Hygiene

Generated artifacts are not tracked in git. Before committing, the working tree should not include:

- `build/`
- `dist/`
- `*.egg-info/`
- `__pycache__/`

Clean local build artifacts with:

```bash
make clean
```

## 6. CI Expectations

The CI workflow validates three things on every change:

- linting with Pyflakes
- tests with Pytest
- install-time CLI smoke checks through `ttsrun`
- package build validation with `python -m build`

Any local change should pass the same checks before release work begins.

For maintainer release steps, see `docs/RELEASING.md`.
