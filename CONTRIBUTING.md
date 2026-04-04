# Contributing

Thanks for contributing to `voice-dashboard`.

## 1. Development Setup

Use the contributor workflow from [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Before opening a change, run:

```bash
make check
```

For release-oriented validation, also run:

```bash
make release-smoke
```

## 2. Scope Expectations

The project currently prioritizes:

- stable CLI behavior
- packaging and release quality
- macOS and Linux support
- predictable automation-friendly output

Changes that expand the public interface, supported platforms, or release behavior should update the relevant docs in `docs/`.

## 3. Reporting Bugs

Prefer the GitHub bug report template. Good bug reports include:

- the installed version
- install channel
- Python version
- OS
- the exact command used
- stderr output
- relevant `manifest.json` or `errors.jsonl` snippets when available

## 4. Submitting Changes

- Keep changes focused.
- Add or update tests when behavior changes.
- Do not commit generated artifacts such as `dist/`, `build/`, `*.egg-info/`, or `__pycache__/`.
- If you change release, install, or support behavior, update:
  - [docs/RELEASING.md](docs/RELEASING.md)
  - [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md)
  - [docs/USAGE.md](docs/USAGE.md)
  - [README.md](README.md)

## 5. Triage And Validation

When validating a fix:

- reproduce the problem first when possible
- prefer adding a regression test before or alongside the fix
- use `ttsrun doctor` and the CLI smoke commands for environment-sensitive issues
- verify install-path issues through the published smoke tooling when relevant:

```bash
python scripts/verify_public_install.py --package-spec dist/*.whl
```

## 6. Support Boundary

Contributions should respect the current support policy in [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md). New platform or packaging claims should not be documented unless they are backed by tests and repeatable validation.
