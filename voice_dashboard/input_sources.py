import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


class InputSourceError(RuntimeError):
    """Raised when the requested input source cannot be read."""


@dataclass(frozen=True)
class InputSource:
    kind: str
    label: str
    text: str
    input_file: str | None = None


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


def read_clipboard_source() -> InputSource:
    completed = subprocess.run(
        ["pbpaste"],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        error_text = (completed.stderr or completed.stdout or "").strip()
        raise InputSourceError(error_text or "Failed to read macOS clipboard.")

    if not completed.stdout.strip():
        raise InputSourceError("Clipboard is empty.")

    return InputSource(kind="clipboard", label="clipboard", text=completed.stdout)
