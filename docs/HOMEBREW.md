# Homebrew Packaging Guide

This document covers the planned Homebrew distribution path for `voice-dashboard`.

## 1. Current Status

Homebrew support is not published yet. The repository now includes:

- a release workflow that creates tagged source and wheel artifacts
- a Homebrew formula template under `packaging/homebrew/`
- maintainer guidance for turning a tagged release into a tap formula

The actual tap repository should be created only after the PyPI release path is stable.

## 2. Recommended Tap Layout

Use a dedicated tap repository such as:

```text
leonwong282/homebrew-voice-dashboard
```

The formula file should live at:

```text
Formula/voice-dashboard.rb
```

End users would then install with:

```bash
brew install leonwong282/voice-dashboard/voice-dashboard
```

## 3. Formula Workflow

Homebrew’s official guidance for Python applications is to package them as applications, declare a brewed Python dependency, and vendor Python module dependencies as `resource` stanzas.

Suggested workflow for each release:

1. Cut and publish the GitHub release tag first.
2. Use the release source tarball URL in the formula.
3. Start from `packaging/homebrew/voice-dashboard.rb.template`.
4. Fill in the version, tarball URL, and SHA256.
5. Generate or refresh Python `resource` stanzas with Homebrew tooling.
6. Test the formula locally before pushing the tap update.

Useful commands:

```bash
make dist-sha256
brew create --python --set-name voice-dashboard <source-tarball-url>
brew update-python-resources --print-only Formula/voice-dashboard.rb
HOMEBREW_NO_INSTALL_FROM_API=1 brew install --build-from-source Formula/voice-dashboard.rb
brew audit --strict --formula Formula/voice-dashboard.rb
brew test voice-dashboard
```

## 4. Local Testing Notes

When iterating on a local formula checkout, force Homebrew to use the local tap checkout instead of the API:

```bash
export HOMEBREW_NO_INSTALL_FROM_API=1
```

This matters when testing unpublished formula changes from a tap repository.

## 5. Template Files

The repository includes:

- `packaging/homebrew/voice-dashboard.rb.template`
- `scripts/render_homebrew_formula.py`

That template is intentionally not a live formula yet. It exists to keep release-time edits small and repeatable.

You can render a concrete formula directly from the published PyPI release metadata with:

```bash
python scripts/render_homebrew_formula.py --package-version 0.4.0
```

If you need to override the source tarball URL manually, the script also accepts:

```bash
python scripts/render_homebrew_formula.py \
  --source-url <source-tarball-url> \
  --source-sha256 <sha256>
```
