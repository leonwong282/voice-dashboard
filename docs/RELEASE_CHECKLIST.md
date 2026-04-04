# Release Checklist

Use this checklist when shipping a new `voice-dashboard` version. The goal is to make releases repeatable without relying on chat history.

## 1. Preflight

- Confirm the working tree is clean.
- Confirm `voice_dashboard.__version__` already matches the intended release version.
- Confirm `CHANGELOG.md` contains release-ready notes.
- Confirm required external release credentials still exist:
  - PyPI Trusted Publisher for `.github/workflows/release.yml`
  - GitHub repository secret `HOMEBREW_TAP_TOKEN`
- Run the local quality gates:

```bash
make check release-smoke
```

## 2. Cut The Release

- Switch to the release branch, normally `main`.
- Pull the latest remote state.
- Create and push the tag:

```bash
git checkout main
git pull --ff-only
git tag vX.Y.Z
git push origin vX.Y.Z
```

## 3. Watch The Release Workflow

In GitHub Actions, confirm the following jobs succeed for the tagged run:

- `build`
- `pypi-publish`
- `public-install-smoke`
- `homebrew-formula`
- `homebrew-publish`
- `homebrew-install-smoke`
- `github-release`

The release is not complete until the Homebrew publish and install-smoke steps also pass.

## 4. Post-Release Validation

- Verify the GitHub Release exists for the tag and contains:
  - the wheel
  - the source distribution
  - `SHA256SUMS.txt`
  - `voice-dashboard.rb`
- Verify the new package version appears on PyPI.
- Verify the new formula version appears in `leonwong282/homebrew-tap`.
- Perform public install checks:

```bash
python scripts/verify_public_install.py --package-spec voice-dashboard==X.Y.Z
brew tap leonwong282/tap
brew install leonwong282/tap/voice-dashboard
ttsrun --version
brew test leonwong282/tap/voice-dashboard
```

## 5. Recovery Paths

### 5.1 Failed PyPI Publish

- Inspect the `pypi-publish` job logs first.
- Fix the root cause before cutting another version tag.
- Common causes:
  - version/tag mismatch
  - PyPI publisher misconfiguration
  - invalid distribution metadata
- If the version was not accepted by PyPI, you can usually reuse the same version after fixing the workflow or metadata and re-running from a new tag push.
- If PyPI already accepted the version, do not overwrite it; move forward with a new version instead.

### 5.2 Failed Homebrew Publish

- If PyPI already succeeded, do not immediately cut a new package release.
- Use the dedicated recovery workflow:
  - `.github/workflows/publish-homebrew.yml`
- Pass the already-published package version, then confirm:
  - the formula was pushed into `leonwong282/homebrew-tap`
  - the macOS Homebrew smoke check passed
- Common causes:
  - missing or under-scoped `HOMEBREW_TAP_TOKEN`
  - tap repo drift
  - Homebrew install regression on macOS

### 5.3 Failed GitHub Release Creation

- Confirm the tag exists remotely.
- Download the workflow artifacts from the failed run:
  - `dist/*`
  - `SHA256SUMS.txt`
  - `voice-dashboard.rb`
- Create the GitHub Release manually from the existing tag and attach those files.
- If the release workflow can be safely re-run after permissions or transient failures are fixed, prefer that path first.

## 6. Release Notes Hygiene

- Keep the GitHub generated notes, but ensure `CHANGELOG.md` remains the maintainer source of truth.
- If the release introduced support-boundary changes, update:
  - `docs/COMPATIBILITY.md`
  - `README.md`
  - `README.zh-TW.md`

## 7. Final Close-Out

- Confirm the repository default branch remains clean after the release.
- Confirm there are no orphaned release artifacts in the working tree.
- If a manual recovery step was required, document it in `docs/RELEASING.md` before the next release.
