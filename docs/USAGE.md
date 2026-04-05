# ttsrun Usage Guide

This document explains how to use `ttsrun` in this repository for daily batch TTS conversion.

`ttsrun` is a TTS-only CLI. You provide an existing `voice_id` from your provider; the tool does not create, list, or manage voices.

## 1. Feature Overview

`ttsrun` supports:

- Multiple TTS providers selected by `--provider` or config default
- Three input sources (choose one):
  - Text file path (positional argument)
  - `--stdin` (standard input)
  - `--clipboard` (supported clipboard commands such as `pbpaste`, `wl-paste`, `xclip`, or `xsel`)
- Plain-text splitting by empty lines (one MP3 per segment)
- Optional merge via `--merge` (default is **no merge**)
- Output control for scripting:
  - `--quiet`
  - `--verbose`
  - `--json-summary`
- Runtime request controls:
  - `--request-timeout`
  - `--max-retries`
- Output artifacts: `manifest.json` and `errors.jsonl`
- Config file support for persistent defaults

## 2. Prerequisites

- Python 3.10+
- One provider API key, depending on the active provider:
  - `MINIMAX_API_KEY`
  - `ELEVENLABS_API_KEY`
- `ffmpeg` installed if you use `--merge`
- A supported clipboard command installed if you use `--clipboard`

Set API key (macOS/Linux):

```bash
# MiniMax
export MINIMAX_API_KEY="your_new_key"

# ElevenLabs
export ELEVENLABS_API_KEY="your_elevenlabs_key"
```

> Security note: if an old hardcoded key was exposed before, revoke it and rotate to a new one.

## 3. Installation and Entrypoints

The project exposes a `console_scripts` command named `ttsrun`.

### 3.1 Published install from PyPI

Once a public PyPI release exists, prefer `pipx` for end-user CLI installation:

```bash
pipx install voice-dashboard
```

If you want the package inside an existing Python environment instead:

```bash
python3 -m pip install voice-dashboard
```

Homebrew install is also available:

```bash
brew install leonwong282/tap/voice-dashboard
```

See `docs/HOMEBREW.md` for the tap and release automation details.

### 3.2 Local install from source

Run at repository root:

```bash
python3 -m pip install .
```

Then verify:

```bash
ttsrun --help
ttsrun doctor
```

### 3.3 Editable install for contributors

If you are working on the project itself:

```bash
python3 -m pip install -e ".[dev]"
```

See `docs/DEVELOPMENT.md` for the full contributor workflow.

### 3.4 Direct script entrypoint

If you do not want an installed command yet:

```bash
python3 voice.py --help
```

`voice.py` is currently a thin wrapper; core logic lives in `voice_dashboard.cli`.

## 4. Common Workflows

### 4.1 File input (most stable)

```bash
ttsrun --provider minimax --voice-id clone_voice_can examples/sample.txt
```

Explicit command form:

```bash
ttsrun run --provider minimax --voice-id clone_voice_can examples/sample.txt
```

ElevenLabs example:

```bash
ttsrun --provider elevenlabs --voice-id JBFqnCBsd6RMkjVDRZzb examples/sample.txt
```

### 4.2 Clipboard input (macOS)

```bash
ttsrun --clipboard
```

### 4.3 Stdin pipeline input

```bash
pbpaste | ttsrun --stdin
```

### 4.4 Merge only when you need a combined audio file

```bash
ttsrun examples/sample.txt --merge
```

- Without `--merge`: keeps `0001.mp3`, `0002.mp3`, ...
- With `--merge`: generates `merged.mp3` after all segments succeed, then removes segment files from this run

### 4.5 Machine-readable summary

```bash
ttsrun examples/sample.txt --json-summary
```

This prints the final manifest summary JSON to stdout. Progress output stays on stderr so the JSON can be piped safely.

### 4.6 Tune request timeout and retry boundaries

```bash
ttsrun examples/sample.txt --request-timeout 90 --max-retries 5
```

- `--request-timeout` controls the HTTP timeout for each provider request attempt.
- `--max-retries` controls the total number of attempts per segment, including the first request.
- The same defaults can be persisted in config with `request_timeout_seconds` and `max_retries`.

## 5. Output Rules

### 5.1 Default output directory

If `--output-dir` is not provided, the tool creates:

```text
<output_root>/<YYYY-MM-DD>/<YYYYMMDD-HHMMSS>-<label>/
```

Where:
- `output_root` comes from config (default: `~/Documents/voice-dashboard` when `~/Documents` exists, otherwise an XDG-style data directory)
- `label` is derived from the input source (or overridden by `--name`)

### 5.2 Fixed output directory

```bash
ttsrun examples/sample.txt --output-dir outputs/demo
```

- If `outputs/demo` already exists and is not empty, `ttsrun` stops with an input error by default.
- Use `--force-output-dir` only when you intentionally want to reuse that directory and allow generated files such as `0001.mp3`, `manifest.json`, or `merged.mp3` to be overwritten.

### 5.3 Automatic output-directory collision handling

If an auto-generated timestamped directory already exists, `ttsrun` creates a suffixed directory such as `20260404-173000-job-2` instead of mixing outputs from two runs.

### 5.4 Generated files

Each run generates at least:

- `manifest.json`: job summary, parameters, per-segment results
- `errors.jsonl`: only failed segments
- Segment files (`0001.mp3`, etc.) when not merged, or `merged.mp3` when merge succeeds

## 6. Config File

Default config path:

```text
~/.config/voice-dashboard/config.json
```

If you already have the legacy file `~/.voice-dashboard.json`, `ttsrun` keeps using it until you move or replace it.

Important: the config schema is provider-local. `voice_id`, `model`, and `speed` live under each provider, not in a shared `defaults` block.

Print a config example:

```bash
ttsrun config example
```

Print the resolved config path:

```bash
ttsrun config path
```

Create an example config file:

```bash
ttsrun config init
```

Show the effective configuration, including resolved metadata:

```bash
ttsrun config show
```

### 6.1 How the config is structured

The config answers three separate questions:

- which provider should be used by default
- which settings are truly global across providers
- which settings belong to each provider

Current schema:

```json
{
  "default_provider": "minimax",
  "global": {
    "output_root": "~/Documents/voice-dashboard",
    "format": "mp3",
    "request_timeout_seconds": 60,
    "max_retries": 3,
    "open_after_finish": false
  },
  "providers": {
    "minimax": {
      "voice_id": "clone_voice_can",
      "speed": 1.2,
      "model": "speech-2.8-hd",
      "pitch": 0,
      "language_boost": "Chinese,Yue",
      "sample_rate": 32000
    },
    "elevenlabs": {
      "voice_id": "JBFqnCBsd6RMkjVDRZzb",
      "speed": 1.0,
      "model": "eleven_multilingual_v2",
      "output_format": "mp3_44100_128",
      "timestamps": true,
      "language_code": "zh",
      "seed": 12345,
      "enable_logging": true,
      "continuity_mode": "adjacent_text",
      "voice_settings": {
        "speed": 0.95,
        "stability": 0.5,
        "similarity_boost": 0.8,
        "style": 0.1,
        "use_speaker_boost": true
      }
    }
  }
}
```

Meaning of each section:

- `default_provider`: used when CLI does not pass `--provider`
- `global`: only for settings that make sense regardless of provider
- `providers.minimax`: MiniMax defaults, including shared-looking fields such as `voice_id`, `model`, and `speed`
- `providers.elevenlabs`: ElevenLabs defaults, with its own `voice_id`, `model`, `speed`, and optional provider-native fields such as `output_format`, `timestamps`, `language_code`, `seed`, `enable_logging`, `continuity_mode`, and nested `voice_settings`

Runtime precedence:

1. CLI flags such as `--provider`, `--voice-id`, `--model`
2. active provider section in config
3. `global` config values
4. built-in defaults

### 6.2 What should go in `global`

Keep only genuinely cross-provider settings in `global`:

- `output_root`
- `format`
- `request_timeout_seconds`
- `max_retries`
- `open_after_finish`

Do not put these in a shared section:

- `voice_id`
- `model`
- `speed`

Those are stored under each provider because they are provider-specific in practice.

### 6.3 MiniMax and ElevenLabs in one config

One config can now hold both providers cleanly:

- MiniMax can keep its own `voice_id`, `model`, `speed`, `pitch`, `language_boost`, `sample_rate`
- ElevenLabs can keep its own `voice_id`, `model`, `speed`, and provider-native request fields

Example:

```json
{
  "default_provider": "minimax",
  "global": {
    "output_root": "~/Documents/voice-dashboard",
    "format": "mp3",
    "request_timeout_seconds": 60,
    "max_retries": 3,
    "open_after_finish": false
  },
  "providers": {
    "minimax": {
      "voice_id": "clone_voice_can",
      "speed": 1.2,
      "model": "speech-2.8-hd",
      "pitch": 0,
      "language_boost": "Chinese,Yue",
      "sample_rate": 32000
    },
    "elevenlabs": {
      "voice_id": "JBFqnCBsd6RMkjVDRZzb",
      "speed": 1.0,
      "model": "eleven_multilingual_v2",
      "output_format": "mp3_44100_128",
      "timestamps": true,
      "language_code": "zh",
      "seed": 12345,
      "enable_logging": true,
      "continuity_mode": "adjacent_text",
      "voice_settings": {
        "speed": 0.95,
        "stability": 0.5,
        "similarity_boost": 0.8,
        "style": 0.1,
        "use_speaker_boost": true
      }
    }
  }
}
```

With that config:

- `ttsrun input.txt` uses MiniMax by default
- `ttsrun --provider elevenlabs input.txt` switches to the ElevenLabs section
- `ttsrun --provider elevenlabs --voice-id custom123 input.txt` overrides only the current run

### 6.4 API keys are not stored in config

Do not put secrets in the JSON file.

Use environment variables instead:

```bash
export MINIMAX_API_KEY="your_minimax_key"
export ELEVENLABS_API_KEY="your_elevenlabs_key"
```

`ttsrun` only checks the key for the active provider.

### 6.5 ElevenLabs config surface note

`providers.elevenlabs` supports provider-native request fields such as `output_format`, `timestamps`, `language_code`, `seed`, `enable_logging`, `continuity_mode`, and nested `voice_settings`.

Speed note:

- `providers.elevenlabs.speed` is the tool-level shared speed value for the active provider
- `providers.elevenlabs.voice_settings.speed` is the ElevenLabs-native override
- if both are present, `voice_settings.speed` wins for the actual ElevenLabs request
- if you do not need an ElevenLabs-specific override, set only the outer `speed`

Current runtime note:

- `output_format` is sent as an ElevenLabs query parameter
- `timestamps: true` switches ElevenLabs to `/with-timestamps` and writes one `.timestamps.json` sidecar per successful segment
- `enable_logging` is sent as an ElevenLabs query parameter when configured
- `language_code` and `seed` are sent in the ElevenLabs request body when configured
- `continuity_mode: "adjacent_text"` makes batch runs send neighboring segment text as `previous_text` and `next_text`
- nested `voice_settings` fields are sent only when configured
- `voice_settings.speed` overrides the provider-level ElevenLabs `speed` for the request when both are present
- continuity is opt-in and config-only in the current release

### 6.6 Using a custom config path

Use a custom config path:

```bash
ttsrun examples/sample.txt --config /path/to/config.json
```

### 6.7 Provider Notes

- `ttsrun` is TTS-only. It expects an existing `voice_id`.
- `--provider minimax` supports MiniMax-specific controls such as `--pitch`, `--language-boost`, and `--sample-rate`.
- `--provider elevenlabs` supports the shared controls plus provider-local config fields under `providers.elevenlabs`.
- ElevenLabs-native fields remain config-only in the current CLI. There are no `--el-*` flags in this release.
- ElevenLabs timestamp metadata is available through `providers.elevenlabs.timestamps: true`.
- MiniMax-only flags are rejected when `--provider elevenlabs` is active.

## 7. Option Quick Reference

- Input source (choose one):
  - `ttsrun <input_path>`
  - `ttsrun --stdin`
  - `ttsrun --clipboard`
- Output control:
  - `--output-dir <dir>`
  - `--force-output-dir`
  - `--output-root <dir>`
  - `--name <job-name>`
- Voice parameters:
  - `--provider {minimax,elevenlabs}`
  - `--voice-id`
  - `--speed`
  - `--model`
  - `--format mp3`
  - `--request-timeout <seconds>`
  - `--max-retries <count>`
- MiniMax-only parameters:
  - `--pitch` (integer)
  - `--language-boost`
  - `--sample-rate`
- ElevenLabs-native parameters:
  - configure these under `providers.elevenlabs`
  - current release does not expose `--el-*` CLI flags
- Workflow switches:
  - `--merge`
  - `--open`
  - `--quiet`
  - `--verbose`
  - `--json-summary`
- Management commands:
  - `--version`
  - `doctor`
  - `config path`
  - `config show`
  - `config example`
  - `config init`
- Deprecated compatibility flags:
  - `--doctor`
  - `--print-config-path`
  - `--print-config-example`
  - `--init-config`
  - `--force` (with `--init-config`)

## 8. Failure Handling and Exit Codes

- Stable exit codes:
  - `0`: success
  - `2`: command-line usage error from `argparse`
  - `3`: config error
  - `4`: input source error
  - `5`: authentication error
  - `6`: API or network error
  - `7`: dependency error
- If any segment fails, process exits with a category-specific non-zero status, while successful segments are kept.
- In `--merge` mode:
  - Missing `ffmpeg`, merge failure, or cleanup failure leads to non-zero exit.
  - On merge failure, segment files are preserved for troubleshooting.
  - On cleanup failure after a successful merge, generated segments are either restored in place or preserved in a hidden cleanup backup directory reported in the manifest summary.

## 9. Environment Checks

Run a quick environment report:

```bash
ttsrun doctor
```

You can check another provider explicitly:

```bash
ttsrun doctor --provider elevenlabs
```

`doctor` treats the active provider key as required and reports the inactive provider key as informational only.

## 10. Output Streams

- stdout is used for explicit command output such as:
  - `--version`
  - `ttsrun config path`
  - `ttsrun config example`
  - `ttsrun config show`
  - `--json-summary`
- stderr is used for progress lines, warnings, and errors during batch execution.
- `--quiet` suppresses progress output while still allowing warnings and errors.
- `--verbose` adds extra detail such as resolved voice settings, request timeout/retry settings, and retry notices.

## 11. Recommended Daily Commands

If your workflow is "copy text → generate audio":

```bash
pbpaste | ttsrun --stdin --merge
```

Open output folder after completion:

```bash
pbpaste | ttsrun --stdin --merge --open
```

For release-style manual verification, use [docs/MANUAL_USABILITY_CHECKLIST.md](./MANUAL_USABILITY_CHECKLIST.md).
