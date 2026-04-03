# Release Guide

This guide covers the maintainer workflow for shipping `voice-dashboard` to GitHub Releases and PyPI.

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

## 3. Release Workflow

Cut and push a version tag:

```bash
git tag v0.4.0
git push origin v0.4.0
```

The release workflow then:

1. Installs the project and development toolchain.
2. Runs `make check release-smoke`.
3. Builds `sdist` and `wheel` artifacts.
4. Uploads `dist/*` as workflow artifacts.
5. Publishes the same distributions to PyPI through Trusted Publishing.
6. Verifies `voice-dashboard==<tag-version>` through real `pip` and `pipx` installs from PyPI.
7. Renders a Homebrew formula asset for the same tag.
8. Creates or updates the matching GitHub Release and attaches both the built distributions and the rendered formula.

You can also run the workflow manually with `workflow_dispatch` to rehearse the build and artifact path without creating a published release.

## 4. Post-Release Verification

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
python scripts/verify_public_install.py --package-spec voice-dashboard==0.4.0
```

The same verification now runs automatically in the tag-driven release workflow after PyPI publication succeeds.

## 5. Homebrew Follow-Up

Homebrew support should be added only after the PyPI release path is stable. Once the first public PyPI release is verified, use the GitHub Release artifacts from the matching tag as the input for a tap formula.

The repository includes a starting point at `packaging/homebrew/voice-dashboard.rb.template` plus a dedicated guide in `docs/HOMEBREW.md`.

To prepare the source tarball checksum for a formula update:

```bash
make dist-sha256
```

To render a concrete formula body from the published source tarball:

```bash
python scripts/render_homebrew_formula.py \
  --source-url https://github.com/leonwong282/voice-dashboard/archive/refs/tags/v0.4.0.tar.gz \
  --source-sha256 <sha256>
```

The release workflow now attaches the rendered `voice-dashboard.rb` file to the matching GitHub Release so the tap update can start from a concrete artifact instead of a manual copy step.
