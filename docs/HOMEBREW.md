# Homebrew Packaging Guide

This document covers the published Homebrew distribution path for `voice-dashboard`.

## 1. Current Status

`voice-dashboard` is now published through the shared tap:

```text
leonwong282/homebrew-tap
```

End users install it with:

```bash
brew install leonwong282/tap/voice-dashboard
```

The main release workflow renders a formula from the published PyPI sdist metadata, pushes that formula into the tap repository, and then verifies a real Homebrew install on `macos-latest`.

## 2. Tap Layout

The shared tap repository lives at:

```text
https://github.com/leonwong282/homebrew-tap
```

The formula file path is:

```text
Formula/voice-dashboard.rb
```

This shared tap layout is the intended structure for future CLI tools as well.

## 3. Release Automation

The tag-driven `release.yml` workflow now handles Homebrew publication automatically after PyPI publication succeeds.

Required repository secret:

- `HOMEBREW_TAP_TOKEN`
  - type: fine-grained GitHub personal access token
  - repository access: `leonwong282/homebrew-tap`
  - minimal permissions:
    - `Contents`: `Read and write`
    - `Metadata`: `Read-only`

Release flow:

1. Build and validate `sdist` and `wheel`.
2. Publish to PyPI through Trusted Publishing.
3. Verify public `pip` and `pipx` installation paths.
4. Render `Formula/voice-dashboard.rb` from published PyPI metadata.
5. Push the updated formula into `leonwong282/homebrew-tap`.
6. Verify `brew install leonwong282/tap/voice-dashboard` on `macos-latest`.
7. Attach the rendered formula and checksums to the matching GitHub Release.

If the main tag workflow already published to PyPI but failed before updating the tap, run the recovery workflow manually:

```text
.github/workflows/publish-homebrew.yml
```

Pass the already-published package version, for example `0.7.1`.

## 4. Local Formula Testing

Recent Homebrew versions reject direct `brew install /path/to/formula.rb` for tap-managed formulae. Test through a local tap checkout instead.

Example local workflow:

```bash
git clone https://github.com/leonwong282/homebrew-tap /tmp/homebrew-tap
python scripts/render_homebrew_formula.py --package-version 0.7.1 --output /tmp/homebrew-tap/Formula/voice-dashboard.rb

export HOMEBREW_NO_AUTO_UPDATE=1
export HOMEBREW_NO_INSTALL_FROM_API=1

brew untap leonwong282/tap || true
brew tap leonwong282/tap /tmp/homebrew-tap
brew audit --strict leonwong282/tap/voice-dashboard
brew install leonwong282/tap/voice-dashboard
brew test leonwong282/tap/voice-dashboard
```

If you want to clean up afterwards:

```bash
brew uninstall voice-dashboard || true
brew untap leonwong282/tap
```

## 5. Formula Inputs

The repository includes:

- `packaging/homebrew/voice-dashboard.rb.template`
- `scripts/render_homebrew_formula.py`

Render a concrete formula from a published package version:

```bash
python scripts/render_homebrew_formula.py --package-version 0.7.1
```

If you need to override the source tarball URL manually:

```bash
python scripts/render_homebrew_formula.py \
  --source-url <source-tarball-url> \
  --source-sha256 <sha256>
```
