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

Status: completed on 2026-04-04.

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

Progress notes:

- A tag-driven `release.yml` workflow now builds distributions, runs install-from-wheel smoke checks, creates GitHub release assets, and publishes to PyPI via Trusted Publishing.
- Installation docs now describe the intended `pipx install voice-dashboard` and `pip install voice-dashboard` paths for public releases.
- Maintainer release steps are now documented in `docs/RELEASING.md`.
- A Homebrew packaging guide and formula template now exist so tap work can start from a repeatable baseline.
- A reusable public-install smoke workflow and helper script now exist for verifying published `pip` and `pipx` installation paths.
- A Homebrew formula renderer now converts the repository template plus resolved Python resources into a concrete formula body.
- The main release workflow now includes post-publish install verification from PyPI and publishes a rendered Homebrew formula artifact alongside the release assets.
- The release workflow now also publishes artifact checksums and renders the Homebrew formula from the published PyPI release metadata.
- A shared tap repository now exists at `leonwong282/homebrew-tap`.
- Tagged releases now push `Formula/voice-dashboard.rb` into the shared tap automatically when `HOMEBREW_TAP_TOKEN` is configured.
- The release workflow now verifies a real `brew install leonwong282/tap/voice-dashboard` on `macos-latest` before considering the release complete.

Suggested release label:

- `0.4.0`

### Milestone P3: Reliability, Supportability, And v1.0 Readiness

Status: completed on 2026-04-04.

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

Progress notes:

- P3.1 is complete: subprocess-based installed-CLI integration tests now cover the main command surface and failure paths.
- P3.2 is complete: request timeout/retry settings, output-directory overwrite rules, and merge-cleanup safety are now explicit, documented, and tested.
- P3.3 is complete: maintainer docs now include a release checklist, compatibility/support policy, and contributor-facing maintenance guidance.
- P3.4 is complete: GitHub issue templates, contact routing, and the public support boundary are now documented.
- The local release gate now passes through `make check release-smoke`, and the published PyPI/Homebrew install paths have already been verified in the tag-driven workflow.

Execution plan:

1. P3.1 Test Hardening
   - Add CLI integration tests that execute the installed command through subprocesses.
   - Add config-path and config-migration coverage for both XDG-style and legacy config locations.
   - Add failure-mode coverage for invalid config, missing API key, missing clipboard backend, and missing `ffmpeg`.
   - Add regression coverage for `scripts/verify_public_install.py` retry behavior.
   - Exit criteria:
     - Integration tests run in CI.
     - Release helper scripts have direct test coverage.
     - Critical error paths are covered by tests instead of only manual verification.

2. P3.2 Operational Hardening
   - Review retry and timeout boundaries in the MiniMax request path.
   - Make overwrite and output-directory behavior explicit when a target path already exists.
   - Tighten merge and cleanup safety so partial failures never delete successful outputs unexpectedly.
   - Review stderr/stdout behavior and exit codes for automation stability.
   - Exit criteria:
     - Error handling is predictable for partial-success and dependency-failure scenarios.
     - Cleanup behavior is documented and tested.
     - No known ambiguous overwrite paths remain.

3. P3.3 Maintainer Process Docs
   - Add a release checklist document for preflight, tagging, post-release checks, and recovery.
   - Add a compatibility/support policy covering supported Python versions, platforms, and external dependencies.
   - Add a contributor-facing maintenance guide for triaging bugs and validating fixes.
   - Exit criteria:
     - A maintainer can follow written docs to release, recover, and support the project without relying on chat history.

4. P3.4 Public Maintenance Scaffolding
   - Add GitHub issue templates for bug reports and feature requests.
   - Add a user-facing support boundary document or section covering what is and is not supported.
   - Review whether a dedicated `CONTRIBUTING.md` should be added instead of relying only on development docs.
   - Exit criteria:
     - New issues arrive with enough structure to reproduce problems.
     - Public maintenance expectations are explicit.

Recommended file-level work:

- `tests/`
  - add integration-style CLI tests
  - add release-helper tests
- `voice_dashboard/pipeline.py`
  - tighten retry, timeout, cleanup, and overwrite behavior
- `voice_dashboard/config.py`
  - harden config discovery, migration, and validation edge cases
- `docs/`
  - add release checklist
  - add compatibility/support policy
  - refine maintainer-facing guides
- `.github/`
  - add issue templates for bugs and feature requests

Suggested execution order inside P3:

1. Ship P3.1 first so later refactors have safety coverage.
2. Use P3.2 to harden runtime behavior once tests can catch regressions.
3. Close P3.3 and P3.4 after the runtime and release workflows are stable enough to document cleanly.

Recommended release slices:

- `0.5.x`: test hardening
- `0.6.x`: runtime hardening and safer operational behavior
- `0.7.x`: maintainer docs, support policy, and issue templates
- `1.0.0`: freeze interface expectations and declare support boundary

Working checklist:

- `docs/P3_CHECKLIST.md`

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

1. Decide whether to ship one more `0.7.x` stabilization release or promote directly toward `1.0.0`.
2. Review any remaining undocumented edge cases in the manifest/output contract before freezing the `1.0.0` public interface.
3. Keep `docs/COMPATIBILITY.md` aligned with CI if Python-version or platform support expands.
4. Treat any new user-facing behavior changes as `1.0.0` scope decisions rather than packaging work.

## 10. Success Metrics

The roadmap is working if the project reaches these measurable outcomes:

- New users can install the tool in under five minutes from docs alone.
- Maintainers can cut a release from a git tag without editing files by hand.
- The CLI behavior is stable enough that installation docs do not need frequent rewrites.
- Reported issues shift from setup problems to real product feedback.
