# MiniMax Async Provider Plan

This document describes how to introduce MiniMax async TTS into the current repository by treating MiniMax sync and MiniMax async as two separate providers.

## 1. Decision

Adopt two MiniMax providers instead of one provider with an internal `mode` switch.

Recommended provider names:

- `minimax-sync`
- `minimax-async`

Migration recommendation:

- keep `minimax` as a temporary alias to `minimax-sync`
- expose `minimax-async` explicitly as the new long-text / subtitle-oriented provider
- remove the alias only in a later breaking release if desired

## 2. Why This Is The Right Shape

MiniMax sync and MiniMax async are not just two endpoints for the same execution model.

They differ in:

- request/response lifecycle
- result retrieval flow
- output artifacts
- timeout and retry behavior
- best-fit user workflows

MiniMax sync is a one-shot request that returns audio immediately.

MiniMax async is:

1. create task
2. poll task state
3. retrieve file metadata
4. download result files

That is a different provider behavior, not just a slightly different payload.

Treating them as separate providers keeps:

- runtime settings cleaner
- manifest semantics clearer
- CLI and doctor behavior easier to explain
- long-text subtitle workflows isolated from current segment-based sync logic

## 3. Product Positioning

Recommended positioning:

- `minimax-sync`: short-form, paragraph-split, one-request-per-segment generation
- `minimax-async`: long-form, whole-document generation with subtitle outputs
- `elevenlabs`: paragraph-split generation with optional timestamps and continuity

This aligns provider choice with user intent instead of forcing one provider to hide two incompatible modes.

## 4. Official API Basis

Relevant MiniMax docs:

- Sync TTS HTTP:
  - https://platform.minimaxi.com/docs/api-reference/speech-t2a-http
- Async create:
  - https://platform.minimaxi.com/docs/api-reference/speech-t2a-async-create
- Async query:
  - https://platform.minimaxi.com/docs/api-reference/speech-t2a-async-query
- Async guide:
  - https://platform.minimaxi.com/docs/guides/speech-t2a-async
- File retrieve:
  - https://platform.minimaxi.com/docs/api-reference/file-management-retrieve
- File content:
  - https://platform.minimaxi.com/docs/api-reference/file-management-retrieve-content

MiniMax async is the stronger fit for automatic subtitle workflows because the official async flow explicitly supports subtitle outputs.

## 5. Recommended Provider Contract

### 5.1 `minimax-sync`

Keep current behavior:

- input text is split by blank lines
- each segment becomes one request
- output is `0001.mp3`, `0002.mp3`, ...
- `--merge` remains meaningful

### 5.2 `minimax-async`

New behavior:

- submit the whole normalized input as one async task
- poll until terminal state
- retrieve and download result files
- write one primary audio file plus subtitle / metadata artifacts
- do not use segment-level generation

Important rule:

`minimax-async` should bypass the existing per-segment synthesis loop.

## 6. Config Design

Recommended config shape:

```json
{
  "default_provider": "minimax-sync",
  "providers": {
    "minimax-sync": {
      "voice_id": "sync_voice_id",
      "model": "speech-2.8-hd",
      "speed": 1.2,
      "pitch": 0,
      "language_boost": "Chinese,Yue",
      "sample_rate": 32000
    },
    "minimax-async": {
      "voice_id": "async_voice_id",
      "model": "speech-2.8-hd",
      "speed": 1.0,
      "pitch": 0,
      "language_boost": "Chinese,Yue",
      "sample_rate": 32000,
      "subtitles": true,
      "poll_interval_seconds": 2,
      "task_timeout_seconds": 900
    }
  }
}
```

Recommended first-phase `minimax-async` fields:

- `voice_id`
- `model`
- `speed`
- `pitch`
- `language_boost`
- `sample_rate`
- `subtitles`
- `poll_interval_seconds`
- `task_timeout_seconds`

Deferred fields:

- `pronunciation_dict`
- `voice_modify`
- `timbre_weights`
- `emotion`
- `vol`
- `bitrate`
- `channel`
- file-upload text input

## 7. Runtime Design

### 7.1 Provider Settings

Add a dedicated `MiniMaxAsyncTTSSettings` runtime dataclass.

Do not reuse `MiniMaxTTSSettings` directly.

Recommended fields:

- `common`
- `language_boost`
- `pitch`
- `sample_rate`
- `subtitles`
- `poll_interval_seconds`
- `task_timeout_seconds`

### 7.2 Provider Registry

Registry target state:

- `minimax-sync`
- `minimax-async`
- `elevenlabs`

Optional temporary alias:

- `minimax` -> `minimax-sync`

### 7.3 Provider Result Model

Current `SynthesisResult` already supports additive metadata.

It should be extended only if needed for async attachments, for example:

- `audio_bytes`
- `timestamps`
- `attachments`

Recommended attachment shape:

- subtitle file
- extra info JSON

If attachment handling becomes too awkward inside `SynthesisResult`, introduce a separate async result model rather than forcing segment-oriented assumptions.

## 8. Pipeline Design

This is the main cost center.

### 8.1 Current mismatch

Current pipeline is segment-oriented:

1. parse input into segments
2. call provider once per segment
3. write per-segment files
4. optionally merge

That fits `minimax-sync` and `elevenlabs`.

It does not fit `minimax-async`.

### 8.2 Recommended solution

Add a separate pipeline path for whole-document providers.

Recommended split:

- keep current `run_batch_job()` for segment-based providers
- add `run_whole_input_job()` for providers like `minimax-async`

Provider capability can be declared via:

- registry metadata, or
- a provider method/property such as `execution_mode = "segment"` vs `"whole_input"`

### 8.3 Behavior of `minimax-async`

Recommended whole-input flow:

1. normalize input text
2. create async task
3. poll task status until `success`, `failed`, or timeout
4. retrieve file metadata by `file_id`
5. download primary audio
6. download subtitle file if present
7. download extra info JSON if present
8. write local artifacts
9. write manifest

### 8.4 Merge behavior

For `minimax-async`:

- `--merge` should be rejected, or
- treated as a no-op with an explicit warning

Recommendation:

- reject it for `minimax-async`

Reason:

There is only one primary output file in the intended async flow.

## 9. Output Artifacts

Recommended local artifact shape for `minimax-async`:

- `output.mp3`
- `output.srt` or provider subtitle file name if the API returns one
- `output.extra.json`
- `manifest.json`
- `errors.jsonl`

Recommended manifest shape:

```json
{
  "input_source": "file",
  "settings": {
    "provider": "minimax-async",
    "common_settings": { "...": "..." },
    "provider_settings": { "...": "..." }
  },
  "summary": {
    "task_id": 123,
    "remote_status": "success",
    "file_id": 456,
    "subtitle_file": "output.srt",
    "extra_file": "output.extra.json",
    "merged_output_file": null,
    "merge_status": "skipped"
  },
  "segments": [
    {
      "index": 1,
      "text": "<whole input>",
      "output_file": "output.mp3",
      "timestamp_file": null,
      "timestamp_status": "skipped",
      "status": "success",
      "error": null
    }
  ]
}
```

Important:

- preserve `manifest.json` as the main output index
- do not pretend async subtitles are the same thing as ElevenLabs character timestamps

## 10. CLI And UX

Recommended CLI behavior:

- expose provider selection only:
  - `--provider minimax-sync`
  - `--provider minimax-async`
- keep common flags:
  - `--voice-id`
  - `--model`
  - `--speed`
  - `--request-timeout`
  - `--max-retries`
- keep MiniMax-specific flags provider-bound:
  - `--pitch`
  - `--language-boost`
  - `--sample-rate`

Keep async-only knobs config-only at first:

- `subtitles`
- `poll_interval_seconds`
- `task_timeout_seconds`

Why:

- avoids expanding CLI too early
- keeps current user mental model stable

## 11. Error Model

`minimax-async` needs new failure categories beyond simple HTTP failure:

- task creation failure
- polling timeout
- remote task failed
- remote task expired
- file metadata retrieval failure
- file download failure
- subtitle file missing when requested

These should still map onto existing exit code categories where possible:

- auth
- api/network
- runtime

## 12. Cost Assessment

### Low cost

- provider registry changes
- config model changes
- doctor/env support
- new provider dataclasses

### Medium cost

- async provider implementation
- polling logic
- file retrieve/download flow
- manifest expansion
- tests and docs

### High cost

- replacing current `minimax` default behavior outright
- forcing whole-input and segment-input providers through one pipeline path
- preserving every existing output expectation while changing MiniMax semantics underneath users

Overall assessment:

- adding `minimax-async` as a new provider: medium cost
- replacing current `minimax` with async by default immediately: medium-high to high cost

## 13. Implementation Phases

### Phase 1: Provider Split

- add `minimax-sync` provider identity
- add `minimax-async` provider identity
- optionally keep `minimax` alias to sync
- update config validation and doctor logic

### Phase 2: Async Config Surface

- add `MiniMaxAsyncConfig`
- add `MiniMaxAsyncTTSSettings`
- support:
  - `subtitles`
  - `poll_interval_seconds`
  - `task_timeout_seconds`

### Phase 3: Async Provider Client

- implement async create request
- implement query polling
- implement file metadata retrieval
- implement file content download
- map remote outputs into local artifacts

### Phase 4: Whole-Input Pipeline

- add `run_whole_input_job()`
- route `minimax-async` into whole-input path
- reject `--merge` under `minimax-async`

### Phase 5: Manifest And Output Contract

- finalize manifest fields
- finalize subtitle and extra-file naming
- ensure `errors.jsonl` behavior remains consistent

### Phase 6: Tests And Manual Validation

- provider resolution tests
- async polling tests
- file download tests
- manifest contract tests
- real MiniMax async validation with subtitle output

## 14. Recommendation

Proceed with the split-provider approach.

Do not replace the current sync provider in-place first.

Recommended first milestone:

- ship `minimax-async` alongside current `minimax-sync`
- validate subtitle output on real jobs
- only after that decide whether `minimax` should continue pointing to sync or move to async in a later release
