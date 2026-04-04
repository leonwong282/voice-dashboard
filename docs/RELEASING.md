# Release Guide

This guide covers the maintainer workflow for shipping `voice-dashboard` to GitHub Releases, PyPI, and Homebrew.

Maintainer companion docs:

- `docs/RELEASE_CHECKLIST.md`
- `docs/COMPATIBILITY.md`
- `CONTRIBUTING.md`

## 1. Release Preconditions

Before cutting a tag:

- The working tree should be clean.
- `CHANGELOG.md` should include the release-ready notes.
- The version in `voice_dashboard.__version__` should already reflect the release you are cutting.
- Local validation should pass:

```bash
make check release-smoke
```

## 2. PyPI Trusted Publishing Setup

This repository is configured to publish through GitHub Actions Trusted Publishing.

Create or update the PyPI project, then register this trusted publisher:

- Owner: `leonwong282`
- Repository: `voice-dashboard`
- Workflow: `.github/workflows/release.yml`
- Environment: `pypi`

The `pypi` GitHub environment is intentionally part of the trust boundary. Keep any environment protection rules aligned with your release policy.

## 3. Homebrew Tap Automation Setup

This repository now publishes the Homebrew formula automatically into:

- `leonwong282/homebrew-tap`

Create a repository secret in `leonwong282/voice-dashboard`:

- Name: `HOMEBREW_TAP_TOKEN`
- Type: fine-grained GitHub personal access token
- Repository access: `leonwong282/homebrew-tap`
- Minimal permissions:
  - `Contents`: `Read and write`
  - `Metadata`: `Read-only` (required by GitHub and added automatically)

Without that secret, tagged releases will still build and publish to PyPI, but the Homebrew publish step will fail.

For the exact release-day sequence, use `docs/RELEASE_CHECKLIST.md` as the operational source of truth.

## 4. Release Workflow

Cut and push a version tag:

```bash
git tag v0.7.1
git push origin v0.7.1
```

The release workflow then:

1. Installs the project and development toolchain.
2. Runs `make check release-smoke`.
3. Builds `sdist` and `wheel` artifacts.
4. Uploads `dist/*` as workflow artifacts.
5. Generates `SHA256SUMS.txt` for the release artifacts.
6. Publishes the same distributions to PyPI through Trusted Publishing.
7. Verifies `voice-dashboard==<tag-version>` through real `pip` and `pipx` installs from PyPI.
8. Renders a Homebrew formula asset for the same tag using the published PyPI sdist metadata.
9. Pushes the rendered formula into `leonwong282/homebrew-tap`.
10. Verifies `brew install leonwong282/tap/voice-dashboard` on `macos-latest`.
11. Creates or updates the matching GitHub Release and attaches the built distributions, checksums, and rendered formula.

You can also run the workflow manually with `workflow_dispatch` to rehearse the build and artifact path without creating a published release.

If PyPI publication succeeds but the Homebrew portion fails afterward, use the dedicated recovery workflow instead of cutting a new package version immediately:

```bash
.github/workflows/publish-homebrew.yml
```

That workflow renders the formula from the already-published PyPI version, pushes it into `leonwong282/homebrew-tap`, and runs the same macOS Homebrew install smoke check.

## 5. Post-Release Verification

After PyPI publication completes, verify the public install path in a clean shell:

```bash
pipx install voice-dashboard
ttsrun --help
ttsrun --version
MINIMAX_API_KEY=smoke-test-key ttsrun doctor
pipx uninstall voice-dashboard
```

If you want to verify the plain `pip` path as well:

```bash
python3 -m venv /tmp/voice-dashboard-release-check
/tmp/voice-dashboard-release-check/bin/python -m pip install --upgrade pip
/tmp/voice-dashboard-release-check/bin/python -m pip install voice-dashboard
/tmp/voice-dashboard-release-check/bin/ttsrun --help
rm -rf /tmp/voice-dashboard-release-check
```

For a repeatable scripted check, use:

```bash
python scripts/verify_public_install.py --package-spec voice-dashboard==0.7.1
```

The same verification now runs automatically in the tag-driven release workflow after PyPI publication succeeds.

Verify the published Homebrew route as well:

```bash
brew tap leonwong282/tap
brew install leonwong282/tap/voice-dashboard
ttsrun --version
brew test leonwong282/tap/voice-dashboard
```

## 6. Homebrew Notes

The repository still includes the template and rendering path used by the automation:

- `packaging/homebrew/voice-dashboard.rb.template`
- `scripts/render_homebrew_formula.py`
- `docs/HOMEBREW.md`

To prepare the source tarball checksum for a formula update:

```bash
make dist-sha256
```

To render a concrete formula body from the published source tarball:

```bash
python scripts/render_homebrew_formula.py --package-version 0.7.1
```

The release workflow now also pushes that rendered formula directly into the shared tap, so the GitHub Release attachment is mainly useful for inspection and troubleshooting.

If the tag workflow fails after PyPI publication and the GitHub Release does not exist yet, create the GitHub Release manually from the existing tag and attach:

- the `sdist`
- the wheel
- `SHA256SUMS.txt`
- the rendered `voice-dashboard.rb`

See also:

- `docs/RELEASE_CHECKLIST.md` for the step-by-step release and recovery checklist
- `docs/COMPATIBILITY.md` for the supported Python, platform, and install boundary
- `CONTRIBUTING.md` for contributor and triage expectations
