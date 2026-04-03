# voice-dashboard Product Roadmap

This roadmap defines how `voice-dashboard` should evolve from a repository-installable batch TTS utility into a professional open source CLI that users can install with `pip` or Homebrew and use reliably from the terminal.

## 1. Product Goal

The target state is a CLI tool that meets the following bar:

- Installable from Python packaging without cloning the repository.
- Installable from Homebrew with a stable formula and release artifacts.
- Predictable CLI UX with clear help text, version reporting, config management, and actionable errors.
- Clean release engineering with CI, repeatable builds, and documented release steps.
- Maintained like a real project rather than a personal script.

## 2. Current Baseline

The project already has a usable starting point:

- A Python package with a console entrypoint: `ttsrun`.
- A working batch TTS flow with file, stdin, and macOS clipboard input.
- A basic config model, manifest output, and merge flow.
- Initial unit tests for core CLI and pipeline behavior.

The project is not yet at product level because it still depends on repository-local installation habits, thin packaging metadata, manual release work, platform-specific assumptions, and a minimal quality pipeline.

## 3. Definition Of Done For v1.0

`voice-dashboard` can be considered product-grade when all of the following are true:

- Users can run `pipx install voice-dashboard` or `pip install voice-dashboard` from published artifacts.
- Users can run `brew install <tap>/voice-dashboard` from a maintained Homebrew tap.
- `ttsrun --help` and `ttsrun --version` work in a clean environment.
- The CLI has clear config commands, doctor checks, and stable exit codes.
- CI validates linting, tests, and package builds on supported Python versions.
- GitHub releases and PyPI releases are created from a repeatable tag-based workflow.
- Repository hygiene is clean: no generated artifacts tracked in git, no manual build leftovers, and no duplicated version sources.

## 4. Roadmap Principles

- Prioritize distributability before adding many new features.
- Prefer predictable CLI behavior over clever shortcuts.
- Treat packaging, docs, tests, and release automation as product features.
- Keep scope tight until install and release workflows are solid.
- Target macOS and Linux first; Windows support can improve incrementally after the core release pipeline is stable.

## 5. Milestones

### Milestone P0: Packaging And Repository Foundation

Status: completed on 2026-04-03.

Target outcome: a clean Python project that can be built, tested, and prepared for publication in a repeatable way.

Key work:

- Expand `pyproject.toml` metadata:
  - add `readme`
  - add `license` metadata
  - add `authors`
  - add `keywords`
  - add `classifiers`
  - add `project.urls`
  - add optional dependency groups for development
- Move to a single source of truth for versioning.
- Add `.gitignore` and stop tracking generated files such as `build/`, `*.egg-info/`, and `__pycache__/`.
- Add a documented development bootstrap flow.
- Add build and test commands that work in a clean environment.
- Add CI for at least:
  - package build
  - test execution
  - basic style or lint checks

Acceptance criteria:

- A fresh clone can run the documented setup and complete tests successfully.
- `python -m build` works in CI.
- The git tree stays clean after local build and test commands.
- Release metadata is complete enough for PyPI display without manual editing.

Completion notes:

- Packaging metadata was expanded in `pyproject.toml`.
- Versioning now uses a single source of truth from the package module.
- Generated artifacts were removed from version control and ignored going forward.
- Local contributor commands were documented and codified in `Makefile`.
- CI now runs lint, tests, and package build validation.

Suggested release label:

- `0.2.0`

### Milestone P1: CLI Productization

Status: completed on 2026-04-03.

Target outcome: a CLI that feels intentional and maintainable, not just functional.

Key work:

- Add `--version`.
- Add explicit config-oriented commands or workflows, for example:
  - `ttsrun config path`
  - `ttsrun config init`
  - `ttsrun doctor`
- Define stable exit code semantics for:
  - invalid user input
  - config errors
  - API failures
  - dependency failures such as missing `ffmpeg`
- Improve error messages so they tell users what to do next.
- Review output behavior:
  - support quiet or verbose modes
  - keep stdout and stderr roles consistent
  - consider machine-readable summary output for automation
- Reduce platform-specific assumptions:
  - abstract clipboard support
  - use better config and output path conventions
  - make open-folder behavior explicit and portable
- Refactor the internal structure so the CLI layer, provider client, file output, and OS integration are easier to test independently.

Progress notes:

- `--version` is implemented.
- Command-oriented management workflows now include `ttsrun doctor`, `ttsrun config path`, `ttsrun config show`, `ttsrun config example`, and `ttsrun config init`.
- Legacy management flags such as `--doctor`, `--print-config-path`, and `--init-config` remain available as a compatibility layer.
- Exit codes are now category-specific for config, input, auth, API, and dependency failures.
- Clipboard support no longer assumes macOS only.
- Progress output now supports `--quiet` and `--verbose`.
- `--json-summary` provides machine-readable batch summaries on stdout.
- CI now includes a lightweight installed-CLI smoke layer for `ttsrun --help`, `ttsrun doctor`, and config commands.
- Config resolution now prefers an XDG-style path for new users while preserving legacy `~/.voice-dashboard.json` installs.
- Legacy management flags now print deprecation guidance toward the command-oriented interface.

Acceptance criteria:

- Users can discover version, config location, and environment issues from the CLI itself.
- Common failure modes produce clear messages and stable non-zero exit codes.
- macOS and Linux behavior is documented and tested where practical.
- The CLI surface is coherent enough to remain stable through `1.0`.

Completion notes:

- The CLI now has a command-oriented management surface with `doctor`, `config`, and explicit `run` entrypoints.
- Legacy management flags remain available as a deprecated compatibility layer with migration guidance.
- Exit codes, progress streams, machine-readable summaries, and smoke checks are now stable enough to carry into distribution work.

Suggested release label:

- `0.3.0`

### Milestone P2: Distribution And Install Channels

Target outcome: end users can install the tool without cloning the repository.

Key work:

- Publish the package to PyPI.
- Recommend `pipx` for isolated CLI installation.
- Produce release artifacts on GitHub tags:
  - source distribution
  - wheel
- Create and maintain a Homebrew tap.
- Add a Homebrew formula that installs the CLI cleanly and declares dependencies where needed.
- Document installation paths:
  - PyPI
  - pipx
  - Homebrew
  - source install for contributors
- Add smoke tests for post-install CLI behavior.

Acceptance criteria:

- A user can install the current release from PyPI and run `ttsrun --help`.
- A user can install from Homebrew and run the same CLI successfully.
- Tagging a release produces the expected artifacts without ad hoc manual steps.

Suggested release label:

- `0.4.0`

### Milestone P3: Reliability, Supportability, And v1.0 Readiness

Target outcome: the project is credible as a maintained CLI product.

Key work:

- Add broader test coverage:
  - integration-style CLI tests
  - config edge cases
  - packaging smoke tests
  - release workflow validation
- Improve operational resilience:
  - better retry boundaries
  - clearer timeout behavior
  - safer merge and cleanup handling
  - more explicit overwrite rules
- Write maintainer-facing process docs:
  - release checklist
  - support policy
  - compatibility policy
- Tighten documentation around prerequisites, supported platforms, and expected environment variables.
- Review licensing, contribution guidance, and issue templates for public maintenance.

Acceptance criteria:

- Maintainers can release confidently from a written checklist.
- Users can install and use the tool through documented channels without guessing.
- The project has a clear support boundary and stable public interface.

Suggested release label:

- `1.0.0`

## 6. Recommended Execution Order

1. Finish P0 before adding new user-facing features.
2. Start P1 only after packaging, build, and CI basics are stable.
3. Start P2 only after the CLI contract is stable enough that install docs will not churn every week.
4. Use P3 to lock down reliability and maintainer operations before declaring `1.0`.

## 7. Workstreams

These workstreams can run in parallel once P0 is underway:

- Packaging and metadata
- CLI UX and command design
- Test and CI infrastructure
- Release automation
- Installation and documentation

The only workstream that should stay on the critical path is packaging and release engineering, because Homebrew and PyPI distribution both depend on it.

## 8. Out Of Scope For The First Product Release

The following items may be valuable, but they should not block productization:

- GUI or desktop app wrappers
- Multi-provider TTS abstraction
- Cloud sync or hosted dashboard features
- Large-scale job orchestration
- Windows-first UX parity

## 9. Immediate Next Actions

The highest-value next moves are:

1. Prepare PyPI publishing so users can install the package without cloning the repository.
2. Normalize user-facing installation docs around `pip install`, `pipx install`, contributor install, and future Homebrew support.
3. Add tag-driven release automation for source distributions and wheels.
4. Define the initial Homebrew tap and formula strategy after the PyPI release path is stable.
5. Add post-install smoke checks that validate the published package rather than only editable installs.

## 10. Success Metrics

The roadmap is working if the project reaches these measurable outcomes:

- New users can install the tool in under five minutes from docs alone.
- Maintainers can cut a release from a git tag without editing files by hand.
- The CLI behavior is stable enough that installation docs do not need frequent rewrites.
- Reported issues shift from setup problems to real product feedback.
