import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from voice_dashboard.errors import InputSourceError


@dataclass(frozen=True)
class InputSource:
    kind: str
    label: str
    text: str
    input_file: str | None = None


CLIPBOARD_READERS: list[tuple[str, list[str], str]] = [
    ("pbpaste", ["pbpaste"], "macOS clipboard"),
    ("wl-paste", ["wl-paste", "-n"], "Wayland clipboard"),
    ("xclip", ["xclip", "-selection", "clipboard", "-out"], "X11 clipboard"),
    ("xsel", ["xsel", "--clipboard", "--output"], "X11 clipboard"),
]


def read_file_source(file_path: str) -> InputSource:
    path = Path(file_path).expanduser()
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise InputSourceError(f"Input file not found: {path}") from exc
    except UnicodeDecodeError as exc:
        raise InputSourceError(f"Input file is not valid UTF-8: {path}") from exc
    return InputSource(kind="file", label=path.stem, text=text, input_file=str(path))


def read_stdin_source() -> InputSource:
    text = sys.stdin.read()
    if not text.strip():
        raise InputSourceError("No text received from stdin.")
    return InputSource(kind="stdin", label="stdin", text=text)


def detect_clipboard_reader() -> tuple[str, list[str], str] | None:
    for reader in CLIPBOARD_READERS:
        _, command, _ = reader
        if shutil.which(command[0]):
            return reader
    return None


def read_clipboard_source() -> InputSource:
    reader = detect_clipboard_reader()
    if reader is None:
        raise InputSourceError(
            "Clipboard input is not available. Install pbpaste, wl-paste, xclip, or xsel."
        )

    _, command, description = reader
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        error_text = (completed.stderr or completed.stdout or "").strip()
        raise InputSourceError(
            error_text or f"Failed to read {description.lower()}."
        )

    if not completed.stdout.strip():
        raise InputSourceError("Clipboard is empty.")

    return InputSource(kind="clipboard", label="clipboard", text=completed.stdout)
