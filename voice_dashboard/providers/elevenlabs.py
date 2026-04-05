from __future__ import annotations

import base64
import os

import requests

from voice_dashboard.defaults import (
    DEFAULT_MODEL,
    ELEVENLABS_DEFAULT_MODEL,
)
from voice_dashboard.errors import ApiError, AuthenticationError, RetryableApiError
from voice_dashboard.providers.base import (
    ElevenLabsTTSSettings,
    SegmentSynthesisContext,
    SynthesisResult,
)


ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1/text-to-speech"


def extract_api_error_message(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        body = response.text.strip()
        return body or "Unknown API error"

    if isinstance(payload, str) and payload.strip():
        return payload.strip()
    if not isinstance(payload, dict):
        return "Unexpected API error response"

    for key in ("detail", "message", "msg", "error"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, dict):
            nested = value.get("message") or value.get("detail")
            if isinstance(nested, str) and nested.strip():
                return nested.strip()

    detail = payload.get("detail")
    if isinstance(detail, list) and detail:
        first = detail[0]
        if isinstance(first, str) and first.strip():
            return first.strip()
        if isinstance(first, dict):
            message = first.get("message") or first.get("detail")
            if isinstance(message, str) and message.strip():
                return message.strip()

    return "Unknown API error"


def build_voice_settings_payload(
    settings: ElevenLabsTTSSettings,
) -> dict[str, object]:
    voice_settings: dict[str, object] = {}

    speed = settings.voice_settings.speed
    if speed is None:
        speed = settings.speed
    voice_settings["speed"] = speed

    if settings.voice_settings.stability is not None:
        voice_settings["stability"] = settings.voice_settings.stability
    if settings.voice_settings.similarity_boost is not None:
        voice_settings["similarity_boost"] = settings.voice_settings.similarity_boost
    if settings.voice_settings.style is not None:
        voice_settings["style"] = settings.voice_settings.style
    if settings.voice_settings.use_speaker_boost is not None:
        voice_settings["use_speaker_boost"] = settings.voice_settings.use_speaker_boost

    return voice_settings


def decode_audio_base64(audio_base64: str) -> bytes:
    try:
        return base64.b64decode(audio_base64, validate=True)
    except (ValueError, TypeError) as exc:
        raise ApiError("API response audio payload was not valid base64 data.") from exc


def build_timestamp_payload(data: dict[str, object]) -> dict[str, object]:
    return {
        "alignment": data.get("alignment"),
        "normalized_alignment": data.get("normalized_alignment"),
    }


class ElevenLabsProvider:
    name = "elevenlabs"
    api_key_env_var = "ELEVENLABS_API_KEY"
    execution_mode = "segment"

    def read_api_key(self) -> str:
        api_key = os.getenv(self.api_key_env_var, "").strip()
        if api_key:
            return api_key
        raise AuthenticationError(
            "ELEVENLABS_API_KEY is not set. Export it before running ttsrun, or use --doctor to inspect your environment."
        )

    def synthesize(
        self,
        *,
        text: str,
        settings: ElevenLabsTTSSettings,
        api_key: str,
        timeout_seconds: int,
        max_retries: int = 1,
        context: SegmentSynthesisContext | None = None,
    ) -> SynthesisResult:
        model_id = settings.model
        if not model_id or model_id == DEFAULT_MODEL:
            model_id = ELEVENLABS_DEFAULT_MODEL

        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": build_voice_settings_payload(settings),
        }
        if settings.language_code is not None:
            payload["language_code"] = settings.language_code
        if settings.seed is not None:
            payload["seed"] = settings.seed
        if settings.continuity_mode == "adjacent_text" and context is not None:
            if context.previous_text is not None:
                payload["previous_text"] = context.previous_text
            if context.next_text is not None:
                payload["next_text"] = context.next_text

        params: dict[str, object] = {"output_format": settings.output_format}
        if settings.enable_logging is not None:
            params["enable_logging"] = str(settings.enable_logging).lower()

        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json" if settings.timestamps else "audio/mpeg",
        }
        endpoint = f"{ELEVENLABS_API_URL}/{settings.voice_id}"
        if settings.timestamps:
            endpoint = f"{endpoint}/with-timestamps"

        try:
            response = requests.post(
                endpoint,
                headers=headers,
                params=params,
                json=payload,
                timeout=timeout_seconds,
            )
        except requests.RequestException as exc:
            raise RetryableApiError(f"Network error: {exc}") from exc

        if response.status_code >= 500:
            raise RetryableApiError(
                f"HTTP {response.status_code}: {extract_api_error_message(response)}"
            )
        if response.status_code >= 400:
            message = f"HTTP {response.status_code}: {extract_api_error_message(response)}"
            if response.status_code in (401, 403):
                raise AuthenticationError(
                    f"{message}. Check ELEVENLABS_API_KEY and account permissions."
                )
            raise ApiError(message)

        if settings.timestamps:
            try:
                data = response.json()
            except ValueError as exc:
                raise ApiError("API returned invalid JSON.") from exc

            if not isinstance(data, dict):
                raise ApiError("API returned an unexpected timestamp payload.")

            audio_base64 = data.get("audio_base64")
            if not isinstance(audio_base64, str) or not audio_base64:
                raise ApiError("API response did not include audio_base64 data.")

            return SynthesisResult(
                audio_bytes=decode_audio_base64(audio_base64),
                timestamps=build_timestamp_payload(data),
            )

        audio_bytes = response.content
        if not audio_bytes:
            raise ApiError("API response did not include audio data.")

        return SynthesisResult(audio_bytes=audio_bytes)


ELEVENLABS_PROVIDER = ElevenLabsProvider()
