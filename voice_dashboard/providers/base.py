from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class CommonTTSSettings:
    model: str
    voice_id: str
    speed: float
    audio_format: str


@dataclass(frozen=True)
class SegmentSynthesisContext:
    previous_text: str | None = None
    next_text: str | None = None


@dataclass(frozen=True)
class SynthesisAttachment:
    kind: str
    filename: str
    content: bytes


@dataclass(frozen=True)
class SynthesisResult:
    audio_bytes: bytes
    timestamps: dict[str, Any] | None = None
    attachments: tuple[SynthesisAttachment, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


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
class MiniMaxAsyncTTSSettings:
    common: CommonTTSSettings
    language_boost: str
    pitch: int
    sample_rate: int
    subtitles: bool
    poll_interval_seconds: int
    task_timeout_seconds: int

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
class ElevenLabsVoiceSettings:
    speed: float | None = None
    stability: float | None = None
    similarity_boost: float | None = None
    style: float | None = None
    use_speaker_boost: bool | None = None


@dataclass(frozen=True)
class ElevenLabsTTSSettings:
    common: CommonTTSSettings
    output_format: str
    timestamps: bool | None = None
    language_code: str | None = None
    seed: int | None = None
    enable_logging: bool | None = None
    continuity_mode: str | None = None
    voice_settings: ElevenLabsVoiceSettings = field(
        default_factory=ElevenLabsVoiceSettings
    )

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


ProviderTTSSettings = (
    MiniMaxTTSSettings | MiniMaxAsyncTTSSettings | ElevenLabsTTSSettings
)


def serialize_common_settings(settings: ProviderTTSSettings) -> dict[str, object]:
    return asdict(settings.common)


def serialize_provider_settings(settings: ProviderTTSSettings) -> dict[str, object]:
    if isinstance(settings, MiniMaxTTSSettings):
        return {
            "language_boost": settings.language_boost,
            "pitch": settings.pitch,
            "sample_rate": settings.sample_rate,
        }
    if isinstance(settings, MiniMaxAsyncTTSSettings):
        return {
            "language_boost": settings.language_boost,
            "pitch": settings.pitch,
            "sample_rate": settings.sample_rate,
            "subtitles": settings.subtitles,
            "poll_interval_seconds": settings.poll_interval_seconds,
            "task_timeout_seconds": settings.task_timeout_seconds,
        }
    provider_settings: dict[str, object] = {
        "output_format": settings.output_format,
    }
    if settings.timestamps is not None:
        provider_settings["timestamps"] = settings.timestamps
    if settings.language_code is not None:
        provider_settings["language_code"] = settings.language_code
    if settings.seed is not None:
        provider_settings["seed"] = settings.seed
    if settings.enable_logging is not None:
        provider_settings["enable_logging"] = settings.enable_logging
    if settings.continuity_mode is not None:
        provider_settings["continuity_mode"] = settings.continuity_mode

    voice_settings = {
        key: value
        for key, value in asdict(settings.voice_settings).items()
        if value is not None
    }
    if voice_settings:
        provider_settings["voice_settings"] = voice_settings
    return provider_settings


class TTSProvider(Protocol):
    """Provider interface for one-shot TTS synthesis."""

    name: str
    api_key_env_var: str
    execution_mode: str

    def read_api_key(self) -> str:
        ...

    def synthesize(
        self,
        *,
        text: str,
        settings: ProviderTTSSettings,
        api_key: str,
        timeout_seconds: int,
        max_retries: int = 1,
        context: SegmentSynthesisContext | None = None,
    ) -> SynthesisResult:
        ...
