from __future__ import annotations

import io
import json
import os
import tarfile
import time
from pathlib import Path
from typing import Any

import requests

from voice_dashboard.defaults import (
    MINIMAX_ASYNC_CREATE_URL,
    MINIMAX_ASYNC_QUERY_URL,
    MINIMAX_FILE_RETRIEVE_URL,
)
from voice_dashboard.errors import ApiError, AuthenticationError, RetryableApiError
from voice_dashboard.providers.base import (
    MiniMaxAsyncTTSSettings,
    SegmentSynthesisContext,
    SynthesisAttachment,
    SynthesisResult,
)
from voice_dashboard.providers.minimax import extract_api_error_message


_AUDIO_EXTENSIONS = {
    ".aac",
    ".flac",
    ".m4a",
    ".mp3",
    ".ogg",
    ".opus",
    ".pcm",
    ".wav",
}
_TITLES_EXTENSION = ".titles"
_EXTRA_EXTENSION = ".extra"


def _normalize_status(raw_status: object) -> str:
    if not isinstance(raw_status, str) or not raw_status.strip():
        raise ApiError("MiniMax async task status was missing from the API response.")
    return raw_status.strip().lower()


def _parse_json_response(response: requests.Response, error_message: str) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise ApiError(error_message) from exc

    if not isinstance(payload, dict):
        raise ApiError(error_message)
    return payload


def _raise_if_base_resp_failed(payload: dict[str, Any]) -> None:
    base_resp = payload.get("base_resp")
    if not isinstance(base_resp, dict):
        return
    if base_resp.get("status_code") not in (None, 0):
        status_msg = base_resp.get("status_msg", "Unknown API error")
        raise ApiError(str(status_msg))


def _is_retryable_http_status(status_code: int) -> bool:
    return status_code >= 500


def _request_with_retries(
    method: str,
    url: str,
    *,
    api_key: str,
    timeout_seconds: int,
    max_retries: int,
    params: dict[str, object] | None = None,
    json_payload: dict[str, object] | None = None,
) -> requests.Response:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    request_fn = requests.post if method == "POST" else requests.get
    last_error: RetryableApiError | None = None

    for attempt in range(1, max_retries + 1):
        try:
            response = request_fn(
                url,
                headers=headers,
                params=params,
                json=json_payload,
                timeout=timeout_seconds,
            )
        except requests.RequestException as exc:
            last_error = RetryableApiError(f"Network error: {exc}")
        else:
            if _is_retryable_http_status(response.status_code):
                last_error = RetryableApiError(
                    f"HTTP {response.status_code}: {extract_api_error_message(response)}"
                )
            else:
                if response.status_code >= 400:
                    message = (
                        f"HTTP {response.status_code}: "
                        f"{extract_api_error_message(response)}"
                    )
                    if response.status_code in (401, 403):
                        raise AuthenticationError(
                            f"{message}. Check MINIMAX_API_KEY and account permissions."
                        )
                    raise ApiError(message)
                return response

        if attempt < max_retries:
            time.sleep(min(attempt, 3))

    if last_error is not None:
        raise last_error
    raise ApiError("MiniMax async request failed for an unknown reason.")


def _download_from_url(
    download_url: str,
    *,
    timeout_seconds: int,
    max_retries: int,
) -> bytes:
    last_error: RetryableApiError | None = None

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(download_url, timeout=timeout_seconds)
        except requests.RequestException as exc:
            last_error = RetryableApiError(f"Network error: {exc}")
        else:
            if response.status_code >= 500:
                last_error = RetryableApiError(
                    f"HTTP {response.status_code}: download_url request failed."
                )
            elif response.status_code >= 400:
                body = response.text.strip() or "download_url request failed."
                raise ApiError(f"HTTP {response.status_code}: {body}")
            elif response.content:
                return response.content
            else:
                raise ApiError("MiniMax async download URL returned empty content.")

        if attempt < max_retries:
            time.sleep(min(attempt, 3))

    if last_error is not None:
        raise last_error
    raise ApiError("MiniMax async download failed for an unknown reason.")


def _select_archive_member(
    members: list[tuple[str, bytes]],
    *,
    suffixes: set[str],
    preferred_suffix: str | None = None,
    exclude_suffixes: set[str] | None = None,
) -> tuple[str, bytes] | None:
    exclude_suffixes = exclude_suffixes or set()
    if preferred_suffix is not None:
        for filename, content in members:
            suffix = Path(filename).suffix.lower()
            if suffix == preferred_suffix and suffix not in exclude_suffixes:
                return filename, content
    for filename, content in members:
        suffix = Path(filename).suffix.lower()
        if suffix in suffixes and suffix not in exclude_suffixes:
            return filename, content
    return None


def _ms_to_srt_time(milliseconds: float | int) -> str:
    total_ms = max(float(milliseconds), 0.0)
    total_seconds = int(total_ms // 1000)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    millis = int(round(total_ms - (total_seconds * 1000)))
    if millis >= 1000:
        seconds += 1
        millis -= 1000
    if seconds >= 60:
        minutes += 1
        seconds -= 60
    if minutes >= 60:
        hours += 1
        minutes -= 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def _titles_to_srt_bytes(titles_bytes: bytes) -> bytes:
    try:
        payload = json.loads(titles_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ApiError("MiniMax .titles file was not valid UTF-8 JSON.") from exc

    items: Any = payload
    if isinstance(items, dict):
        for key in ("subtitles", "sentences", "data", "items"):
            value = items.get(key)
            if isinstance(value, list):
                items = value
                break

    if not isinstance(items, list):
        raise ApiError("MiniMax .titles file did not contain a subtitle list.")

    lines: list[str] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise ApiError("MiniMax .titles item was not a JSON object.")
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        try:
            start = _ms_to_srt_time(float(item["time_begin"]))
            end = _ms_to_srt_time(float(item["time_end"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise ApiError(
                "MiniMax .titles item was missing valid time_begin/time_end fields."
            ) from exc
        lines.append(f"{index}\n{start} --> {end}\n{text}\n")

    return "\n".join(lines).encode("utf-8")


def _extract_bundle(
    bundle_bytes: bytes,
    settings: MiniMaxAsyncTTSSettings,
) -> tuple[str, bytes, tuple[SynthesisAttachment, ...]]:
    bundle_stream = io.BytesIO(bundle_bytes)
    try:
        with tarfile.open(fileobj=bundle_stream, mode="r:*") as archive:
            members = []
            for member in archive.getmembers():
                if not member.isfile():
                    continue
                content = archive.extractfile(member)
                if content is None:
                    continue
                members.append((Path(member.name).name, content.read()))
    except tarfile.TarError as exc:
        raise ApiError("MiniMax async bundle was not a valid tar archive.") from exc

    if not members:
        raise ApiError("MiniMax async bundle did not contain any files.")

    preferred_audio_suffix = f".{settings.audio_format.lstrip('.').lower()}"
    audio_member = _select_archive_member(
        members,
        suffixes=_AUDIO_EXTENSIONS,
        preferred_suffix=preferred_audio_suffix,
    )
    if audio_member is None:
        raise ApiError("MiniMax async bundle did not contain an audio file.")
    audio_filename, audio_bytes = audio_member

    attachments: list[SynthesisAttachment] = []

    titles_member = _select_archive_member(members, suffixes={_TITLES_EXTENSION})
    if titles_member is not None:
        titles_filename, titles_bytes = titles_member
        attachments.append(
            SynthesisAttachment(
                kind="titles",
                filename=titles_filename,
                content=titles_bytes,
            )
        )
        if settings.subtitles:
            attachments.append(
                SynthesisAttachment(
                    kind="subtitle_srt",
                    filename="subtitle.srt",
                    content=_titles_to_srt_bytes(titles_bytes),
                )
            )
    elif settings.subtitles:
        raise ApiError(
            "MiniMax async task completed without a .titles subtitle file."
        )

    extra_member = _select_archive_member(members, suffixes={_EXTRA_EXTENSION})
    if extra_member is not None:
        extra_filename, extra_bytes = extra_member
        attachments.append(
            SynthesisAttachment(
                kind="extra",
                filename=extra_filename,
                content=extra_bytes,
            )
        )

    return audio_filename, audio_bytes, tuple(attachments)


class MiniMaxAsyncProvider:
    name = "minimax-async"
    api_key_env_var = "MINIMAX_API_KEY"
    execution_mode = "whole_input"

    def read_api_key(self) -> str:
        api_key = os.getenv(self.api_key_env_var, "").strip()
        if api_key:
            return api_key
        raise AuthenticationError(
            "MINIMAX_API_KEY is not set. Export it before running ttsrun, or use --doctor to inspect your environment."
        )

    def _create_task(
        self,
        *,
        text: str,
        settings: MiniMaxAsyncTTSSettings,
        api_key: str,
        timeout_seconds: int,
        max_retries: int,
    ) -> dict[str, Any]:
        payload: dict[str, object] = {
            "model": settings.model,
            "text": text,
            "language_boost": settings.language_boost,
            "voice_setting": {
                "voice_id": settings.voice_id,
                "speed": settings.speed,
                "pitch": settings.pitch,
            },
            "audio_setting": {
                "audio_sample_rate": settings.sample_rate,
                "format": settings.audio_format,
            },
        }
        response = _request_with_retries(
            "POST",
            MINIMAX_ASYNC_CREATE_URL,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            json_payload=payload,
        )
        data = _parse_json_response(response, "MiniMax async create returned invalid JSON.")
        _raise_if_base_resp_failed(data)
        return data

    def _query_task(
        self,
        *,
        task_id: int | str,
        api_key: str,
        timeout_seconds: int,
        max_retries: int,
    ) -> dict[str, Any]:
        response = _request_with_retries(
            "GET",
            MINIMAX_ASYNC_QUERY_URL,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            params={"task_id": task_id},
        )
        data = _parse_json_response(response, "MiniMax async query returned invalid JSON.")
        _raise_if_base_resp_failed(data)
        return data

    def _retrieve_file(
        self,
        *,
        file_id: int | str,
        api_key: str,
        timeout_seconds: int,
        max_retries: int,
    ) -> dict[str, Any]:
        response = _request_with_retries(
            "GET",
            MINIMAX_FILE_RETRIEVE_URL,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            params={"file_id": file_id},
        )
        data = _parse_json_response(
            response, "MiniMax file metadata endpoint returned invalid JSON."
        )
        _raise_if_base_resp_failed(data)
        file_payload = data.get("file")
        if not isinstance(file_payload, dict):
            raise ApiError("MiniMax file metadata response did not include file details.")
        return file_payload

    def _download_file(
        self,
        *,
        download_url: str,
        timeout_seconds: int,
        max_retries: int,
    ) -> bytes:
        return _download_from_url(
            download_url,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )

    def synthesize(
        self,
        *,
        text: str,
        settings: MiniMaxAsyncTTSSettings,
        api_key: str,
        timeout_seconds: int,
        max_retries: int = 1,
        context: SegmentSynthesisContext | None = None,
    ) -> SynthesisResult:
        del context
        task_payload = self._create_task(
            text=text,
            settings=settings,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )

        task_id = task_payload.get("task_id")
        if task_id in (None, ""):
            raise ApiError("MiniMax async create response did not include task_id.")
        file_id = task_payload.get("file_id")
        task_token = task_payload.get("task_token")
        usage_characters = task_payload.get("usage_characters")

        deadline = time.monotonic() + settings.task_timeout_seconds
        remote_status = "processing"
        last_status_payload = task_payload

        while True:
            if time.monotonic() > deadline:
                raise ApiError(
                    "MiniMax async task did not finish within "
                    f"{settings.task_timeout_seconds} seconds."
                )

            status_payload = self._query_task(
                task_id=task_id,
                api_key=api_key,
                timeout_seconds=timeout_seconds,
                max_retries=max_retries,
            )
            last_status_payload = status_payload
            remote_status = _normalize_status(status_payload.get("status"))
            if remote_status == "success":
                file_id = status_payload.get("file_id", file_id)
                break
            if remote_status == "failed":
                raise ApiError(f"MiniMax async task {task_id} failed.")
            if remote_status == "expired":
                raise ApiError(f"MiniMax async task {task_id} expired before download.")

            time.sleep(settings.poll_interval_seconds)

        if file_id in (None, ""):
            raise ApiError("MiniMax async task completed without a downloadable file_id.")

        file_payload = self._retrieve_file(
            file_id=file_id,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )
        download_url = file_payload.get("download_url")
        if not isinstance(download_url, str) or not download_url.strip():
            raise ApiError("MiniMax file metadata response did not include download_url.")
        downloaded_bytes = self._download_file(
            download_url=download_url.strip(),
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )
        audio_filename, audio_bytes, attachments = _extract_bundle(
            downloaded_bytes, settings
        )

        metadata = {
            "task_id": task_id,
            "task_token": task_token,
            "file_id": file_id,
            "remote_status": remote_status,
            "remote_filename": file_payload.get("filename"),
            "remote_download_url": download_url.strip(),
            "usage_characters": usage_characters,
            "last_status": last_status_payload.get("status"),
        }
        return SynthesisResult(
            audio_bytes=audio_bytes,
            audio_filename=audio_filename,
            attachments=attachments,
            metadata=metadata,
        )


MINIMAX_ASYNC_PROVIDER = MiniMaxAsyncProvider()
