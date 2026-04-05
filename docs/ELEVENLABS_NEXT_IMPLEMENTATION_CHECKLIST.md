# ElevenLabs Next Implementation Checklist

This checklist turns the next-stage ElevenLabs roadmap into an execution sequence for the current repository state.

Use this document together with:

- [docs/ELEVENLABS_NEXT_ROADMAP.md](./ELEVENLABS_NEXT_ROADMAP.md)
- [docs/MANUAL_USABILITY_CHECKLIST.md](./MANUAL_USABILITY_CHECKLIST.md)

This is the post-MVP checklist. The earlier completed provider-integration work remains documented in [docs/ELEVENLABS_IMPLEMENTATION_CHECKLIST.md](./ELEVENLABS_IMPLEMENTATION_CHECKLIST.md).

## 1. Working Assumptions

- The tool remains TTS-only.
- `voice_id` is still an input the user already has.
- `global` remains only for provider-independent settings.
- Provider-native fields must not appear in another provider's runtime settings, verbose output, or manifest.
- ElevenLabs expansion should follow the official API surface instead of extending the old MiniMax-shaped runtime model.

## 2. Definition Of Done

The next stage is complete when all of the following are true:

- runtime settings are provider-specific rather than one shared dataclass
- ElevenLabs runs no longer carry MiniMax-only fields in logs or manifest
- `providers.elevenlabs` can express provider-native request settings cleanly
- ElevenLabs supports at least one expanded native settings set beyond `voice_id`, `model`, and `speed`
- automated tests cover the provider-local runtime and manifest behavior
- manual checks document the expanded ElevenLabs behavior clearly

## 3. Phase 1: Split Runtime Settings By Provider

### Files

- `voice_dashboard/pipeline.py`
- `voice_dashboard/cli.py`
- `voice_dashboard/providers/base.py`
- `voice_dashboard/providers/minimax.py`
- `voice_dashboard/providers/elevenlabs.py`

### Tasks

- [x] Introduce a small common runtime layer for truly shared values only.
- [x] Replace shared `TTSSettings` with separate provider runtime settings:
  - `MiniMaxTTSSettings`
  - `ElevenLabsTTSSettings`
- [x] Update provider interfaces so each provider consumes its own settings type.
- [x] Stop assigning placeholder MiniMax defaults to ElevenLabs runs.
- [x] Keep provider resolution stable while changing only the runtime settings model.

Acceptance:

- [x] ElevenLabs runtime settings no longer contain `language_boost`, `pitch`, or `sample_rate`.
- [x] MiniMax runtime behavior stays unchanged.
- [x] No provider depends on irrelevant fields being present.

## 4. Phase 2: Split Manifest And Verbose Output

### Files

- `voice_dashboard/pipeline.py`

### Tasks

- [ ] Replace `manifest.settings = {"provider": ..., **asdict(settings)}` with structured output.
- [ ] Recommended structure:
  - `provider`
  - `common_settings`
  - `provider_settings`
- [ ] Update verbose output to print only the active provider's settings.
- [ ] Ensure ElevenLabs logs and manifest do not display MiniMax-only fields.
- [ ] Keep output additive and stable where possible.

Acceptance:

- [ ] ElevenLabs manifest output contains only ElevenLabs-relevant provider settings.
- [ ] ElevenLabs verbose output no longer includes MiniMax-only fields.
- [ ] No secrets leak into output artifacts.

## 5. Phase 3: Promote ElevenLabs Config To A Real Provider Surface

### Files

- `voice_dashboard/config.py`
- `docs/USAGE.md`
- `docs/MANUAL_USABILITY_CHECKLIST.md`

### Tasks

- [ ] Add provider-local ElevenLabs config fields:
  - `output_format`
  - `language_code`
  - `seed`
  - `enable_logging`
- [ ] Add nested `voice_settings` under `providers.elevenlabs`.
- [ ] Support:
  - `stability`
  - `similarity_boost`
  - `style`
  - `use_speaker_boost`
  - `speed`
- [ ] Validate these fields inside the ElevenLabs config branch only.
- [ ] Keep these fields out of `global`.

Acceptance:

- [ ] ElevenLabs-native request fields can be stored in config without abusing shared fields.
- [ ] Invalid ElevenLabs config values fail with clear config errors.

## 6. Phase 4: Expand ElevenLabs Adapter With Low-Risk Fields

### Files

- `voice_dashboard/providers/elevenlabs.py`
- `voice_dashboard/config.py`
- `voice_dashboard/cli.py`

### Tasks

- [ ] Add adapter support for:
  - `output_format`
  - `language_code`
  - `seed`
  - `enable_logging`
- [ ] Add nested `voice_settings` request mapping.
- [ ] Only send provider-native fields that are actually configured.
- [ ] Keep unsupported fields out of the request body.
- [ ] Preserve current auth and retry behavior.

Acceptance:

- [ ] ElevenLabs request payload matches the documented fields actually in use.
- [ ] Existing MiniMax synthesis behavior is unchanged.
- [ ] Expanded ElevenLabs fields work from config without regressing the basic path.

## 7. Phase 5: Decide Minimal CLI Exposure

### Files

- `voice_dashboard/cli.py`
- `docs/USAGE.md`

### Tasks

- [ ] Keep the current common flags unchanged.
- [ ] Keep MiniMax-only flags explicit and provider-bound.
- [ ] Decide which ElevenLabs-native fields remain config-only for now.
- [ ] If exposing new CLI flags, keep the first set minimal:
  - `--el-output-format`
  - `--el-language-code`
  - `--el-seed`
  - `--el-stability`
  - `--el-similarity-boost`
  - `--el-style`
  - `--el-use-speaker-boost`
- [ ] Reject ElevenLabs-only flags when MiniMax is active, if any are added.

Acceptance:

- [ ] CLI remains understandable and does not become a union of every provider field.
- [ ] Provider-specific flags remain clearly separated.

## 8. Phase 6: Continuity-Aware Batch Generation

### Files

- `voice_dashboard/providers/elevenlabs.py`
- `voice_dashboard/cli.py`
- `voice_dashboard/pipeline.py`
- `docs/USAGE.md`
- `docs/MANUAL_USABILITY_CHECKLIST.md`

### Tasks

- [ ] Evaluate support for `previous_text` and `next_text`.
- [ ] Decide whether continuity should be:
  - config-only
  - CLI opt-in
  - automatic but explicitly documented
- [ ] If added, keep the first mode opt-in and predictable.
- [ ] Document when continuity helps and when it can over-constrain generation.

Acceptance:

- [ ] Continuity behavior is explicit and testable.
- [ ] Manual A/B checks show whether adjacent-segment quality improves.

## 9. Phase 7: Timestamp And Streaming Decision

### Files

- `docs/ELEVENLABS_NEXT_ROADMAP.md`
- `docs/USAGE.md`

### Tasks

- [ ] Decide whether the next priority is timestamps or streaming.
- [ ] Document the decision and rationale.
- [ ] If timestamps are chosen, define the target output shape before coding.
- [ ] If streaming is chosen, define how it fits a file-oriented batch CLI before coding.

Acceptance:

- [ ] There is one explicit direction rather than both being partially implemented.

## 10. Phase 8: Tests And Manual Verification

### Files

- `tests/test_voice.py`
- `tests/test_cli_integration.py`
- `docs/MANUAL_USABILITY_CHECKLIST.md`

### Tasks

- [ ] Add tests for provider-specific runtime settings types.
- [ ] Add tests for provider-specific manifest output.
- [ ] Add tests for ElevenLabs nested `voice_settings`.
- [ ] Add tests for ElevenLabs `output_format`, `language_code`, and `seed`.
- [ ] Add tests for continuity request shaping if continuity is implemented.
- [ ] Extend the manual checklist with new ElevenLabs-specific verification steps.

Acceptance:

- [ ] `pytest -q` passes locally.
- [ ] Manual verification steps cover the expanded ElevenLabs path.

## 11. Suggested Execution Order

Recommended order:

1. Phase 1: split runtime settings by provider
2. Phase 2: split manifest and verbose output
3. Phase 3: add provider-local ElevenLabs config fields
4. Phase 4: expand low-risk ElevenLabs API fields
5. Phase 5: expose only the minimum safe CLI surface
6. Phase 6: evaluate continuity support
7. Phase 7: choose timestamps or streaming
8. Phase 8: finalize tests and manual verification

## 12. Final Verification Commands

Run before considering this next stage complete:

```bash
python3 -m pyflakes voice_dashboard tests
python3 -m pytest -q
```

Then manually verify the expanded ElevenLabs path using:

```bash
ttsrun config show
ttsrun doctor --provider elevenlabs
ttsrun --provider elevenlabs /path/to/input.txt
```

If expanded provider-native fields are added, also run at least one real ElevenLabs synthesis using those fields and confirm the resulting `manifest.json` contains only provider-local settings.
