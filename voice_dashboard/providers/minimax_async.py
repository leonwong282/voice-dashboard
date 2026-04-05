from __future__ import annotations

import os

from voice_dashboard.errors import ApiError, AuthenticationError
from voice_dashboard.providers.base import (
    MiniMaxTTSSettings,
    SegmentSynthesisContext,
    SynthesisResult,
)


class MiniMaxAsyncProvider:
    name = "minimax-async"
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
        context: SegmentSynthesisContext | None = None,
    ) -> SynthesisResult:
        raise ApiError(
            "MiniMax async provider is not implemented yet. "
            "Current phase only adds provider identity and routing scaffolding."
        )


MINIMAX_ASYNC_PROVIDER = MiniMaxAsyncProvider()
