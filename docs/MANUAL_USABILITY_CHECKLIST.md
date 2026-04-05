# Manual Usability Checklist

Use this checklist before release or after config/provider changes. It is written for the current config schema:

- `default_provider`
- `global`
- `providers`

This checklist assumes:

- you already have valid provider `voice_id` values
- API keys are provided through environment variables
- `ttsrun` is installed or runnable from the repo

## 1. Test Setup

Create a small input file:

```bash
cat > /tmp/tts-sample.txt <<'EOF'
第一段

第二段
EOF
```

Prepare a config file:

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
      "voice_id": "your_minimax_voice_id",
      "speed": 1.2,
      "model": "speech-2.8-hd",
      "pitch": 0,
      "language_boost": "Chinese,Yue",
      "sample_rate": 32000
    },
    "elevenlabs": {
      "voice_id": "your_elevenlabs_voice_id",
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

Save it to:

```bash
mkdir -p ~/.config/voice-dashboard
$EDITOR ~/.config/voice-dashboard/config.json
```

Set API keys:

```bash
export MINIMAX_API_KEY="your_minimax_key"
export ELEVENLABS_API_KEY="your_elevenlabs_key"
```

## 2. Config Sanity

- Run `ttsrun config show`
- Confirm output contains:
  - `default_provider`
  - `global`
  - `providers.minimax`
  - `providers.elevenlabs`
- Confirm both providers have their own `voice_id`, `model`, and `speed`
- Confirm `providers.elevenlabs` also carries its provider-local fields if you configured them
- If both `providers.elevenlabs.speed` and `providers.elevenlabs.voice_settings.speed` are set:
  - treat the outer `speed` as the shared/default value
  - treat `voice_settings.speed` as the ElevenLabs-specific override
- Confirm `global.output_root` and `global.request_timeout_seconds` look correct

## 3. Doctor Checks

- Run `ttsrun doctor`
- Expect:
  - active provider is `minimax`
  - `MINIMAX_API_KEY` is required and shown as `ok`
  - `ELEVENLABS_API_KEY` is shown as informational

- Run `ttsrun doctor --provider elevenlabs`
- Expect:
  - active provider changes to `elevenlabs`
  - `ELEVENLABS_API_KEY` is required and shown as `ok`
  - `MINIMAX_API_KEY` is informational

## 4. MiniMax Default Config Path

- Run:

```bash
ttsrun /tmp/tts-sample.txt
```

- Expect:
  - command succeeds
  - output directory is created under `global.output_root`
  - `0001.mp3` and `0002.mp3` exist
  - `manifest.json` exists
  - `manifest.json.settings.provider` is `minimax`
  - `manifest.json.settings.common_settings.voice_id` matches `providers.minimax.voice_id`
  - `manifest.json.settings.common_settings.model` matches `providers.minimax.model`
  - `manifest.json.settings.provider_settings.pitch` matches `providers.minimax.pitch`

## 5. ElevenLabs Provider Switch

- Run:

```bash
ttsrun --provider elevenlabs /tmp/tts-sample.txt
```

- Expect:
  - command succeeds
  - `manifest.json.settings.provider` is `elevenlabs`
  - `manifest.json.settings.common_settings.voice_id` matches `providers.elevenlabs.voice_id`
  - `manifest.json.settings.common_settings.model` matches `providers.elevenlabs.model`
  - `manifest.json.settings.provider_settings.output_format` matches `providers.elevenlabs.output_format`
  - `manifest.json.settings.provider_settings` does not include MiniMax-only fields

## 6. CLI Override Checks

- Run:

```bash
ttsrun --provider elevenlabs --voice-id override_voice --model eleven_multilingual_v2 /tmp/tts-sample.txt
```

- Expect:
  - command succeeds
  - `manifest.json.settings.provider` is `elevenlabs`
  - `manifest.json.settings.common_settings.voice_id` is `override_voice`
  - config is not mutated

## 7. MiniMax-Specific Flags

- Run:

```bash
ttsrun --provider minimax --pitch 1 --language-boost Chinese,Yue --sample-rate 32000 /tmp/tts-sample.txt
```

- Expect:
  - command succeeds
  - `manifest.json.settings.provider_settings.pitch` is `1`
  - `manifest.json.settings.provider_settings.language_boost` is `Chinese,Yue`
  - `manifest.json.settings.provider_settings.sample_rate` is `32000`

## 8. ElevenLabs Flag Rejection

- Run each command:

```bash
ttsrun --provider elevenlabs --pitch 1 /tmp/tts-sample.txt
ttsrun --provider elevenlabs --language-boost Chinese,Yue /tmp/tts-sample.txt
ttsrun --provider elevenlabs --sample-rate 32000 /tmp/tts-sample.txt
```

- Expect:
  - each command exits with usage error
  - each error clearly says the flag can only be used with `--provider=minimax`

## 9. Output Directory Behavior

- Run:

```bash
mkdir -p /tmp/tts-fixed-out
echo keep > /tmp/tts-fixed-out/stale.txt
ttsrun /tmp/tts-sample.txt --output-dir /tmp/tts-fixed-out
```

- Expect:
  - command fails because directory is non-empty

- Then run:

```bash
ttsrun /tmp/tts-sample.txt --output-dir /tmp/tts-fixed-out --force-output-dir
```

- Expect:
  - command succeeds
  - generated files are written into `/tmp/tts-fixed-out`

## 10. JSON Summary

- Run:

```bash
ttsrun /tmp/tts-sample.txt --json-summary > /tmp/tts-summary.json
```

- Expect:
  - stdout is valid JSON summary
  - progress output stays on stderr
  - `/tmp/tts-summary.json` contains `provider`, segment counts, and output info

## 11. Merge Flow

- Run:

```bash
ttsrun /tmp/tts-sample.txt --merge
```

- Expect:
  - `merged.mp3` exists
  - segment files are removed after successful merge
  - manifest summary reports merge success

If `ffmpeg` is not installed:

- expect a non-zero exit
- expect segment files to remain for debugging

## 12. ElevenLabs Continuity Check

- Prepare a three-segment input:

```bash
cat > /tmp/tts-continuity.txt <<'EOF'
第一段

第二段

第三段
EOF
```

- Set `providers.elevenlabs.continuity_mode` to `"adjacent_text"`, then run:

```bash
ttsrun --provider elevenlabs /tmp/tts-continuity.txt --verbose
```

- Expect:
  - command succeeds
  - `manifest.json.settings.provider_settings.continuity_mode` is `adjacent_text`
  - continuity remains provider-local and does not affect MiniMax runs
  - adjacent-segment phrasing sounds more connected than the same run with `continuity_mode` removed

## 13. ElevenLabs Timestamp Sidecars

- Set `providers.elevenlabs.timestamps` to `true`, then run:

```bash
ttsrun --provider elevenlabs /tmp/tts-sample.txt
```

- Expect:
  - command succeeds
  - each successful segment has a matching sidecar such as `0001.timestamps.json`
  - `manifest.json.settings.provider_settings.timestamps` is `true`
  - each successful segment entry includes:
    - `timestamp_file`
    - `timestamp_status`

## 14. Legacy Config Rejection

Create an old-style config file:

```json
{
  "provider": "minimax",
  "defaults": {
    "voice_id": "legacy_voice"
  }
}
```

Run:

```bash
ttsrun config show --config /path/to/legacy-config.json
```

Expect:

- command fails with config error
- error mentions:
  - legacy config schema is not supported
  - use `default_provider`, `global`, and `providers`

## 15. Final Sign-Off

- MiniMax path works with config defaults
- ElevenLabs path works with config defaults
- ElevenLabs timestamp sidecars are written only when explicitly enabled
- ElevenLabs continuity works only when explicitly enabled
- CLI overrides beat config values
- MiniMax-only flags are rejected for ElevenLabs
- `doctor` shows the correct active/inactive API key behavior
- `manifest.json` records the correct provider and effective settings
