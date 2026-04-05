from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Protocol


@dataclass(frozen=True)
class CommonTTSSettings:
    model: str
    voice_id: str
    speed: float
    audio_format: str


@dataclass(frozen=True)
class MiniMaxTTSSettings:
    common: CommonTTSSettings
    language_boost: str
    pitch: int
    sample_rate: int

    @property
    def model(self) -> str:
        return self.common.model

    @property
    def voice_id(self) -> str:
        return self.common.voice_id

    @property
    def speed(self) -> float:
        return self.common.speed

    @property
    def audio_format(self) -> str:
        return self.common.audio_format


@dataclass(frozen=True)
class ElevenLabsTTSSettings:
    common: CommonTTSSettings

    @property
    def model(self) -> str:
        return self.common.model

    @property
    def voice_id(self) -> str:
        return self.common.voice_id

    @property
    def speed(self) -> float:
        return self.common.speed

    @property
    def audio_format(self) -> str:
        return self.common.audio_format


ProviderTTSSettings = MiniMaxTTSSettings | ElevenLabsTTSSettings


def serialize_common_settings(settings: ProviderTTSSettings) -> dict[str, object]:
    return asdict(settings.common)


def serialize_provider_settings(settings: ProviderTTSSettings) -> dict[str, object]:
    if isinstance(settings, MiniMaxTTSSettings):
        return {
            "language_boost": settings.language_boost,
            "pitch": settings.pitch,
            "sample_rate": settings.sample_rate,
        }
    return {}


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
        settings: ProviderTTSSettings,
        api_key: str,
        timeout_seconds: int,
    ) -> bytes:
        ...
