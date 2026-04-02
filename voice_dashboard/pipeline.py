import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from voice_dashboard.defaults import (
    API_URL,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT_SECONDS,
)
from voice_dashboard.input_sources import InputSource


class TTSBatchError(RuntimeError):
    """Raised when the TTS batch job cannot continue."""


class RetryableTTSBatchError(TTSBatchError):
    """Raised for failures that are safe to retry."""


@dataclass(frozen=True)
class TTSSettings:
    model: str
    language_boost: str
    voice_id: str
    speed: float
    pitch: int
    sample_rate: int
    audio_format: str


@dataclass(frozen=True)
class BatchResult:
    exit_code: int
    output_dir: Path
    manifest: dict[str, Any]


def parse_segments(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []

    segments = re.split(r"\n\s*\n+", normalized)
    return [segment.strip() for segment in segments if segment.strip()]


def get_api_key() -> str:
    api_key = os.getenv("MINIMAX_API_KEY", "").strip()
    if api_key:
        return api_key
    raise TTSBatchError(
        "MINIMAX_API_KEY is not set. Rotate the previously hard-coded key and export the new one before running."
    )


def extract_api_error_message(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        body = response.text.strip()
        return body or "Unknown API error"

    if not isinstance(payload, dict):
        return "Unexpected API error response"

    base_resp = payload.get("base_resp")
    if isinstance(base_resp, dict):
        status_msg = base_resp.get("status_msg")
        if status_msg:
            return str(status_msg)

    for key in ("message", "msg", "error"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, dict):
            nested = value.get("message")
            if isinstance(nested, str) and nested.strip():
                return nested.strip()

    return "Unknown API error"


def decode_audio_hex(audio_hex: str) -> bytes:
    try:
        return bytes.fromhex(audio_hex)
    except ValueError as exc:
        raise TTSBatchError("Response audio payload was not valid hex data.") from exc


def synthesize_segment(
    text: str,
    settings: TTSSettings,
    api_key: str,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> bytes:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.model,
        "text": text,
        "language_boost": settings.language_boost,
        "voice_setting": {
            "voice_id": settings.voice_id,
            "speed": settings.speed,
            "pitch": settings.pitch,
        },
        "audio_setting": {
            "format": settings.audio_format,
            "sample_rate": settings.sample_rate,
        },
    }

    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        retryable = False
        try:
            response = requests.post(
                API_URL,
                headers=headers,
                json=payload,
                timeout=timeout,
            )
        except requests.RequestException as exc:
            last_error = RetryableTTSBatchError(f"Network error: {exc}")
            retryable = True
        else:
            if response.status_code >= 500:
                last_error = RetryableTTSBatchError(
                    f"HTTP {response.status_code}: {extract_api_error_message(response)}"
                )
                retryable = True
            elif response.status_code >= 400:
                raise TTSBatchError(
                    f"HTTP {response.status_code}: {extract_api_error_message(response)}"
                )
            else:
                try:
                    data = response.json()
                except ValueError as exc:
                    raise TTSBatchError("API returned invalid JSON.") from exc

                base_resp = data.get("base_resp")
                if isinstance(base_resp, dict) and base_resp.get("status_code") not in (
                    None,
                    0,
                ):
                    status_msg = base_resp.get("status_msg", "Unknown API error")
                    raise TTSBatchError(str(status_msg))

                audio_hex = data.get("data", {}).get("audio")
                if not isinstance(audio_hex, str) or not audio_hex:
                    raise TTSBatchError("API response did not include audio data.")

                return decode_audio_hex(audio_hex)

        if retryable and attempt < max_retries:
            time.sleep(attempt)
            continue

        if last_error is not None:
            raise last_error

    raise TTSBatchError("TTS synthesis failed for an unknown reason.")


def write_audio_file(output_path: Path, audio_bytes: bytes) -> None:
    output_path.write_bytes(audio_bytes)


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
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        return ffmpeg_path
    raise TTSBatchError("ffmpeg is not available in PATH.")


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
        raise TTSBatchError(error_output or "ffmpeg merge failed.")

    if not merged_output_path.exists() or merged_output_path.stat().st_size <= 0:
        raise TTSBatchError("ffmpeg merge did not produce a valid merged.mp3.")

    return merged_output_path


def delete_segment_files(audio_files: list[Path]) -> tuple[int, list[str]]:
    deleted_count = 0
    cleanup_errors: list[str] = []
    for audio_file in audio_files:
        try:
            audio_file.unlink()
            deleted_count += 1
        except FileNotFoundError:
            cleanup_errors.append(f"Missing segment during cleanup: {audio_file.name}")
        except OSError as exc:
            cleanup_errors.append(f"Failed to delete {audio_file.name}: {exc}")
    return deleted_count, cleanup_errors


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


def open_output_dir(output_dir: Path) -> None:
    launcher = None
    if shutil.which("open"):
        launcher = ["open", str(output_dir)]
    elif shutil.which("xdg-open"):
        launcher = ["xdg-open", str(output_dir)]

    if launcher is None:
        raise TTSBatchError("No supported folder opener was found on this system.")

    completed = subprocess.run(
        launcher,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        error_output = (completed.stderr or completed.stdout or "").strip()
        raise TTSBatchError(error_output or "Failed to open the output directory.")


def run_batch_job(
    source: InputSource,
    output_dir: Path,
    settings: TTSSettings,
    api_key: str,
    merge: bool,
) -> BatchResult:
    segments = parse_segments(source.text)
    if not segments:
        raise TTSBatchError("No non-empty segments found in the provided input.")

    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Loaded {len(segments)} segments from {source.kind}")
    print(f"Output directory: {output_dir.resolve()}")

    index_width = max(4, len(str(len(segments))))
    results: list[dict[str, Any]] = []
    success_count = 0
    failure_count = 0
    generated_audio_files: list[Path] = []

    for index, text in enumerate(segments, start=1):
        filename = f"{index:0{index_width}d}.{settings.audio_format}"
        output_path = output_dir / filename
        print(f"[{index}/{len(segments)}] Synthesizing {filename} ...")

        try:
            audio_bytes = synthesize_segment(text, settings, api_key)
        except TTSBatchError as exc:
            failure_count += 1
            results.append(
                {
                    "index": index,
                    "text": text,
                    "output_file": None,
                    "status": "failed",
                    "error": str(exc),
                }
            )
            print(f"[{index}/{len(segments)}] Failed: {exc}", file=sys.stderr)
            continue

        write_audio_file(output_path, audio_bytes)
        generated_audio_files.append(output_path)
        success_count += 1
        results.append(
            {
                "index": index,
                "text": text,
                "output_file": filename,
                "status": "success",
                "error": None,
            }
        )
        print(f"[{index}/{len(segments)}] Wrote {filename}")

    merged_output_file: str | None = None
    merge_status = "skipped"
    merge_error: str | None = None
    cleanup_status = "skipped"
    deleted_segment_files = 0

    if failure_count == 0 and merge:
        print("All segments generated successfully. Starting merge to merged.mp3 ...")
        try:
            merged_output_path = merge_audio_files(output_dir, generated_audio_files)
        except TTSBatchError as exc:
            merge_status = "failed"
            merge_error = str(exc)
            print(f"Merge failed: {exc}", file=sys.stderr)
        else:
            merge_status = "success"
            merged_output_file = merged_output_path.name
            print(f"Merge succeeded: {merged_output_path}")
            deleted_segment_files, cleanup_errors = delete_segment_files(
                generated_audio_files
            )
            if cleanup_errors:
                cleanup_status = "failed"
                merge_error = "; ".join(cleanup_errors)
                print(f"Cleanup failed after merge: {merge_error}", file=sys.stderr)
            else:
                cleanup_status = "success"
                print(
                    f"Deleted {deleted_segment_files} segment files after successful merge."
                )
    elif failure_count == 0:
        print("Merge not requested. Keeping segment files.")
    else:
        print("Skipping merge because one or more segments failed.")

    manifest = {
        "input_source": source.kind,
        "input_file": source.input_file,
        "created_at": datetime.now().astimezone().isoformat(),
        "settings": asdict(settings),
        "summary": {
            "total_segments": len(segments),
            "succeeded": success_count,
            "failed": failure_count,
            "output_dir": str(output_dir.resolve()),
            "merged_output_file": merged_output_file,
            "merge_status": merge_status,
            "deleted_segment_files": deleted_segment_files,
            "cleanup_status": cleanup_status,
            "merge_error": merge_error,
        },
        "segments": results,
    }
    write_manifest(output_dir, manifest)
    write_errors_file(output_dir, results)

    print(
        f"Finished. Success: {success_count}, Failed: {failure_count}, Manifest: {output_dir / 'manifest.json'}"
    )

    exit_code = 0
    if failure_count > 0:
        exit_code = 1
    elif merge and merge_status != "success":
        exit_code = 1
    elif merge and cleanup_status not in ("success", "skipped"):
        exit_code = 1

    return BatchResult(
        exit_code=exit_code,
        output_dir=output_dir,
        manifest=manifest,
    )
