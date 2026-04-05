# ElevenLabs Implementation Checklist

This checklist turns the ElevenLabs TTS support plan into an execution sequence for this repository.

Use this document together with [docs/ELEVENLABS_SUPPORT_PLAN.md](./ELEVENLABS_SUPPORT_PLAN.md).

For the post-MVP next-stage checklist, see [docs/ELEVENLABS_NEXT_IMPLEMENTATION_CHECKLIST.md](./ELEVENLABS_NEXT_IMPLEMENTATION_CHECKLIST.md).

## 1. Working Assumptions

- The tool remains TTS-only.
- `voice_id` is an input the user already has.
- No voice cloning, voice listing, or voice management commands are part of this work.
- Provider selection must support both config defaults and CLI override.
- API keys must remain in environment variables, not config.

## 2. Definition Of Done

The implementation is done when all of the following are true:

- `ttsrun` can synthesize with MiniMax exactly as before.
- `ttsrun --provider elevenlabs <input>` works with an existing ElevenLabs `voice_id`.
- provider resolution follows `CLI > config > default`
- MiniMax uses `MINIMAX_API_KEY`
- ElevenLabs uses `ELEVENLABS_API_KEY`
- `ttsrun doctor` validates the active provider key correctly
- tests cover MiniMax backward compatibility and ElevenLabs synthesis behavior
- docs explain provider selection and API key setup

## 3. Phase 0: Freeze Scope

- [x] Confirm in code comments and docs that the feature is "multi-provider TTS" rather than "multi-provider voice management".
- [x] Keep `voices list`, `voices clone`, and related commands out of the implementation scope.
- [x] Avoid adding provider-specific advanced flags unless they are required for the TTS MVP.
- [x] Keep first ElevenLabs output support narrow and stable.
Acceptance:
- [x] No new non-TTS command surface is introduced.

## 4. Phase 1: Introduce Provider Abstraction Without Behavior Change

### Files

- `voice_dashboard/pipeline.py`
- `voice_dashboard/providers/base.py`
- `voice_dashboard/providers/registry.py`
- `voice_dashboard/providers/minimax.py`

### Tasks

- [x] Create a provider interface for TTS synthesis.
- [x] Move MiniMax request construction and response decoding into `providers/minimax.py`.
- [x] Keep the batch pipeline responsible only for shared orchestration:
  - input loading
  - segmentation
  - retries
  - file writing
  - manifest generation
  - merge flow
- [x] Add a provider registry that can resolve `minimax` and later `elevenlabs`.
- [x] Keep default behavior unchanged while only `minimax` is active.

Acceptance:

- [x] Existing MiniMax code path still produces the same runtime behavior.
- [x] Existing MiniMax tests pass without needing provider-specific CLI changes yet.

## 5. Phase 2: Add Provider Resolution To Config And CLI

### Files

- `voice_dashboard/config.py`
- `voice_dashboard/cli.py`
- `voice_dashboard/defaults.py`

### Tasks

- [x] Add top-level config field `provider`.
- [x] Default provider to `minimax` when config does not specify one.
- [x] Add `--provider {minimax,elevenlabs}` to CLI.
- [x] Implement precedence rule: `CLI > config > default`.
- [x] Separate common TTS settings from provider-specific settings in code.
- [x] Preserve legacy MiniMax config parsing from `defaults` for backward compatibility.
- [x] Keep current MiniMax defaults intact for users who do not opt into provider selection.

Acceptance:

- [x] A legacy MiniMax config with no `provider` still works.
- [x] `ttsrun --provider minimax` behaves the same as before.
- [x] `ttsrun --provider elevenlabs` is parsed successfully even before the adapter is complete.

## 6. Phase 3: Add Provider-Specific API Key Resolution

### Files

- `voice_dashboard/pipeline.py`
- `voice_dashboard/providers/base.py`
- `voice_dashboard/providers/minimax.py`
- `voice_dashboard/providers/elevenlabs.py`
- `voice_dashboard/cli.py`

### Tasks

- [x] Stop using one hard-coded API key lookup path.
- [x] Resolve the active provider before reading any API key.
- [x] For MiniMax, read `MINIMAX_API_KEY`.
- [x] For ElevenLabs, read `ELEVENLABS_API_KEY`.
- [x] Return clear provider-specific auth errors.
- [x] Update `ttsrun doctor` to validate only the active provider key as required.
- [x] Optionally report the inactive provider key as informational only.

Acceptance:

- [x] Active provider auth succeeds when the correct env var is present.
- [x] Active provider auth fails clearly when the correct env var is missing.
- [x] Presence or absence of the inactive provider key does not affect the run.

## 7. Phase 4: Implement ElevenLabs TTS Adapter

### Files

- `voice_dashboard/providers/elevenlabs.py`
- `voice_dashboard/providers/registry.py`

### Tasks

- [x] Add ElevenLabs provider registration.
- [x] Implement `POST /v1/text-to-speech/:voice_id`.
- [x] Send auth via `xi-api-key`.
- [x] Use an MP3 output format that is fixed and documented for the MVP.
- [x] Map common request fields:
  - `text`
  - `voice_id`
  - `model`
  - optional `speed`
- [x] Encode ElevenLabs request JSON correctly.
- [x] Decode raw audio bytes from the response body.
- [x] Handle retryable network and `5xx` failures consistently with the existing retry model.
- [x] Handle `401` and `403` as authentication errors.
- [x] Parse non-success errors into stable user-facing messages.

Acceptance:

- [x] A successful ElevenLabs request writes a playable MP3 file.
- [x] Retry behavior works for transient failures.
- [x] Auth failures produce clear provider-specific errors.

## 8. Phase 5: Validate Provider-Specific Option Boundaries

### Files

- `voice_dashboard/cli.py`
- `voice_dashboard/config.py`

### Tasks

- [x] Keep MiniMax-only options explicit:
  - `--pitch`
  - `--language-boost`
  - `--sample-rate`
- [x] Reject MiniMax-only options when `--provider elevenlabs` is active.
- [x] Avoid exposing new ElevenLabs-only flags unless they are required for the MVP.
- [x] If ElevenLabs needs one provider-specific default such as `output_format`, keep it config-backed or internal for the first pass.

Acceptance:

- [x] `--pitch` with `--provider elevenlabs` fails fast with a clear input error.
- [x] Common options like `--voice-id`, `--model`, and `--speed` work for both providers.

## 9. Phase 6: Keep Manifest And Output Stable

### Files

- `voice_dashboard/pipeline.py`

### Tasks

- [x] Add `provider` to the persisted settings block.
- [x] Preserve existing output directory and merge behavior.
- [x] Keep manifest changes additive rather than breaking.
- [x] Do not leak secrets into manifest output.
- [x] Include provider-specific settings only where they are useful and stable.

Acceptance:

- [x] Existing automation relying on current output files still works or requires only additive handling.
- [x] Manifest output clearly shows which provider generated the audio.

## 10. Phase 7: Test Coverage

### Files

- `tests/test_voice.py`
- `tests/test_cli_integration.py`

### Tasks

- [x] Keep current MiniMax regression coverage passing.
- [x] Add provider resolution tests:
  - CLI overrides config
  - config overrides default
  - default falls back to MiniMax
- [x] Add API key tests:
  - MiniMax requires `MINIMAX_API_KEY`
  - ElevenLabs requires `ELEVENLABS_API_KEY`
- [x] Add ElevenLabs request tests:
  - path includes `voice_id`
  - correct auth header
  - correct query parameter for output format
  - correct JSON body for text/model/speed
- [x] Add ElevenLabs response tests:
  - success writes binary audio
  - `401` and `403` map to auth failure
  - network errors and `5xx` retry
- [x] Add CLI validation tests for provider-specific flag rejection.
- [x] Add `doctor` tests for provider-aware environment validation.

Acceptance:

- [x] `pytest -q` passes locally.
- [x] No MiniMax regression is introduced.

## 11. Phase 8: Documentation Updates

### Files

- `docs/USAGE.md`
- `docs/COMPATIBILITY.md`
- `docs/DEVELOPMENT.md`
- `README.md`
- `README.zh-TW.md`
- `CONTRIBUTING.md`

### Tasks

- [x] Document `--provider`.
- [x] Document config-based default provider.
- [x] Document separate env vars for each provider.
- [x] Document that the tool remains TTS-only.
- [x] Document any provider-specific limitations of the ElevenLabs MVP.
- [x] Update examples for both MiniMax and ElevenLabs runs.

Acceptance:

- [x] A new user can determine how to run MiniMax and ElevenLabs from the docs alone.

## 12. Suggested Execution Order For PRs

Recommended split if you do not want one oversized PR:

1. PR 1: provider abstraction with MiniMax only, no behavior change
2. PR 2: config and CLI provider resolution
3. PR 3: ElevenLabs adapter plus tests
4. PR 4: docs cleanup and polish

If you prefer one implementation branch, still keep commits separated in roughly that order.

## 13. Final Verification Commands

Run before considering the work complete:

```bash
make check
```

And manually smoke-test both providers:

```bash
MINIMAX_API_KEY=test-key ttsrun doctor
ELEVENLABS_API_KEY=test-key ttsrun --provider elevenlabs --help
ttsrun config example
ttsrun config show
```

If you have real credentials available, also run one real synthesis for each provider with a known `voice_id`.
