# ElevenLabs TTS Support Plan

This document describes how `voice-dashboard` should support ElevenLabs within the actual product scope of this repository.

This analysis was checked against the official ElevenLabs documentation on April 4, 2026.

For an execution-oriented task list, see [docs/ELEVENLABS_IMPLEMENTATION_CHECKLIST.md](./ELEVENLABS_IMPLEMENTATION_CHECKLIST.md).

## 1. Scope Clarification

`voice-dashboard` is a TTS execution tool only.

Its job is:

1. accept text input
2. call a provider TTS API with a user-supplied `voice_id`
3. write audio files and run-local artifacts

Its job is not:

- creating voices
- cloning voices
- listing voices
- managing provider-side voice assets

This means `voice_id` is treated as an input that the user already has. The tool does not care whether that `voice_id` came from:

- a provider default voice
- a previously cloned voice
- a custom voice created elsewhere

That clarification reduces the design scope substantially. We only need multi-provider TTS synthesis support.

## 2. Executive Summary

Supporting ElevenLabs is reasonable.

The integration is not mainly difficult because ElevenLabs is complicated. The real work is that the current codebase is shaped around MiniMax-specific assumptions:

- one fixed endpoint
- one fixed auth variable
- one fixed request shape
- one fixed response decoding path
- several MiniMax-specific CLI and config fields

Recommended product direction:

1. keep the tool TTS-only
2. add provider selection
3. support ElevenLabs synthesis with an existing `voice_id`
4. keep all non-TTS provider APIs out of scope

## 3. Recommended Product Boundary

### In scope

- `text -> audio` synthesis
- `voice_id` as required provider input
- `--provider {minimax,elevenlabs}`
- config-driven default provider
- provider-specific API key lookup
- shared batch flow:
  - input loading
  - paragraph splitting
  - output directory creation
  - manifest generation
  - optional merge

### Out of scope

- `voices list`
- `voices clone`
- any upload-based voice management
- any provider console replacement behavior
- feature parity across every advanced provider option

## 4. Why ElevenLabs Is A Good Fit

ElevenLabs is a reasonable second provider because it supports the same core runtime model this tool already uses:

- the caller already knows the `voice_id`
- the caller sends text plus synthesis settings
- the API returns generated audio

Primary TTS endpoint:

```text
POST https://api.elevenlabs.io/v1/text-to-speech/:voice_id
```

Key integration facts:

- `voice_id` is in the path
- auth uses `xi-api-key`
- output format is controlled by query parameter
- success response is raw audio bytes

That is different from MiniMax, but still fits the repo's batch pipeline well.

## 5. Core Design Decision

The tool should select a provider by configuration, with CLI override.

Recommended precedence:

1. CLI `--provider`
2. config file `provider`
3. built-in default `minimax`

This keeps the tool predictable:

- users can set a personal default once in config
- scripts can force the provider explicitly at runtime
- existing MiniMax users remain backward-compatible by default

## 6. API Key Strategy

Provider API keys should be separate environment variables.

Recommended variables:

- `MINIMAX_API_KEY`
- `ELEVENLABS_API_KEY`

Recommended runtime rule:

- resolve the active provider first
- read only the environment variable for that provider
- fail clearly if that specific variable is missing

Examples:

- if provider is `minimax`, require `MINIMAX_API_KEY`
- if provider is `elevenlabs`, require `ELEVENLABS_API_KEY`

Even if both variables are set, the tool should only use the one for the active provider.

### Do not put API keys in config

Config should not contain secrets.

Reasons:

- easy to commit by mistake
- easy to leak through `config show`
- harder to rotate safely
- unnecessary once provider-specific env vars exist

## 7. Config Design

The config should answer two questions:

1. which provider is the default
2. what defaults apply for common settings and provider-specific settings

Recommended shape:

```json
{
  "provider": "minimax",
  "defaults": {
    "voice_id": "clone_voice_can",
    "model": "speech-2.8-hd",
    "speed": 1.2,
    "format": "mp3",
    "request_timeout_seconds": 60,
    "max_retries": 3,
    "output_root": "~/Documents/voice-dashboard",
    "open_after_finish": false
  },
  "providers": {
    "minimax": {
      "pitch": 0,
      "language_boost": "Chinese,Yue",
      "sample_rate": 32000
    },
    "elevenlabs": {
      "output_format": "mp3_44100_128"
    }
  }
}
```

### Backward compatibility

Recommended rules:

- if `provider` is absent, default to `minimax`
- if `providers.minimax` is absent, continue reading legacy MiniMax keys from `defaults`
- old MiniMax-only config should continue to work without migration

## 8. CLI Design

Recommended common CLI options:

- `--provider {minimax,elevenlabs}`
- `--voice-id`
- `--model`
- `--speed`
- `--format`
- `--request-timeout`
- `--max-retries`

Recommended MiniMax-only CLI options:

- `--pitch`
- `--language-boost`
- `--sample-rate`

Recommended ElevenLabs-only option for the first phase:

- none exposed yet, or only internal config-backed `output_format`

Reason:

The first goal is multi-provider TTS support, not full provider surface exposure.

Validation rule:

- provider-specific options must fail fast when used with the wrong provider

Example:

```text
--pitch is only supported when --provider=minimax
```

## 9. Runtime Flow

Recommended runtime behavior:

1. load config
2. resolve active provider
3. resolve common settings
4. resolve provider-specific settings
5. read the provider-specific API key from environment
6. synthesize each segment through the selected provider adapter
7. write outputs and manifest as usual

This keeps provider logic isolated to one part of the application.

## 10. Architecture Recommendation

Keep the current batch pipeline shared. Move only provider-specific synthesis behind a provider interface.

Recommended module layout:

```text
voice_dashboard/
  providers/
    __init__.py
    base.py
    registry.py
    minimax.py
    elevenlabs.py
```

Recommended interface shape:

```python
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class SynthesisRequest:
    provider: str
    text: str
    voice_id: str
    model: str
    audio_format: str
    speed: float | None
    provider_options: dict[str, Any]


class TTSProvider(Protocol):
    name: str
    api_key_env_var: str

    def read_api_key(self) -> str:
        ...

    def synthesize(
        self,
        request: SynthesisRequest,
        request_timeout_seconds: int,
    ) -> bytes:
        ...
```

This abstraction only needs to isolate:

- auth header handling
- endpoint construction
- request payload formation
- response decoding
- provider-specific error parsing

Everything else should remain shared.

## 11. ElevenLabs MVP Request Mapping

Recommended first mapping for `--provider elevenlabs`:

- `POST /v1/text-to-speech/:voice_id`
- header `xi-api-key: $ELEVENLABS_API_KEY`
- query `output_format=mp3_44100_128`
- JSON body:
  - `text`
  - `model_id`
  - `voice_settings.speed` only when `speed` is provided
- write returned audio bytes directly to `*.mp3`

This is enough for a clean TTS-only MVP.

## 12. Doctor Command Behavior

`ttsrun doctor` should be provider-aware.

Recommended behavior:

- resolve active provider from CLI or config
- check only the active provider key as required
- keep optional local dependency checks unchanged

Examples:

- active provider `minimax`:
  - required: `MINIMAX_API_KEY`
- active provider `elevenlabs`:
  - required: `ELEVENLABS_API_KEY`

Optional enhancement:

- display the inactive provider key as informational only

## 13. Manifest Strategy

Manifest changes should be additive, not breaking.

Recommended direction:

```json
{
  "settings": {
    "provider": "elevenlabs",
    "voice_id": "JBFqnCBsd6RMkjVDRZzb",
    "model": "eleven_multilingual_v2",
    "speed": 1.0,
    "audio_format": "mp3",
    "provider_options": {
      "output_format": "mp3_44100_128"
    }
  }
}
```

Rules:

- include `provider`
- keep the existing settings block shape as stable as possible
- never store secrets in manifest output

## 14. Testing Plan

Recommended test coverage:

### 14.1 Refactor safety

- existing MiniMax behavior remains unchanged
- legacy config still defaults to MiniMax

### 14.2 Provider selection

- CLI `--provider` overrides config
- config `provider` is used when CLI is absent
- default provider is `minimax` when both are absent

### 14.3 API key behavior

- MiniMax provider requires `MINIMAX_API_KEY`
- ElevenLabs provider requires `ELEVENLABS_API_KEY`
- active provider ignores the inactive provider key

### 14.4 ElevenLabs request formation

- correct path includes `voice_id`
- correct `xi-api-key` header
- correct `output_format` query parameter
- correct body for `text`, `model_id`, and optional speed

### 14.5 ElevenLabs response handling

- binary audio is written correctly
- retries on network errors and `5xx`
- clear failure on `401` and `403`

## 15. Effort And Difficulty

Difficulty: medium

Why:

- the TTS-only scope is narrow
- no voice-management commands are needed
- the main work is refactoring MiniMax-specific assumptions into a provider abstraction
- config, doctor, and tests all need provider awareness

This is much smaller than a true multi-provider voice-management tool.

## 16. Recommended Implementation Order

1. Introduce provider abstraction with MiniMax moved behind it and no behavior change.
2. Add `provider` resolution from CLI and config.
3. Add provider-specific API key lookup.
4. Implement ElevenLabs synthesis adapter.
5. Update `doctor`, tests, usage docs, and README.

## 17. Expected File Touches

- `voice_dashboard/defaults.py`
- `voice_dashboard/config.py`
- `voice_dashboard/cli.py`
- `voice_dashboard/pipeline.py`
- `voice_dashboard/providers/base.py`
- `voice_dashboard/providers/registry.py`
- `voice_dashboard/providers/minimax.py`
- `voice_dashboard/providers/elevenlabs.py`
- `tests/test_voice.py`
- `tests/test_cli_integration.py`
- `docs/USAGE.md`
- `docs/COMPATIBILITY.md`
- `README.md`
- `README.zh-TW.md`

## 18. Example Usage

Use config to define the default provider:

```json
{
  "provider": "elevenlabs"
}
```

Then run:

```bash
export ELEVENLABS_API_KEY="..."
ttsrun input.txt
```

Or override provider explicitly:

```bash
export ELEVENLABS_API_KEY="..."
ttsrun --provider elevenlabs input.txt
```

MiniMax remains:

```bash
export MINIMAX_API_KEY="..."
ttsrun --provider minimax input.txt
```

## 19. External References

- ElevenLabs authentication:
  - https://elevenlabs.io/docs/api-reference/authentication
- ElevenLabs create speech:
  - https://elevenlabs.io/docs/api-reference/text-to-speech/convert
- ElevenLabs list models:
  - https://elevenlabs.io/docs/api-reference/models/list
