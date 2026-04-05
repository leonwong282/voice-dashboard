from __future__ import annotations

from voice_dashboard.providers.base import TTSProvider
from voice_dashboard.providers.elevenlabs import ELEVENLABS_PROVIDER
from voice_dashboard.providers.minimax import MINIMAX_PROVIDER
from voice_dashboard.providers.minimax_async import MINIMAX_ASYNC_PROVIDER


MINIMAX_PROVIDER_ALIAS = "minimax"
MINIMAX_SYNC_PROVIDER_NAME = "minimax-sync"
MINIMAX_ASYNC_PROVIDER_NAME = "minimax-async"

DEFAULT_PROVIDER_NAME = MINIMAX_PROVIDER_ALIAS
SUPPORTED_PROVIDER_NAMES = (
    MINIMAX_PROVIDER_ALIAS,
    MINIMAX_SYNC_PROVIDER_NAME,
    MINIMAX_ASYNC_PROVIDER_NAME,
    ELEVENLABS_PROVIDER.name,
)

_PROVIDERS: dict[str, TTSProvider] = {
    MINIMAX_PROVIDER_ALIAS: MINIMAX_PROVIDER,
    MINIMAX_SYNC_PROVIDER_NAME: MINIMAX_PROVIDER,
    MINIMAX_ASYNC_PROVIDER_NAME: MINIMAX_ASYNC_PROVIDER,
    ELEVENLABS_PROVIDER.name: ELEVENLABS_PROVIDER,
}


def is_minimax_provider_name(name: str) -> bool:
    return name in (
        MINIMAX_PROVIDER_ALIAS,
        MINIMAX_SYNC_PROVIDER_NAME,
        MINIMAX_ASYNC_PROVIDER_NAME,
    )


def get_supported_api_key_env_vars() -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(provider.api_key_env_var for provider in _PROVIDERS.values())
    )


def get_provider(name: str = DEFAULT_PROVIDER_NAME) -> TTSProvider:
    try:
        return _PROVIDERS[name]
    except KeyError as exc:
        raise LookupError(f"Unknown TTS provider: {name}") from exc
