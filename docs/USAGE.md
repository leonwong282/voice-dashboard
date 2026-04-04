# ttsrun Usage Guide

This document explains how to use `ttsrun` in this repository for daily batch TTS conversion.

## 1. Feature Overview

`ttsrun` supports:

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
- Environment variable: `MINIMAX_API_KEY`
- `ffmpeg` installed if you use `--merge`
- A supported clipboard command installed if you use `--clipboard`

Set API key (macOS/Linux):

```bash
export MINIMAX_API_KEY="your_new_key"
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
ttsrun examples/sample.txt
```

Explicit command form:

```bash
ttsrun run examples/sample.txt
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

- `--request-timeout` controls the HTTP timeout for each MiniMax request attempt.
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

You can save and customize output in the resolved config path, for example:

```json
{
  "defaults": {
    "voice_id": "clone_voice_can",
    "speed": 1.2,
    "pitch": 0,
    "language_boost": "Chinese,Yue",
    "model": "speech-2.8-hd",
    "sample_rate": 32000,
    "format": "mp3",
    "request_timeout_seconds": 60,
    "max_retries": 3,
    "output_root": "~/Documents/voice-dashboard",
    "open_after_finish": false
  }
}
```

Use a custom config path:

```bash
ttsrun examples/sample.txt --config /path/to/config.json
```

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
  - `--voice-id`
  - `--speed`
  - `--pitch` (integer)
  - `--language-boost`
  - `--model`
  - `--sample-rate`
  - `--format mp3`
  - `--request-timeout <seconds>`
  - `--max-retries <count>`
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
