from __future__ import annotations

import os

import requests

from voice_dashboard.defaults import DEFAULT_MODEL
from voice_dashboard.errors import ApiError, AuthenticationError, RetryableApiError


ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1/text-to-speech"
ELEVENLABS_DEFAULT_MODEL = "eleven_multilingual_v2"
ELEVENLABS_OUTPUT_FORMAT = "mp3_44100_128"


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


class ElevenLabsProvider:
    name = "elevenlabs"
    api_key_env_var = "ELEVENLABS_API_KEY"

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
        settings: object,
        api_key: str,
        timeout_seconds: int,
    ) -> bytes:
        model_id = settings.model
        if not model_id or model_id == DEFAULT_MODEL:
            model_id = ELEVENLABS_DEFAULT_MODEL

        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {
                "speed": settings.speed,
            },
        }
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }

        try:
            response = requests.post(
                f"{ELEVENLABS_API_URL}/{settings.voice_id}",
                headers=headers,
                params={"output_format": ELEVENLABS_OUTPUT_FORMAT},
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

        audio_bytes = response.content
        if not audio_bytes:
            raise ApiError("API response did not include audio data.")

        return audio_bytes


ELEVENLABS_PROVIDER = ElevenLabsProvider()
