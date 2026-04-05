# MiniMax Async Correction Plan

This document replaces the earlier MiniMax async implementation assumptions with the flow validated by the local working example:

- [test-async.py](/Users/liang/Downloads/repository/voice-dashboard/examples/test-async.py)
- [tts_output](/Users/liang/Downloads/repository/voice-dashboard/examples/tts_output)

## 1. Verified Correct Flow

The confirmed MiniMax async flow is:

1. `POST /v1/t2a_async_v2` to create a task
2. `GET /v1/query/t2a_async_query_v2?task_id=...` until `Success`
3. `GET /v1/files/retrieve?file_id=...`
4. read `file.download_url`
5. `GET download_url` directly without `Authorization`
6. receive a `.tar` archive
7. extract provider files such as:
   - `*.mp3`
   - `*.titles`
   - `*.extra`
8. optionally convert `.titles` into a derived local `.srt`

This is the behavior demonstrated in [test-async.py](/Users/liang/Downloads/repository/voice-dashboard/examples/test-async.py).

## 2. What The Current Implementation Gets Wrong

The current implementation in [minimax_async.py](/Users/liang/Downloads/repository/voice-dashboard/voice_dashboard/providers/minimax_async.py) is incorrect in several important ways.

### 2.1 Wrong download path

Current code:

- calls `GET /v1/files/retrieve_content?file_id=...`
- assumes that response bytes are the final result payload

Correct behavior from the working example:

- call `GET /v1/files/retrieve?file_id=...`
- read `file.download_url`
- download the archive from that URL directly

Implication:

- the current implementation is using the wrong final download mechanism
- it also ignores the provider-returned download indirection entirely

### 2.2 Wrong archive type

Current code:

- assumes the downloaded bundle is ZIP
- parses it with `zipfile.ZipFile`

Correct behavior from the working example:

- the downloaded payload is `.tar`
- it must be extracted with `tarfile`

Implication:

- the current archive extraction layer is fundamentally incompatible with the real output

### 2.3 Wrong attachment expectations

Current code expects:

- subtitle files like `.srt`, `.vtt`, `.ass`
- extra JSON files like `.json`

Real output in [tts_output](/Users/liang/Downloads/repository/voice-dashboard/examples/tts_output):

- `...mp3`
- `...titles`
- `...extra`

Implication:

- current attachment detection will miss the real provider outputs
- subtitle handling is coupled to the wrong file extensions

### 2.4 Wrong subtitle model

Current code assumes:

- subtitle-like output can be treated as generic downloaded attachment content

Real output in [content-1999137282161906420_202604051437_384264756052083_384264756052084.titles](/Users/liang/Downloads/repository/voice-dashboard/examples/tts_output/content-1999137282161906420_202604051437_384264756052083_384264756052084.titles):

- JSON array entries
- fields include:
  - `text`
  - `pronounce_text`
  - `time_begin`
  - `time_end`
  - `text_begin`
  - `text_end`

Implication:

- `.titles` is a MiniMax-specific subtitle JSON format
- `.srt` should be a derived local artifact, not assumed provider-native output

### 2.5 Wrong local output assumptions

Current code normalizes provider files into:

- `output.mp3`
- `output.srt`
- `output.extra.json`

But the working example preserves provider file names first, then derives:

- provider original audio
- provider original `.titles`
- provider original `.extra`
- optional local `subtitle.srt`

Implication:

- current implementation throws away useful provider naming and format distinctions too early

## 3. Target Design

MiniMax async should be treated as:

- whole-input only
- tar-archive output provider
- provider-native subtitle JSON consumer
- optional local SRT generator

The tool should preserve provider-native artifacts and add normalized convenience artifacts only where useful.

## 4. Correct Output Contract

Recommended local output contract for `minimax-async`:

- preserve original extracted provider files:
  - `*.mp3`
  - `*.titles`
  - `*.extra`
- optionally generate:
  - `subtitle.srt`
- continue writing:
  - `manifest.json`
  - `errors.jsonl`

Recommended manifest summary additions:

- `task_id`
- `file_id`
- `remote_status`
- `remote_filename`
- `remote_download_url`
- `audio_file`
- `titles_file`
- `extra_file`
- `subtitle_srt_file`

Recommended segment entry:

- still use one synthetic segment entry because this remains a whole-input provider
- `output_file` should point to the real extracted audio filename, not forced `output.mp3`

## 5. Real Implementation Plan

### Phase 1: Fix Download Flow

Update [minimax_async.py](/Users/liang/Downloads/repository/voice-dashboard/voice_dashboard/providers/minimax_async.py):

- keep create task logic
- keep task polling logic
- keep `files/retrieve`
- remove `files/retrieve_content` as the primary download path
- add direct download via `file.download_url`
- perform that download without `Authorization`

Acceptance:

- provider successfully downloads bytes from `download_url`
- code no longer assumes `retrieve_content` is the final artifact path

### Phase 2: Replace ZIP Handling With TAR Handling

Update extraction logic in [minimax_async.py](/Users/liang/Downloads/repository/voice-dashboard/voice_dashboard/providers/minimax_async.py):

- remove ZIP-only extraction logic
- replace with `tarfile`
- support `.tar` and compressed tar variants via `mode=\"r:*\"`

Acceptance:

- local sample archive shape is parsed correctly
- extracted members are available with original names

### Phase 3: Detect Real MiniMax Output Types

Update attachment detection:

- audio: `*.mp3` or configured audio format
- titles: `*.titles`
- extra: `*.extra`

Do not treat `.titles` as `timestamps`.

Acceptance:

- provider correctly identifies audio, titles, and extra files from the extracted tar

### Phase 4: Preserve Provider File Names

Update [pipeline.py](/Users/liang/Downloads/repository/voice-dashboard/voice_dashboard/pipeline.py):

- write extracted provider files using their original basenames
- stop forcing audio to `output.mp3`
- stop forcing provider subtitle JSON to `output.srt`
- write `subtitle.srt` only as an additional derived file

Acceptance:

- output directory resembles the validated sample layout
- users can inspect original provider artifacts directly

### Phase 5: Add `.titles` -> `.srt` Conversion

Introduce a MiniMax subtitle conversion helper.

Expected input shape from `.titles`:

- list of subtitle items
- each item contains `time_begin`, `time_end`, and `text`

Generate:

- `subtitle.srt`

Acceptance:

- generated SRT matches the real subtitle timing semantics used by the working example

### Phase 6: Fix Result/Manifest Model

Adjust result modeling in [base.py](/Users/liang/Downloads/repository/voice-dashboard/voice_dashboard/providers/base.py) and [pipeline.py](/Users/liang/Downloads/repository/voice-dashboard/voice_dashboard/pipeline.py):

- represent provider-native attachments explicitly
- record original filenames in manifest
- add derived subtitle SRT pointer separately

Recommended summary fields:

- `audio_file`
- `titles_file`
- `extra_file`
- `subtitle_srt_file`

Acceptance:

- manifest matches actual on-disk artifacts
- no field incorrectly implies ElevenLabs-style timestamp support

### Phase 7: Re-scope Config Surface

Review [config.py](/Users/liang/Downloads/repository/voice-dashboard/voice_dashboard/config.py).

Current `subtitles: true` should mean:

- keep and process `.titles`
- derive `subtitle.srt`

It should not mean:

- expect provider-native `.srt`

Potential additions for correctness:

- `generate_srt: true`
- `preserve_provider_artifacts: true`

This can still remain config-only at first.

Acceptance:

- config names map to real async outputs
- option semantics are not misleading

### Phase 8: Update Tests To Match Real API Semantics

Replace incorrect mocks in [test_voice.py](/Users/liang/Downloads/repository/voice-dashboard/tests/test_voice.py):

- stop mocking ZIP bundles
- mock `files/retrieve` returning `download_url`
- mock unauthenticated download from `download_url`
- use `.tar` bundle fixtures
- use `.titles` and `.extra` files
- validate generated `subtitle.srt`

Acceptance:

- tests lock the correct provider behavior
- tests fail if code regresses back to ZIP or `retrieve_content`

### Phase 9: Update User Docs

Update:

- [USAGE.md](/Users/liang/Downloads/repository/voice-dashboard/docs/USAGE.md)
- [MANUAL_USABILITY_CHECKLIST.md](/Users/liang/Downloads/repository/voice-dashboard/docs/MANUAL_USABILITY_CHECKLIST.md)

Document:

- MiniMax async preserves provider files
- `.titles` is provider subtitle JSON
- `subtitle.srt` is derived locally
- `--merge` still remains invalid for `minimax-async`

## 6. Priority Order

Recommended execution order:

1. fix download flow
2. switch ZIP to TAR
3. support `.titles` and `.extra`
4. preserve original filenames
5. generate `subtitle.srt`
6. update tests
7. update docs

## 7. Final Judgment

The current `minimax-async` implementation should not be iterated incrementally from its current assumptions.

It needs a correction pass because the core model is wrong in three foundational places:

- wrong download path
- wrong archive format
- wrong subtitle artifact assumptions

The good news is that the correct flow is now concrete and reproducible because the repository already contains:

- a working script
- real output artifacts

So the next implementation pass should be straightforward and evidence-based rather than speculative.
