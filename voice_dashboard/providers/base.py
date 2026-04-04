from __future__ import annotations

from typing import Any, Protocol


class TTSProvider(Protocol):
    """Provider interface for one-shot TTS synthesis."""

    name: str
    api_key_env_var: str

    def read_api_key(self) -> str:
        ...

    def synthesize(
        self,
        *,
        text: str,
        settings: Any,
        api_key: str,
        timeout_seconds: int,
    ) -> bytes:
        ...
