from __future__ import annotations

import os

from voice_dashboard.errors import ApiError, AuthenticationError


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
        raise ApiError(
            "Provider 'elevenlabs' is configured but TTS synthesis is not implemented yet."
        )


ELEVENLABS_PROVIDER = ElevenLabsProvider()
