from __future__ import annotations

import os

import requests

from voice_dashboard.defaults import API_URL
from voice_dashboard.errors import ApiError, AuthenticationError, RetryableApiError
from voice_dashboard.providers.base import MiniMaxTTSSettings


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
        raise ApiError("API response audio payload was not valid hex data.") from exc


class MiniMaxProvider:
    name = "minimax"
    api_key_env_var = "MINIMAX_API_KEY"

    def read_api_key(self) -> str:
        api_key = os.getenv(self.api_key_env_var, "").strip()
        if api_key:
            return api_key
        raise AuthenticationError(
            "MINIMAX_API_KEY is not set. Export it before running ttsrun, or use --doctor to inspect your environment."
        )

    def synthesize(
        self,
        *,
        text: str,
        settings: MiniMaxTTSSettings,
        api_key: str,
        timeout_seconds: int,
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

        try:
            response = requests.post(
                API_URL,
                headers=headers,
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
                    f"{message}. Check MINIMAX_API_KEY and account permissions."
                )
            raise ApiError(message)

        try:
            data = response.json()
        except ValueError as exc:
            raise ApiError("API returned invalid JSON.") from exc

        base_resp = data.get("base_resp")
        if isinstance(base_resp, dict) and base_resp.get("status_code") not in (
            None,
            0,
        ):
            status_msg = base_resp.get("status_msg", "Unknown API error")
            raise ApiError(str(status_msg))

        audio_hex = data.get("data", {}).get("audio")
        if not isinstance(audio_hex, str) or not audio_hex:
            raise ApiError("API response did not include audio data.")

        return decode_audio_hex(audio_hex)


MINIMAX_PROVIDER = MiniMaxProvider()
