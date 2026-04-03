# ttsrun Usage Guide

This document explains how to use `ttsrun` in this repository for daily batch TTS conversion.

## 1. Feature Overview

`ttsrun` supports:

- Three input sources (choose one):
  - Text file path (positional argument)
  - `--stdin` (standard input)
  - `--clipboard` (macOS `pbpaste`)
- Plain-text splitting by empty lines (one MP3 per segment)
- Optional merge via `--merge` (default is **no merge**)
- Output artifacts: `manifest.json` and `errors.jsonl`
- Config file support for persistent defaults

## 2. Prerequisites

- Python 3.10+
- Environment variable: `MINIMAX_API_KEY`
- `ffmpeg` installed if you use `--merge`
- macOS `pbpaste` available if you use `--clipboard`

Set API key (macOS/Linux):

```bash
export MINIMAX_API_KEY="your_new_key"
```

> Security note: if an old hardcoded key was exposed before, revoke it and rotate to a new one.

## 3. Installation and Entrypoints

The project exposes a `console_scripts` command named `ttsrun`.

### 3.1 Editable install (recommended)

Run at repository root:

```bash
python3 -m pip install -e .
```

Then verify:

```bash
ttsrun --help
```

### 3.2 Direct script entrypoint

If you do not want a global command yet:

```bash
python3 voice.py --help
```

`voice.py` is currently a thin wrapper; core logic lives in `voice_dashboard.cli`.

## 4. Common Workflows

### 4.1 File input (most stable)

```bash
ttsrun examples/sample.txt
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

## 5. Output Rules

### 5.1 Default output directory

If `--output-dir` is not provided, the tool creates:

```text
<output_root>/<YYYY-MM-DD>/<YYYYMMDD-HHMMSS>-<label>/
```

Where:
- `output_root` comes from config (default: `~/Documents/tts-output`)
- `label` is derived from the input source (or overridden by `--name`)

### 5.2 Fixed output directory

```bash
ttsrun examples/sample.txt --output-dir outputs/demo
```

### 5.3 Generated files

Each run generates at least:

- `manifest.json`: job summary, parameters, per-segment results
- `errors.jsonl`: only failed segments
- Segment files (`0001.mp3`, etc.) when not merged, or `merged.mp3` when merge succeeds

## 6. Config File

Default config path:

```text
~/.voice-dashboard.json
```

Print a config example:

```bash
ttsrun --print-config-example
```

You can save and customize output as `~/.voice-dashboard.json`, for example:

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
    "output_root": "~/Documents/tts-output",
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
- Workflow switches:
  - `--merge`
  - `--open`

## 8. Failure Handling and Exit Codes

- If any segment fails, process exits with non-zero status, while successful segments are kept.
- In `--merge` mode:
  - Missing `ffmpeg`, merge failure, or cleanup failure leads to non-zero exit.
  - On merge failure, segment files are preserved for troubleshooting.

## 9. Recommended Daily Commands

If your workflow is "copy text → generate audio":

```bash
pbpaste | ttsrun --stdin --merge
```

Open output folder after completion:

```bash
pbpaste | ttsrun --stdin --merge --open
```
