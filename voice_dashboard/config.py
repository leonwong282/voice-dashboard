import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from voice_dashboard.defaults import (
    DEFAULT_FORMAT,
    DEFAULT_LANGUAGE_BOOST,
    DEFAULT_MAX_RETRIES,
    DEFAULT_PITCH,
    DEFAULT_SAMPLE_RATE,
    DEFAULT_TIMEOUT_SECONDS,
    ELEVENLABS_DEFAULT_MODEL,
    ELEVENLABS_DEFAULT_OUTPUT_FORMAT,
    ELEVENLABS_DEFAULT_SPEED,
    ELEVENLABS_DEFAULT_VOICE_ID,
    MINIMAX_DEFAULT_MODEL,
    MINIMAX_DEFAULT_SPEED,
    MINIMAX_DEFAULT_VOICE_ID,
    default_config_path,
    default_output_root,
    legacy_config_path,
)
from voice_dashboard.errors import ConfigError
from voice_dashboard.providers.registry import (
    DEFAULT_PROVIDER_NAME,
    SUPPORTED_PROVIDER_NAMES,
    is_minimax_provider_name,
)


@dataclass(frozen=True)
class GlobalConfig:
    output_root: Path = field(default_factory=default_output_root)
    audio_format: str = DEFAULT_FORMAT
    request_timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    max_retries: int = DEFAULT_MAX_RETRIES
    open_after_finish: bool = False


@dataclass(frozen=True)
class MiniMaxConfig:
    voice_id: str = MINIMAX_DEFAULT_VOICE_ID
    speed: float = MINIMAX_DEFAULT_SPEED
    model: str = MINIMAX_DEFAULT_MODEL
    pitch: int = DEFAULT_PITCH
    language_boost: str = DEFAULT_LANGUAGE_BOOST
    sample_rate: int = DEFAULT_SAMPLE_RATE


@dataclass(frozen=True)
class ElevenLabsConfig:
    voice_id: str = ELEVENLABS_DEFAULT_VOICE_ID
    speed: float = ELEVENLABS_DEFAULT_SPEED
    model: str = ELEVENLABS_DEFAULT_MODEL
    output_format: str = ELEVENLABS_DEFAULT_OUTPUT_FORMAT
    timestamps: bool | None = None
    language_code: str | None = None
    seed: int | None = None
    enable_logging: bool | None = None
    continuity_mode: str | None = None
    voice_settings: "ElevenLabsVoiceSettings" = field(
        default_factory=lambda: ElevenLabsVoiceSettings()
    )


@dataclass(frozen=True)
class ElevenLabsVoiceSettings:
    speed: float | None = None
    stability: float | None = None
    similarity_boost: float | None = None
    style: float | None = None
    use_speaker_boost: bool | None = None


@dataclass(frozen=True)
class AppConfig:
    default_provider: str = DEFAULT_PROVIDER_NAME
    global_options: GlobalConfig = field(default_factory=GlobalConfig)
    minimax: MiniMaxConfig = field(default_factory=MiniMaxConfig)
    elevenlabs: ElevenLabsConfig = field(default_factory=ElevenLabsConfig)
    config_path: Path = field(default_factory=default_config_path)

    @property
    def provider(self) -> str:
        return self.default_provider

    @property
    def output_root(self) -> Path:
        return self.global_options.output_root

    @property
    def audio_format(self) -> str:
        return self.global_options.audio_format

    @property
    def request_timeout_seconds(self) -> int:
        return self.global_options.request_timeout_seconds

    @property
    def max_retries(self) -> int:
        return self.global_options.max_retries

    @property
    def open_after_finish(self) -> bool:
        return self.global_options.open_after_finish

    def provider_config(self, provider_name: str) -> MiniMaxConfig | ElevenLabsConfig:
        if is_minimax_provider_name(provider_name):
            return self.minimax
        if provider_name == "elevenlabs":
            return self.elevenlabs
        supported = ", ".join(SUPPORTED_PROVIDER_NAMES)
        raise ConfigError(f"Unsupported provider '{provider_name}'. Supported: {supported}.")


def _coerce_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"Config field '{field_name}' must be a non-empty string.")
    return value.strip()


def _coerce_float(value: Any, field_name: str) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    raise ConfigError(f"Config field '{field_name}' must be a number.")


def _coerce_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError(f"Config field '{field_name}' must be an integer.")
    return value


def _coerce_positive_int(value: Any, field_name: str) -> int:
    integer = _coerce_int(value, field_name)
    if integer < 1:
        raise ConfigError(f"Config field '{field_name}' must be greater than zero.")
    return integer


def _coerce_bool(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigError(f"Config field '{field_name}' must be true or false.")
    return value


def _coerce_optional_str(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    return _coerce_str(value, field_name)


def _coerce_optional_float(value: Any, field_name: str) -> float | None:
    if value is None:
        return None
    return _coerce_float(value, field_name)


def _coerce_optional_int(value: Any, field_name: str) -> int | None:
    if value is None:
        return None
    return _coerce_int(value, field_name)


def _coerce_optional_bool(value: Any, field_name: str) -> bool | None:
    if value is None:
        return None
    return _coerce_bool(value, field_name)


def _coerce_optional_elevenlabs_continuity_mode(
    value: Any,
    field_name: str,
) -> str | None:
    mode = _coerce_optional_str(value, field_name)
    if mode is None:
        return None
    supported_modes = {"adjacent_text"}
    if mode not in supported_modes:
        supported = ", ".join(sorted(supported_modes))
        raise ConfigError(
            f"Config field '{field_name}' must be one of: {supported}."
        )
    return mode


def _coerce_provider(value: Any, field_name: str = "default_provider") -> str:
    provider = _coerce_str(value, field_name)
    if provider not in SUPPORTED_PROVIDER_NAMES:
        supported = ", ".join(SUPPORTED_PROVIDER_NAMES)
        raise ConfigError(
            f"Config field '{field_name}' must be one of: {supported}."
        )
    return provider


def _expect_object(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError(f"Config key '{field_name}' must be a JSON object.")
    return value


def _check_for_legacy_schema(payload: dict[str, Any]) -> None:
    legacy_keys = []
    if "provider" in payload:
        legacy_keys.append("provider")
    if "defaults" in payload:
        legacy_keys.append("defaults")
    if legacy_keys:
        keys = ", ".join(legacy_keys)
        raise ConfigError(
            f"Legacy config schema is not supported ({keys}). "
            "Use 'default_provider', 'global', and 'providers'."
        )


def example_config() -> dict[str, Any]:
    return serialize_config(AppConfig())


def serialize_config(
    config: AppConfig,
    include_metadata: bool = False,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "default_provider": config.default_provider,
        "global": {
            "output_root": str(config.output_root),
            "format": config.audio_format,
            "request_timeout_seconds": config.request_timeout_seconds,
            "max_retries": config.max_retries,
            "open_after_finish": config.open_after_finish,
        },
        "providers": {
            "minimax": asdict(config.minimax),
            "elevenlabs": asdict(config.elevenlabs),
        },
    }
    if include_metadata:
        preferred_config_path = default_config_path()
        legacy_path = legacy_config_path()
        payload["config_path"] = str(config.config_path)
        payload["config_exists"] = config.config_path.exists()
        payload["preferred_config_path"] = str(preferred_config_path)
        payload["legacy_config_path"] = str(legacy_path)
        payload["using_legacy_config_path"] = (
            config.config_path == legacy_path and config.config_path != preferred_config_path
        )
    return payload


def resolve_config_path(config_path: str | None) -> Path:
    if config_path:
        return Path(config_path).expanduser()

    preferred_path = default_config_path()
    legacy_path = legacy_config_path()
    if legacy_path.exists() and not preferred_path.exists():
        return legacy_path
    return preferred_path


def write_example_config(
    config_path: str | None = None,
    overwrite: bool = False,
) -> Path:
    resolved_path = resolve_config_path(config_path)
    if resolved_path.exists() and not overwrite:
        raise ConfigError(
            f"Config file already exists: {resolved_path}. Use --force to overwrite it."
        )

    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_path.write_text(
        json.dumps(example_config(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return resolved_path


def load_config(config_path: str | None) -> AppConfig:
    resolved_path = resolve_config_path(config_path)
    if not resolved_path.exists():
        return AppConfig(config_path=resolved_path)

    try:
        payload = json.loads(resolved_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Config file is not valid JSON: {resolved_path}") from exc

    if not isinstance(payload, dict):
        raise ConfigError(f"Config file must contain a JSON object: {resolved_path}")

    _check_for_legacy_schema(payload)

    global_values = payload.get("global", {})
    providers_values = payload.get("providers", {})
    global_values = _expect_object(global_values, "global")
    providers_values = _expect_object(providers_values, "providers")

    supported_provider_sections = {"minimax", "elevenlabs"}
    unknown_provider_keys = set(providers_values) - supported_provider_sections
    if unknown_provider_keys:
        unknown = ", ".join(sorted(unknown_provider_keys))
        supported = ", ".join(sorted(supported_provider_sections))
        raise ConfigError(
            f"Unsupported provider section(s): {unknown}. Supported: {supported}."
        )

    config = AppConfig(config_path=resolved_path)
    app_updates: dict[str, Any] = {}
    global_updates: dict[str, Any] = {}
    minimax_updates: dict[str, Any] = {}
    elevenlabs_updates: dict[str, Any] = {}

    if "default_provider" in payload:
        app_updates["default_provider"] = _coerce_provider(payload["default_provider"])

    if "output_root" in global_values:
        global_updates["output_root"] = Path(
            _coerce_str(global_values["output_root"], "global.output_root")
        ).expanduser()
    if "format" in global_values:
        global_updates["audio_format"] = _coerce_str(
            global_values["format"], "global.format"
        )
    if "request_timeout_seconds" in global_values:
        global_updates["request_timeout_seconds"] = _coerce_positive_int(
            global_values["request_timeout_seconds"],
            "global.request_timeout_seconds",
        )
    if "max_retries" in global_values:
        global_updates["max_retries"] = _coerce_positive_int(
            global_values["max_retries"], "global.max_retries"
        )
    if "open_after_finish" in global_values:
        global_updates["open_after_finish"] = _coerce_bool(
            global_values["open_after_finish"], "global.open_after_finish"
        )

    minimax_values = providers_values.get("minimax", {})
    minimax_values = _expect_object(minimax_values, "providers.minimax")
    if "voice_id" in minimax_values:
        minimax_updates["voice_id"] = _coerce_str(
            minimax_values["voice_id"], "providers.minimax.voice_id"
        )
    if "speed" in minimax_values:
        minimax_updates["speed"] = _coerce_float(
            minimax_values["speed"], "providers.minimax.speed"
        )
    if "model" in minimax_values:
        minimax_updates["model"] = _coerce_str(
            minimax_values["model"], "providers.minimax.model"
        )
    if "pitch" in minimax_values:
        minimax_updates["pitch"] = _coerce_int(
            minimax_values["pitch"], "providers.minimax.pitch"
        )
    if "language_boost" in minimax_values:
        minimax_updates["language_boost"] = _coerce_str(
            minimax_values["language_boost"], "providers.minimax.language_boost"
        )
    if "sample_rate" in minimax_values:
        minimax_updates["sample_rate"] = _coerce_int(
            minimax_values["sample_rate"], "providers.minimax.sample_rate"
        )

    elevenlabs_values = providers_values.get("elevenlabs", {})
    elevenlabs_values = _expect_object(elevenlabs_values, "providers.elevenlabs")
    if "voice_id" in elevenlabs_values:
        elevenlabs_updates["voice_id"] = _coerce_str(
            elevenlabs_values["voice_id"], "providers.elevenlabs.voice_id"
        )
    if "speed" in elevenlabs_values:
        elevenlabs_updates["speed"] = _coerce_float(
            elevenlabs_values["speed"], "providers.elevenlabs.speed"
        )
    if "model" in elevenlabs_values:
        elevenlabs_updates["model"] = _coerce_str(
            elevenlabs_values["model"], "providers.elevenlabs.model"
        )
    if "output_format" in elevenlabs_values:
        elevenlabs_updates["output_format"] = _coerce_str(
            elevenlabs_values["output_format"], "providers.elevenlabs.output_format"
        )
    if "timestamps" in elevenlabs_values:
        elevenlabs_updates["timestamps"] = _coerce_optional_bool(
            elevenlabs_values["timestamps"],
            "providers.elevenlabs.timestamps",
        )
    if "language_code" in elevenlabs_values:
        elevenlabs_updates["language_code"] = _coerce_optional_str(
            elevenlabs_values["language_code"],
            "providers.elevenlabs.language_code",
        )
    if "seed" in elevenlabs_values:
        elevenlabs_updates["seed"] = _coerce_optional_int(
            elevenlabs_values["seed"], "providers.elevenlabs.seed"
        )
    if "enable_logging" in elevenlabs_values:
        elevenlabs_updates["enable_logging"] = _coerce_optional_bool(
            elevenlabs_values["enable_logging"],
            "providers.elevenlabs.enable_logging",
        )
    if "continuity_mode" in elevenlabs_values:
        elevenlabs_updates["continuity_mode"] = _coerce_optional_elevenlabs_continuity_mode(
            elevenlabs_values["continuity_mode"],
            "providers.elevenlabs.continuity_mode",
        )

    elevenlabs_voice_settings_values = elevenlabs_values.get("voice_settings", {})
    elevenlabs_voice_settings_values = _expect_object(
        elevenlabs_voice_settings_values, "providers.elevenlabs.voice_settings"
    )
    elevenlabs_voice_settings_updates: dict[str, Any] = {}
    if "speed" in elevenlabs_voice_settings_values:
        elevenlabs_voice_settings_updates["speed"] = _coerce_optional_float(
            elevenlabs_voice_settings_values["speed"],
            "providers.elevenlabs.voice_settings.speed",
        )
    if "stability" in elevenlabs_voice_settings_values:
        elevenlabs_voice_settings_updates["stability"] = _coerce_optional_float(
            elevenlabs_voice_settings_values["stability"],
            "providers.elevenlabs.voice_settings.stability",
        )
    if "similarity_boost" in elevenlabs_voice_settings_values:
        elevenlabs_voice_settings_updates["similarity_boost"] = _coerce_optional_float(
            elevenlabs_voice_settings_values["similarity_boost"],
            "providers.elevenlabs.voice_settings.similarity_boost",
        )
    if "style" in elevenlabs_voice_settings_values:
        elevenlabs_voice_settings_updates["style"] = _coerce_optional_float(
            elevenlabs_voice_settings_values["style"],
            "providers.elevenlabs.voice_settings.style",
        )
    if "use_speaker_boost" in elevenlabs_voice_settings_values:
        elevenlabs_voice_settings_updates["use_speaker_boost"] = _coerce_optional_bool(
            elevenlabs_voice_settings_values["use_speaker_boost"],
            "providers.elevenlabs.voice_settings.use_speaker_boost",
        )

    merged = asdict(config)
    merged.update(app_updates)
    merged["global_options"] = GlobalConfig(
        **{**asdict(config.global_options), **global_updates}
    )
    merged["minimax"] = MiniMaxConfig(**{**asdict(config.minimax), **minimax_updates})
    merged["elevenlabs"] = ElevenLabsConfig(
        **{
            **asdict(config.elevenlabs),
            **elevenlabs_updates,
            "voice_settings": ElevenLabsVoiceSettings(
                **{
                    **asdict(config.elevenlabs.voice_settings),
                    **elevenlabs_voice_settings_updates,
                }
            ),
        }
    )
    return AppConfig(**merged)
