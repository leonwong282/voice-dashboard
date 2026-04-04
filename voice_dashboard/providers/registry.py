from __future__ import annotations

from voice_dashboard.providers.base import TTSProvider
from voice_dashboard.providers.minimax import MINIMAX_PROVIDER


DEFAULT_PROVIDER_NAME = MINIMAX_PROVIDER.name

_PROVIDERS: dict[str, TTSProvider] = {
    MINIMAX_PROVIDER.name: MINIMAX_PROVIDER,
}


def get_provider(name: str = DEFAULT_PROVIDER_NAME) -> TTSProvider:
    try:
        return _PROVIDERS[name]
    except KeyError as exc:
        raise LookupError(f"Unknown TTS provider: {name}") from exc
