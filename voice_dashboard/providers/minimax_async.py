from __future__ import annotations

import io
import os
import time
import zipfile
from pathlib import Path
from typing import Any

import requests

from voice_dashboard.defaults import (
    MINIMAX_ASYNC_CREATE_URL,
    MINIMAX_ASYNC_QUERY_URL,
    MINIMAX_FILE_RETRIEVE_CONTENT_URL,
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
_SUBTITLE_EXTENSIONS = {".ass", ".lrc", ".srt", ".ssa", ".vtt"}


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


def _extract_bundle(
    bundle_bytes: bytes,
    settings: MiniMaxAsyncTTSSettings,
) -> tuple[bytes, tuple[SynthesisAttachment, ...]]:
    bundle_stream = io.BytesIO(bundle_bytes)
    if not zipfile.is_zipfile(bundle_stream):
        if settings.subtitles:
            raise ApiError(
                "MiniMax async returned a single file instead of a bundle with subtitles."
            )
        return bundle_bytes, ()

    with zipfile.ZipFile(bundle_stream) as archive:
        members = [
            (info.filename, archive.read(info.filename))
            for info in archive.infolist()
            if not info.is_dir()
        ]

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
    _, audio_bytes = audio_member

    attachments: list[SynthesisAttachment] = []

    subtitle_member = _select_archive_member(members, suffixes=_SUBTITLE_EXTENSIONS)
    if settings.subtitles:
        if subtitle_member is None:
            raise ApiError(
                "MiniMax async task completed without a subtitle file."
            )
        subtitle_filename, subtitle_bytes = subtitle_member
        subtitle_suffix = Path(subtitle_filename).suffix.lower() or ".srt"
        attachments.append(
            SynthesisAttachment(
                kind="subtitle",
                filename=f"output{subtitle_suffix}",
                content=subtitle_bytes,
            )
        )

    extra_member = _select_archive_member(
        members,
        suffixes={".json"},
    )
    if extra_member is not None:
        _, extra_bytes = extra_member
        attachments.append(
            SynthesisAttachment(
                kind="extra",
                filename="output.extra.json",
                content=extra_bytes,
            )
        )

    return audio_bytes, tuple(attachments)


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
        file_id: int | str,
        api_key: str,
        timeout_seconds: int,
        max_retries: int,
    ) -> bytes:
        response = _request_with_retries(
            "GET",
            MINIMAX_FILE_RETRIEVE_CONTENT_URL,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            params={"file_id": file_id},
        )
        if not response.content:
            raise ApiError("MiniMax file download response did not include file content.")
        return response.content

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
        downloaded_bytes = self._download_file(
            file_id=file_id,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )
        audio_bytes, attachments = _extract_bundle(downloaded_bytes, settings)

        metadata = {
            "task_id": task_id,
            "task_token": task_token,
            "file_id": file_id,
            "remote_status": remote_status,
            "remote_filename": file_payload.get("filename"),
            "remote_download_url": file_payload.get("download_url"),
            "usage_characters": usage_characters,
            "last_status": last_status_payload.get("status"),
        }
        return SynthesisResult(
            audio_bytes=audio_bytes,
            attachments=attachments,
            metadata=metadata,
        )


MINIMAX_ASYNC_PROVIDER = MiniMaxAsyncProvider()
