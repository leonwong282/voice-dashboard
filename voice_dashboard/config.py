import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from voice_dashboard.defaults import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_FORMAT,
    DEFAULT_LANGUAGE_BOOST,
    DEFAULT_MODEL,
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_PITCH,
    DEFAULT_SAMPLE_RATE,
    DEFAULT_SPEED,
    DEFAULT_VOICE_ID,
)
from voice_dashboard.errors import ConfigError


@dataclass(frozen=True)
class AppConfig:
    voice_id: str = DEFAULT_VOICE_ID
    speed: float = DEFAULT_SPEED
    pitch: int = DEFAULT_PITCH
    language_boost: str = DEFAULT_LANGUAGE_BOOST
    model: str = DEFAULT_MODEL
    sample_rate: int = DEFAULT_SAMPLE_RATE
    audio_format: str = DEFAULT_FORMAT
    output_root: Path = DEFAULT_OUTPUT_ROOT
    open_after_finish: bool = False
    config_path: Path = DEFAULT_CONFIG_PATH


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


def _coerce_bool(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigError(f"Config field '{field_name}' must be true or false.")
    return value


def example_config() -> dict[str, Any]:
    config = AppConfig()
    data = asdict(config)
    data["output_root"] = str(config.output_root)
    data["format"] = data.pop("audio_format")
    data.pop("config_path", None)
    return {"defaults": data}


def resolve_config_path(config_path: str | None) -> Path:
    return Path(config_path).expanduser() if config_path else DEFAULT_CONFIG_PATH


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

    values = payload.get("defaults", payload)
    if not isinstance(values, dict):
        raise ConfigError("Config key 'defaults' must be a JSON object.")

    config = AppConfig(config_path=resolved_path)
    updates: dict[str, Any] = {}

    if "voice_id" in values:
        updates["voice_id"] = _coerce_str(values["voice_id"], "voice_id")
    if "speed" in values:
        updates["speed"] = _coerce_float(values["speed"], "speed")
    if "pitch" in values:
        updates["pitch"] = _coerce_int(values["pitch"], "pitch")
    if "language_boost" in values:
        updates["language_boost"] = _coerce_str(
            values["language_boost"], "language_boost"
        )
    if "model" in values:
        updates["model"] = _coerce_str(values["model"], "model")
    if "sample_rate" in values:
        updates["sample_rate"] = _coerce_int(values["sample_rate"], "sample_rate")
    if "format" in values:
        updates["audio_format"] = _coerce_str(values["format"], "format")
    elif "audio_format" in values:
        updates["audio_format"] = _coerce_str(
            values["audio_format"], "audio_format"
        )
    if "output_root" in values:
        updates["output_root"] = Path(
            _coerce_str(values["output_root"], "output_root")
        ).expanduser()
    if "open_after_finish" in values:
        updates["open_after_finish"] = _coerce_bool(
            values["open_after_finish"], "open_after_finish"
        )

    return AppConfig(**{**asdict(config), **updates})
