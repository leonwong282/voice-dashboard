# ElevenLabs Next Implementation Roadmap

This roadmap starts from the current repository state on April 4, 2026.

For an execution-oriented checklist for this next stage, see [docs/ELEVENLABS_NEXT_IMPLEMENTATION_CHECKLIST.md](./ELEVENLABS_NEXT_IMPLEMENTATION_CHECKLIST.md).

It does not repeat already-finished work such as:

- provider-aware config schema
- provider-specific API keys
- basic ElevenLabs synthesis support
- current manual and automated test coverage

Instead, it focuses on the next implementation steps needed to make the provider model technically clean and to support more of the ElevenLabs TTS surface without reintroducing cross-provider confusion.

## 1. Current State

### Already in place

- config is provider-local:
  - `default_provider`
  - `global`
  - `providers.minimax`
  - `providers.elevenlabs`
- MiniMax and ElevenLabs use separate API keys
- ElevenLabs basic TTS works with:
  - existing `voice_id`
  - `model`
  - `speed`
  - fixed `output_format=mp3_44100_128`
- MiniMax-only flags are rejected under `--provider elevenlabs`

### Current technical gap

The config layer is already provider-specific, but the runtime settings model is not.

Today the code still uses one shared `TTSSettings` object containing:

- `model`
- `voice_id`
- `speed`
- `language_boost`
- `pitch`
- `sample_rate`
- `audio_format`

That means:

- ElevenLabs HTTP requests are not polluted by MiniMax fields
- but verbose logs and `manifest.json` still carry MiniMax-shaped fields during ElevenLabs runs
- the runtime model still implies a false shared API shape

This is the first thing that should be fixed.

## 2. Product Rules

The roadmap assumes the following rules remain true:

- the tool stays TTS-only
- `voice_id` is always provided by the user or config
- no voice clone/list/manage commands are added
- `global` remains for truly provider-independent values only
- provider-specific request fields must not be silently mixed into another provider's logs, manifest, or request model

## 3. Phase 1: Split Runtime Settings By Provider

### Goal

Replace the current shared `TTSSettings` model with provider-specific runtime settings.

### Why first

This is the architectural cleanup that prevents all future ElevenLabs work from being built on a misleading shared request model.

### Tasks

- Introduce a small common runtime layer for truly shared values only.
- Replace shared `TTSSettings` with separate settings types:
  - `MiniMaxTTSSettings`
  - `ElevenLabsTTSSettings`
- Update provider interfaces so each provider consumes its own settings shape.
- Stop assigning placeholder MiniMax values for ElevenLabs runs.
- Keep CLI resolution provider-aware from the moment settings are built.

### Acceptance

- ElevenLabs runtime settings no longer contain `language_boost`, `pitch`, or `sample_rate`
- MiniMax runtime settings remain unchanged
- providers no longer depend on irrelevant fields being present

## 4. Phase 2: Split Manifest And Verbose Output

### Goal

Make output artifacts describe the real provider-specific request shape instead of the old shared settings object.

### Tasks

- Replace `manifest.settings = {"provider": ..., **asdict(settings)}` with a structured form.
- Recommended structure:
  - `provider`
  - `common_settings`
  - `provider_settings`
- Update verbose logging to print only the active provider's settings.
- Ensure ElevenLabs runs no longer show MiniMax-only fields in logs or manifest.

### Acceptance

- `manifest.json` for ElevenLabs contains only ElevenLabs-relevant settings
- verbose logs for ElevenLabs no longer show MiniMax-only fields
- no secrets appear in any output artifacts

## 5. Phase 3: Promote ElevenLabs Config To A Real Provider Surface

### Goal

Stop treating ElevenLabs as only `voice_id + model + speed`.

### Recommended additions

Add provider-local config support for these ElevenLabs fields:

- `output_format`
- `language_code`
- `seed`
- `enable_logging`

Add nested `voice_settings` support:

- `stability`
- `similarity_boost`
- `style`
- `use_speaker_boost`
- `speed`

### Design rule

These values should live under `providers.elevenlabs`, not in `global`.

Example shape:

```json
{
  "providers": {
    "elevenlabs": {
      "voice_id": "voice_123",
      "model": "eleven_multilingual_v2",
      "output_format": "mp3_44100_128",
      "language_code": "zh",
      "seed": 12345,
      "enable_logging": true,
      "voice_settings": {
        "speed": 1.0,
        "stability": 0.5,
        "similarity_boost": 0.8,
        "style": 0.0,
        "use_speaker_boost": true
      }
    }
  }
}
```

### Acceptance

- ElevenLabs config can express provider-native request fields without abusing `global`
- adapter reads and validates them cleanly

## 6. Phase 4: Expand ElevenLabs Adapter Carefully

### Goal

Support more of the official ElevenLabs `Create speech` API while keeping the CLI manageable.

### Recommended order

#### 4.1 Low-risk additions

- `output_format`
- `language_code`
- `seed`
- `enable_logging`
- nested `voice_settings`

#### 4.2 Batch-tool-native additions

These fit this repository especially well because the tool already splits long text into segments:

- `previous_text`
- `next_text`
- optional segment-to-segment continuity helpers

#### 4.3 Optional advanced additions

- pronunciation dictionaries
- timestamp output endpoint
- streaming endpoint

### Acceptance

- request payload matches the documented ElevenLabs fields actually in use
- unsupported fields are not faked or silently ignored

## 7. Phase 5: Decide CLI Exposure Strategy

### Goal

Prevent the CLI from becoming an unstructured union of every provider flag.

### Recommendation

Use three categories of CLI surface:

#### Common flags

- `--provider`
- `--voice-id`
- `--model`
- `--speed`
- `--request-timeout`
- `--max-retries`
- `--output-dir`
- `--merge`

#### MiniMax-only flags

- `--pitch`
- `--language-boost`
- `--sample-rate`

#### ElevenLabs-only flags

Only expose these after Phase 1 and Phase 2 are complete:

- `--el-output-format`
- `--el-language-code`
- `--el-seed`
- `--el-stability`
- `--el-similarity-boost`
- `--el-style`
- `--el-use-speaker-boost`

### Rule

If a field is provider-native but rarely changed, config-only support is acceptable at first.

## 8. Phase 6: Continuity-Aware Batch Generation

### Goal

Use ElevenLabs features that actually matter for a paragraph-splitting batch tool.

### Why this matters

This repository already turns one text input into multiple TTS requests.

That makes continuity controls more valuable here than in many simpler wrappers.

### Tasks

- evaluate whether adjacent segments should automatically populate:
  - `previous_text`
  - `next_text`
- add an opt-in mode such as:
  - `--el-continuity adjacent-text`
- document when continuity improves results and when it can over-constrain generation

### Acceptance

- continuity behavior is opt-in and predictable
- output quality across adjacent segments improves in real manual tests

## 9. Phase 7: Timestamp And Streaming Strategy

### Goal

Decide whether this tool should remain a file-oriented batch CLI only, or also expose real-time/provider-native output modes.

### Recommendation

Do not start with streaming.

Prefer timestamps first if there is a downstream need for:

- subtitle alignment
- segment QA
- reading-speed analysis

Only add streaming if there is a concrete user workflow that benefits from it.

### Decision gate

- if the product remains primarily offline batch generation, timestamps are more aligned than streaming
- if interactive playback becomes a goal, streaming can become a separate track

## 10. Phase 8: Tests And Manual Verification

### Automated tests

Add coverage for:

- provider-specific runtime settings types
- provider-specific manifest output
- ElevenLabs nested `voice_settings`
- ElevenLabs `output_format` and `language_code`
- continuity request shaping
- config validation for unsupported provider keys

### Manual checks

Extend [docs/MANUAL_USABILITY_CHECKLIST.md](./MANUAL_USABILITY_CHECKLIST.md) with:

- ElevenLabs custom `output_format`
- ElevenLabs custom `voice_settings`
- continuity A/B comparison
- manifest sanity for provider-local fields only

## 11. Suggested Execution Order

Recommended next order:

1. Phase 1: split runtime settings by provider
2. Phase 2: split manifest and verbose output
3. Phase 3: add provider-local ElevenLabs config fields
4. Phase 4.1: support low-risk ElevenLabs API fields
5. Phase 5: expose only the minimum safe CLI flags
6. Phase 6: evaluate continuity support
7. Phase 7: decide timestamps vs streaming

## 12. What Not To Do

Avoid these shortcuts:

- do not keep one shared settings dataclass and keep adding optional fields forever
- do not record fake provider fields in manifests just because a shared object happens to contain them
- do not put ElevenLabs-native controls into `global`
- do not expose a large set of provider-native CLI flags before runtime settings are split cleanly

## 13. Definition Of Done For The Next Stage

The next stage is complete when all of the following are true:

- runtime settings are provider-specific
- ElevenLabs logs and manifest no longer contain MiniMax-only fields
- ElevenLabs provider config can express native request controls cleanly
- at least one expanded ElevenLabs feature set beyond `speed` is supported
- tests and manual verification cover the new provider-local behavior
