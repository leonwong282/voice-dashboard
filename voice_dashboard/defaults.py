from pathlib import Path


API_URL = "https://api.minimaxi.com/v1/t2a_v2"
DEFAULT_MODEL = "speech-2.8-hd"
DEFAULT_LANGUAGE_BOOST = "Chinese,Yue"
DEFAULT_VOICE_ID = "clone_voice_can"
DEFAULT_SPEED = 1.2
DEFAULT_PITCH = 0
DEFAULT_SAMPLE_RATE = 32000
DEFAULT_FORMAT = "mp3"
DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_MAX_RETRIES = 3
DEFAULT_CONFIG_PATH = Path.home() / ".voice-dashboard.json"
DEFAULT_OUTPUT_ROOT = Path.home() / "Documents" / "tts-output"
