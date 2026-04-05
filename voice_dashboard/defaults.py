import os
from pathlib import Path


MINIMAX_SYNC_API_URL = "https://api.minimaxi.com/v1/t2a_v2"
MINIMAX_ASYNC_CREATE_URL = "https://api.minimaxi.com/v1/t2a_async_v2"
MINIMAX_ASYNC_QUERY_URL = "https://api.minimaxi.com/v1/query/t2a_async_query_v2"
MINIMAX_FILE_RETRIEVE_URL = "https://api.minimaxi.com/v1/files/retrieve"
MINIMAX_FILE_RETRIEVE_CONTENT_URL = "https://api.minimaxi.com/v1/files/retrieve_content"
APP_DIR_NAME = "voice-dashboard"
MINIMAX_DEFAULT_MODEL = "speech-2.8-hd"
DEFAULT_LANGUAGE_BOOST = "Chinese,Yue"
MINIMAX_DEFAULT_VOICE_ID = "clone_voice_can"
MINIMAX_DEFAULT_SPEED = 1.2
DEFAULT_PITCH = 0
DEFAULT_SAMPLE_RATE = 32000
MINIMAX_ASYNC_DEFAULT_SUBTITLES = True
MINIMAX_ASYNC_DEFAULT_POLL_INTERVAL_SECONDS = 2
MINIMAX_ASYNC_DEFAULT_TASK_TIMEOUT_SECONDS = 900
ELEVENLABS_DEFAULT_MODEL = "eleven_multilingual_v2"
ELEVENLABS_DEFAULT_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"
ELEVENLABS_DEFAULT_SPEED = 1.0
ELEVENLABS_DEFAULT_OUTPUT_FORMAT = "mp3_44100_128"
DEFAULT_FORMAT = "mp3"
DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_MAX_RETRIES = 3

# Backward-compatible aliases for internal imports.
API_URL = MINIMAX_SYNC_API_URL
DEFAULT_MODEL = MINIMAX_DEFAULT_MODEL
DEFAULT_VOICE_ID = MINIMAX_DEFAULT_VOICE_ID
DEFAULT_SPEED = MINIMAX_DEFAULT_SPEED


def _expand_path(value: str) -> Path:
    return Path(value).expanduser()


def legacy_config_path() -> Path:
    return Path.home() / ".voice-dashboard.json"


def default_config_path() -> Path:
    xdg_config_home = os.getenv("XDG_CONFIG_HOME", "").strip()
    if xdg_config_home:
        return _expand_path(xdg_config_home) / APP_DIR_NAME / "config.json"
    return Path.home() / ".config" / APP_DIR_NAME / "config.json"


def default_output_root() -> Path:
    documents_dir = Path.home() / "Documents"
    if documents_dir.exists():
        return documents_dir / APP_DIR_NAME

    xdg_data_home = os.getenv("XDG_DATA_HOME", "").strip()
    if xdg_data_home:
        return _expand_path(xdg_data_home) / APP_DIR_NAME / "output"

    return Path.home() / ".local" / "share" / APP_DIR_NAME / "output"
