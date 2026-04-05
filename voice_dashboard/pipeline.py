import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, TextIO

from voice_dashboard.defaults import DEFAULT_MAX_RETRIES, DEFAULT_TIMEOUT_SECONDS
from voice_dashboard.errors import (
    ApiError,
    DependencyError,
    ExitCode,
    InputSourceError,
    RetryableApiError,
    TTSBatchError,
    exit_code_for_error,
)
from voice_dashboard.input_sources import InputSource
from voice_dashboard.providers import DEFAULT_PROVIDER_NAME, get_provider
from voice_dashboard.providers.base import (
    ProviderTTSSettings,
    SegmentSynthesisContext,
    SynthesisResult,
    serialize_common_settings,
    serialize_provider_settings,
)
from voice_dashboard.providers.minimax import requests as provider_requests

# Compatibility alias for existing tests that patch `voice_dashboard.pipeline.requests.post`.
requests = provider_requests


@dataclass(frozen=True)
class BatchResult:
    exit_code: int
    output_dir: Path
    manifest: dict[str, Any]


@dataclass(frozen=True)
class RequestSettings:
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    max_retries: int = DEFAULT_MAX_RETRIES


@dataclass(frozen=True)
class CleanupResult:
    deleted_count: int
    error: str | None = None
    backup_dir: Path | None = None


@dataclass
class ProgressReporter:
    quiet: bool = False
    verbose: bool = False
    stream: TextIO = sys.stderr

    def info(self, message: str) -> None:
        if not self.quiet:
            print(message, file=self.stream)

    def detail(self, message: str) -> None:
        if self.verbose and not self.quiet:
            print(message, file=self.stream)

    def warn(self, message: str) -> None:
        print(message, file=self.stream)

    def error(self, message: str) -> None:
        print(message, file=self.stream)


def parse_segments(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []

    segments = re.split(r"\n\s*\n+", normalized)
    return [segment.strip() for segment in segments if segment.strip()]


def normalize_whole_input(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def get_api_key(provider_name: str = DEFAULT_PROVIDER_NAME) -> str:
    return get_provider(provider_name).read_api_key()


def synthesize_segment(
    text: str,
    settings: ProviderTTSSettings,
    api_key: str,
    request_settings: RequestSettings | None = None,
    reporter: ProgressReporter | None = None,
    provider_name: str = DEFAULT_PROVIDER_NAME,
    context: SegmentSynthesisContext | None = None,
) -> SynthesisResult:
    request_settings = request_settings or RequestSettings()
    provider = get_provider(provider_name)
    last_error: RetryableApiError | None = None
    for attempt in range(1, request_settings.max_retries + 1):
        try:
            return provider.synthesize(
                text=text,
                settings=settings,
                api_key=api_key,
                timeout_seconds=request_settings.timeout_seconds,
                max_retries=request_settings.max_retries,
                context=context,
            )
        except RetryableApiError as exc:
            last_error = exc

        if attempt < request_settings.max_retries:
            if reporter is not None:
                reporter.detail(
                    "Retrying after API failure "
                    f"({attempt}/{request_settings.max_retries}): {last_error}"
                )
            time.sleep(attempt)
            continue

        if last_error is not None:
            raise last_error

    raise ApiError("TTS synthesis failed for an unknown reason.")


def write_audio_file(output_path: Path, audio_bytes: bytes) -> None:
    output_path.write_bytes(audio_bytes)


def write_binary_file(output_path: Path, content: bytes) -> None:
    output_path.write_bytes(content)


def write_timestamp_file(output_path: Path, payload: dict[str, Any]) -> None:
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_manifest(output_dir: Path, manifest: dict[str, Any]) -> None:
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_errors_file(output_dir: Path, segments: list[dict[str, Any]]) -> None:
    errors_path = output_dir / "errors.jsonl"
    failed_segments = [segment for segment in segments if segment["status"] == "failed"]

    with errors_path.open("w", encoding="utf-8") as handle:
        for segment in failed_segments:
            handle.write(json.dumps(segment, ensure_ascii=False) + "\n")


def ensure_ffmpeg_available() -> str:
    ffmpeg_path = find_ffmpeg_path()
    if ffmpeg_path:
        return ffmpeg_path
    raise DependencyError(
        "ffmpeg is not available in PATH. Install ffmpeg before using --merge."
    )


def find_ffmpeg_path() -> str | None:
    return shutil.which("ffmpeg")


def build_concat_list_file(output_dir: Path, audio_files: list[Path]) -> Path:
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".txt",
        prefix="ffmpeg-concat-",
        dir=output_dir,
        delete=False,
    ) as handle:
        for audio_file in audio_files:
            handle.write(f"file '{audio_file.resolve().as_posix()}'\n")
        return Path(handle.name)


def merge_audio_files(output_dir: Path, audio_files: list[Path]) -> Path:
    ffmpeg_path = ensure_ffmpeg_available()
    for audio_file in audio_files:
        if not audio_file.exists():
            raise TTSBatchError(f"Missing audio segment for merge: {audio_file.name}")

    concat_list_path = build_concat_list_file(output_dir, audio_files)
    merged_output_path = output_dir / "merged.mp3"
    try:
        completed = subprocess.run(
            [
                ffmpeg_path,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_list_path),
                "-c",
                "copy",
                str(merged_output_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        concat_list_path.unlink(missing_ok=True)

    if completed.returncode != 0:
        error_output = (completed.stderr or completed.stdout or "").strip()
        raise DependencyError(error_output or "ffmpeg merge failed.")

    if not merged_output_path.exists() or merged_output_path.stat().st_size <= 0:
        raise DependencyError("ffmpeg merge did not produce a valid merged.mp3.")

    return merged_output_path


def _build_cleanup_failure(
    backup_dir: Path,
    errors: list[str],
) -> CleanupResult:
    backup_path: Path | None = None
    if backup_dir.exists():
        try:
            has_contents = any(backup_dir.iterdir())
        except OSError:
            has_contents = True
        if has_contents:
            backup_path = backup_dir
            errors.append(f"Segment backups were preserved at {backup_dir}")
        else:
            backup_dir.rmdir()
    return CleanupResult(
        deleted_count=0,
        error="; ".join(errors),
        backup_dir=backup_path,
    )


def _restore_segment_backups(
    moved_files: list[tuple[Path, Path]],
) -> list[str]:
    restore_errors: list[str] = []
    for original_path, backup_path in reversed(moved_files):
        if not backup_path.exists():
            continue
        try:
            shutil.move(str(backup_path), str(original_path))
        except OSError as exc:
            restore_errors.append(
                f"Failed to restore {original_path.name} from cleanup backup: {exc}"
            )
    return restore_errors


def cleanup_merged_segments(output_dir: Path, audio_files: list[Path]) -> CleanupResult:
    if not audio_files:
        return CleanupResult(deleted_count=0)

    backup_dir = Path(
        tempfile.mkdtemp(prefix=".merge-cleanup-", dir=output_dir)
    )
    moved_files: list[tuple[Path, Path]] = []

    for audio_file in audio_files:
        if not audio_file.exists():
            errors = [f"Missing segment during cleanup: {audio_file.name}"]
            errors.extend(_restore_segment_backups(moved_files))
            return _build_cleanup_failure(backup_dir, errors)

        backup_path = backup_dir / audio_file.name
        try:
            shutil.move(str(audio_file), str(backup_path))
        except OSError as exc:
            errors = [f"Failed to preserve {audio_file.name} during cleanup: {exc}"]
            errors.extend(_restore_segment_backups(moved_files))
            return _build_cleanup_failure(backup_dir, errors)
        moved_files.append((audio_file, backup_path))

    try:
        shutil.rmtree(backup_dir)
    except OSError as exc:
        return CleanupResult(
            deleted_count=0,
            error=f"Failed to remove cleanup backup directory: {exc}",
            backup_dir=backup_dir,
        )

    return CleanupResult(deleted_count=len(audio_files))


def sanitize_label(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-")
    return sanitized or "job"


def build_output_dir(
    source: InputSource,
    output_root: Path,
    explicit_output_dir: str | None = None,
    job_name: str | None = None,
) -> Path:
    if explicit_output_dir:
        return Path(explicit_output_dir).expanduser()

    now = datetime.now().astimezone()
    date_part = now.strftime("%Y-%m-%d")
    timestamp = now.strftime("%Y%m%d-%H%M%S")
    label = sanitize_label(job_name or source.label or source.kind)
    return output_root.expanduser() / date_part / f"{timestamp}-{label}"


def uniquify_output_dir(path: Path) -> Path:
    candidate = path
    suffix = 2
    while candidate.exists():
        candidate = path.with_name(f"{path.name}-{suffix}")
        suffix += 1
    return candidate


def prepare_output_dir(
    output_dir: Path,
    *,
    explicit: bool,
    overwrite: bool,
) -> Path:
    resolved_output_dir = output_dir.expanduser()
    if not resolved_output_dir.exists():
        return resolved_output_dir

    if explicit:
        if not resolved_output_dir.is_dir():
            raise InputSourceError(
                f"Output path exists and is not a directory: {resolved_output_dir}"
            )

        try:
            has_existing_files = any(resolved_output_dir.iterdir())
        except OSError as exc:
            raise InputSourceError(
                f"Failed to inspect output directory: {resolved_output_dir}: {exc}"
            ) from exc

        if has_existing_files and not overwrite:
            raise InputSourceError(
                "Output directory already exists and is not empty: "
                f"{resolved_output_dir}. Use --force-output-dir to allow overwriting generated files in that directory."
            )
        return resolved_output_dir

    return uniquify_output_dir(resolved_output_dir)


def detect_output_dir_opener() -> str | None:
    if shutil.which("open"):
        return "open"
    if shutil.which("xdg-open"):
        return "xdg-open"
    return None


def open_output_dir(output_dir: Path) -> None:
    opener = detect_output_dir_opener()
    if opener is None:
        raise DependencyError("No supported folder opener was found on this system.")

    completed = subprocess.run(
        [opener, str(output_dir)],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        error_output = (completed.stderr or completed.stdout or "").strip()
        raise DependencyError(error_output or "Failed to open the output directory.")


def run_batch_job(
    source: InputSource,
    output_dir: Path,
    settings: ProviderTTSSettings,
    request_settings: RequestSettings | None,
    api_key: str,
    merge: bool,
    reporter: ProgressReporter | None = None,
    provider_name: str = DEFAULT_PROVIDER_NAME,
) -> BatchResult:
    reporter = reporter or ProgressReporter()
    request_settings = request_settings or RequestSettings()
    segments = parse_segments(source.text)
    if not segments:
        raise TTSBatchError("No non-empty segments found in the provided input.")

    output_dir.mkdir(parents=True, exist_ok=True)
    reporter.info(f"Loaded {len(segments)} segments from {source.kind}")
    reporter.info(f"Output directory: {output_dir.resolve()}")
    common_settings = serialize_common_settings(settings)
    provider_settings = serialize_provider_settings(settings)
    reporter.detail(
        "Common settings: "
        + json.dumps(common_settings, ensure_ascii=False, sort_keys=True)
    )
    reporter.detail(
        "Provider settings: "
        + json.dumps(provider_settings, ensure_ascii=False, sort_keys=True)
    )
    reporter.detail(
        "Request settings: "
        + json.dumps(asdict(request_settings), ensure_ascii=False, sort_keys=True)
    )

    index_width = max(4, len(str(len(segments))))
    results: list[dict[str, Any]] = []
    success_count = 0
    failure_count = 0
    generated_audio_files: list[Path] = []
    batch_exit_code = ExitCode.OK
    merge_exit_code = ExitCode.OK

    for index, text in enumerate(segments, start=1):
        filename = f"{index:0{index_width}d}.{settings.audio_format}"
        output_path = output_dir / filename
        reporter.info(f"[{index}/{len(segments)}] Synthesizing {filename} ...")
        previous_text = segments[index - 2] if index > 1 else None
        next_text = segments[index] if index < len(segments) else None

        try:
            audio_bytes = synthesize_segment(
                text,
                settings,
                api_key,
                request_settings=request_settings,
                reporter=reporter,
                provider_name=provider_name,
                context=SegmentSynthesisContext(
                    previous_text=previous_text,
                    next_text=next_text,
                ),
            )
        except TTSBatchError as exc:
            failure_count += 1
            if batch_exit_code == ExitCode.OK:
                batch_exit_code = exit_code_for_error(exc)
            results.append(
                {
                    "index": index,
                    "text": text,
                    "output_file": None,
                    "timestamp_file": None,
                    "timestamp_status": "skipped",
                    "status": "failed",
                    "error": str(exc),
                }
            )
            reporter.error(f"[{index}/{len(segments)}] Failed: {exc}")
            continue

        write_audio_file(output_path, audio_bytes.audio_bytes)
        generated_audio_files.append(output_path)
        success_count += 1
        timestamp_file: str | None = None
        timestamp_status = "skipped"
        if audio_bytes.timestamps is not None:
            timestamp_file = f"{output_path.stem}.timestamps.json"
            write_timestamp_file(
                output_dir / timestamp_file,
                {
                    "provider": provider_name,
                    "segment_index": index,
                    "text": text,
                    "audio_file": filename,
                    **audio_bytes.timestamps,
                },
            )
            timestamp_status = "success"
        results.append(
            {
                "index": index,
                "text": text,
                "output_file": filename,
                "timestamp_file": timestamp_file,
                "timestamp_status": timestamp_status,
                "status": "success",
                "error": None,
            }
        )
        reporter.info(f"[{index}/{len(segments)}] Wrote {filename}")

    merged_output_file: str | None = None
    merge_status = "skipped"
    merge_error: str | None = None
    cleanup_status = "skipped"
    cleanup_error: str | None = None
    cleanup_backup_dir: str | None = None
    deleted_segment_files = 0

    if failure_count == 0 and merge:
        reporter.info("All segments generated successfully. Starting merge to merged.mp3 ...")
        try:
            merged_output_path = merge_audio_files(output_dir, generated_audio_files)
        except TTSBatchError as exc:
            merge_status = "failed"
            merge_error = str(exc)
            merge_exit_code = exit_code_for_error(exc)
            reporter.error(f"Merge failed: {exc}")
        else:
            merge_status = "success"
            merged_output_file = merged_output_path.name
            reporter.info(f"Merge succeeded: {merged_output_path}")
            cleanup_result = cleanup_merged_segments(output_dir, generated_audio_files)
            deleted_segment_files = cleanup_result.deleted_count
            if cleanup_result.error:
                cleanup_status = "failed"
                cleanup_error = cleanup_result.error
                if cleanup_result.backup_dir is not None:
                    cleanup_backup_dir = str(cleanup_result.backup_dir)
                reporter.error(f"Cleanup failed after merge: {cleanup_error}")
            else:
                cleanup_status = "success"
                reporter.info(
                    f"Deleted {deleted_segment_files} segment files after successful merge."
                )
    elif failure_count == 0:
        reporter.info("Merge not requested. Keeping segment files.")
    else:
        reporter.info("Skipping merge because one or more segments failed.")

    manifest = {
        "input_source": source.kind,
        "input_file": source.input_file,
        "created_at": datetime.now().astimezone().isoformat(),
        "settings": {
            "provider": provider_name,
            "common_settings": common_settings,
            "provider_settings": provider_settings,
        },
        "summary": {
            "total_segments": len(segments),
            "succeeded": success_count,
            "failed": failure_count,
            "output_dir": str(output_dir.resolve()),
            "request_timeout_seconds": request_settings.timeout_seconds,
            "max_retries": request_settings.max_retries,
            "merged_output_file": merged_output_file,
            "merge_status": merge_status,
            "deleted_segment_files": deleted_segment_files,
            "cleanup_status": cleanup_status,
            "merge_error": merge_error,
            "cleanup_error": cleanup_error,
            "cleanup_backup_dir": cleanup_backup_dir,
        },
        "segments": results,
    }
    write_manifest(output_dir, manifest)
    write_errors_file(output_dir, results)

    reporter.info(
        f"Finished. Success: {success_count}, Failed: {failure_count}, Manifest: {output_dir / 'manifest.json'}"
    )

    exit_code = ExitCode.OK
    if failure_count > 0:
        exit_code = batch_exit_code or ExitCode.RUNTIME
    elif merge and merge_status != "success":
        exit_code = merge_exit_code or ExitCode.RUNTIME
    elif merge and cleanup_status not in ("success", "skipped"):
        exit_code = ExitCode.RUNTIME

    return BatchResult(
        exit_code=int(exit_code),
        output_dir=output_dir,
        manifest=manifest,
    )


def run_whole_input_job(
    source: InputSource,
    output_dir: Path,
    settings: ProviderTTSSettings,
    request_settings: RequestSettings | None,
    api_key: str,
    merge: bool,
    reporter: ProgressReporter | None = None,
    provider_name: str = DEFAULT_PROVIDER_NAME,
) -> BatchResult:
    del merge
    reporter = reporter or ProgressReporter()
    request_settings = request_settings or RequestSettings()
    normalized_text = normalize_whole_input(source.text)
    if not normalized_text:
        raise TTSBatchError("No non-empty text found in the provided input.")

    output_dir.mkdir(parents=True, exist_ok=True)
    reporter.info(
        f"Loaded whole-input job from {source.kind} ({len(normalized_text)} characters)"
    )
    reporter.info(f"Output directory: {output_dir.resolve()}")
    common_settings = serialize_common_settings(settings)
    provider_settings = serialize_provider_settings(settings)
    reporter.detail(
        "Common settings: "
        + json.dumps(common_settings, ensure_ascii=False, sort_keys=True)
    )
    reporter.detail(
        "Provider settings: "
        + json.dumps(provider_settings, ensure_ascii=False, sort_keys=True)
    )
    reporter.detail(
        "Request settings: "
        + json.dumps(asdict(request_settings), ensure_ascii=False, sort_keys=True)
    )

    provider = get_provider(provider_name)
    output_file: str | None = None
    titles_file: str | None = None
    extra_file: str | None = None
    subtitle_srt_file: str | None = None
    summary_overrides: dict[str, Any] = {}
    exit_code = ExitCode.OK

    try:
        result_payload = provider.synthesize(
            text=normalized_text,
            settings=settings,
            api_key=api_key,
            timeout_seconds=request_settings.timeout_seconds,
            max_retries=request_settings.max_retries,
        )
    except TTSBatchError as exc:
        exit_code = exit_code_for_error(exc)
        segment_entry = {
            "index": 1,
            "text": normalized_text,
            "output_file": None,
            "timestamp_file": None,
            "timestamp_status": "skipped",
            "status": "failed",
            "error": str(exc),
        }
        reporter.error(f"Whole-input synthesis failed: {exc}")
    else:
        output_file = result_payload.audio_filename or f"output.{settings.audio_format}"
        output_path = output_dir / output_file
        write_audio_file(output_path, result_payload.audio_bytes)
        for attachment in result_payload.attachments:
            attachment_path = output_dir / attachment.filename
            write_binary_file(attachment_path, attachment.content)
            if attachment.kind == "titles":
                titles_file = attachment.filename
            elif attachment.kind == "extra":
                extra_file = attachment.filename
            elif attachment.kind == "subtitle_srt":
                subtitle_srt_file = attachment.filename
        summary_overrides = dict(result_payload.metadata)
        segment_entry = {
            "index": 1,
            "text": normalized_text,
            "output_file": output_file,
            "timestamp_file": None,
            "timestamp_status": "skipped",
            "status": "success",
            "error": None,
        }
        reporter.info(f"Wrote {output_file}")

    manifest = {
        "input_source": source.kind,
        "input_file": source.input_file,
        "created_at": datetime.now().astimezone().isoformat(),
        "settings": {
            "provider": provider_name,
            "common_settings": common_settings,
            "provider_settings": provider_settings,
        },
        "summary": {
            "total_segments": 1,
            "succeeded": 1 if segment_entry["status"] == "success" else 0,
            "failed": 1 if segment_entry["status"] == "failed" else 0,
            "output_dir": str(output_dir.resolve()),
            "request_timeout_seconds": request_settings.timeout_seconds,
            "max_retries": request_settings.max_retries,
            "merged_output_file": None,
            "merge_status": "skipped",
            "deleted_segment_files": 0,
            "cleanup_status": "skipped",
            "merge_error": None,
            "cleanup_error": None,
            "cleanup_backup_dir": None,
            "audio_file": output_file,
            "titles_file": titles_file,
            "extra_file": extra_file,
            "subtitle_srt_file": subtitle_srt_file,
            **summary_overrides,
        },
        "segments": [segment_entry],
    }
    write_manifest(output_dir, manifest)
    write_errors_file(output_dir, [segment_entry])

    reporter.info(
        "Finished whole-input job. "
        f"Success: {manifest['summary']['succeeded']}, "
        f"Failed: {manifest['summary']['failed']}, "
        f"Manifest: {output_dir / 'manifest.json'}"
    )

    return BatchResult(
        exit_code=int(exit_code),
        output_dir=output_dir,
        manifest=manifest,
    )
