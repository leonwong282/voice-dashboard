import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from voice_dashboard import __version__
from voice_dashboard.errors import ExitCode


REPO_ROOT = Path(__file__).resolve().parents[1]


def venv_bin_dir(venv_path: Path) -> Path:
    candidate = venv_path / "bin"
    if candidate.exists():
        return candidate
    return venv_path / "Scripts"


def run_checked(command: list[str], *, cwd: Path | None = None) -> None:
    completed = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"Command failed with exit code {completed.returncode}: {' '.join(command)}\n"
            f"{completed.stdout}"
        )


class InstalledCLITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._temp_dir = tempfile.TemporaryDirectory()
        cls.source_root = Path(cls._temp_dir.name) / "source"
        cls.source_root.mkdir()
        shutil.copy(REPO_ROOT / "pyproject.toml", cls.source_root / "pyproject.toml")
        shutil.copy(REPO_ROOT / "README.md", cls.source_root / "README.md")
        shutil.copy(REPO_ROOT / "LICENSE", cls.source_root / "LICENSE")
        shutil.copytree(REPO_ROOT / "voice_dashboard", cls.source_root / "voice_dashboard")

        cls.venv_path = Path(cls._temp_dir.name) / "installed-cli-venv"
        run_checked(
            [sys.executable, "-m", "venv", str(cls.venv_path)],
            cwd=cls.source_root,
        )

        cls.bin_dir = venv_bin_dir(cls.venv_path)
        cls.python_executable = cls.bin_dir / "python"
        cls.ttsrun_executable = cls.bin_dir / "ttsrun"

        run_checked(
            [
                str(cls.python_executable),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                str(cls.source_root),
            ],
            cwd=cls.source_root,
        )

        if not cls.ttsrun_executable.exists():
            raise AssertionError(f"Installed CLI not found: {cls.ttsrun_executable}")

    @classmethod
    def tearDownClass(cls):
        cls._temp_dir.cleanup()

    def run_ttsrun(
        self,
        *args: str,
        env_overrides: dict[str, str | None] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env.pop("MINIMAX_API_KEY", None)

        if env_overrides:
            for key, value in env_overrides.items():
                if value is None:
                    env.pop(key, None)
                else:
                    env[key] = value

        return subprocess.run(
            [str(self.ttsrun_executable), *args],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
        )

    def test_installed_help_command_succeeds(self):
        result = self.run_ttsrun("--help")

        self.assertEqual(result.returncode, ExitCode.OK, result.stderr)
        self.assertIn("Batch synthesize text into MP3 files", result.stdout)
        self.assertIn("ttsrun doctor", result.stdout)

    def test_installed_version_command_reports_package_version(self):
        result = self.run_ttsrun("--version")

        self.assertEqual(result.returncode, ExitCode.OK, result.stderr)
        self.assertEqual(result.stdout.strip(), __version__)

    def test_installed_doctor_reports_missing_api_key(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            home_dir = Path(temp_dir) / "home"
            home_dir.mkdir()

            result = self.run_ttsrun("doctor", env_overrides={"HOME": str(home_dir)})

        self.assertEqual(result.returncode, ExitCode.AUTH)
        self.assertIn("voice-dashboard", result.stdout)
        self.assertIn("MINIMAX_API_KEY", result.stdout)
        self.assertEqual(result.stderr, "")

    def test_installed_doctor_supports_provider_override(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            home_dir = Path(temp_dir) / "home"
            home_dir.mkdir()

            result = self.run_ttsrun(
                "doctor",
                "--provider",
                "elevenlabs",
                env_overrides={"HOME": str(home_dir)},
            )

        self.assertEqual(result.returncode, ExitCode.AUTH)
        self.assertIn("provider", result.stdout)
        self.assertIn("elevenlabs", result.stdout)
        self.assertIn("ELEVENLABS_API_KEY", result.stdout)
        self.assertEqual(result.stderr, "")

    def test_installed_config_path_uses_default_xdg_location(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            home_dir = Path(temp_dir) / "home"
            home_dir.mkdir()
            xdg_config_home = Path(temp_dir) / "xdg-config"

            result = self.run_ttsrun(
                "config",
                "path",
                env_overrides={
                    "HOME": str(home_dir),
                    "XDG_CONFIG_HOME": str(xdg_config_home),
                },
            )

        self.assertEqual(result.returncode, ExitCode.OK, result.stderr)
        self.assertEqual(
            result.stdout.strip(),
            str(xdg_config_home / "voice-dashboard" / "config.json"),
        )

    def test_installed_config_show_accepts_explicit_legacy_style_config_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            legacy_path = Path(temp_dir) / ".voice-dashboard.json"
            legacy_path.write_text(
                json.dumps(
                    {
                        "providers": {
                            "minimax": {
                                "voice_id": "legacy-voice",
                            }
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = self.run_ttsrun("config", "show", "--config", str(legacy_path))

        self.assertEqual(result.returncode, ExitCode.OK, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["config_path"], str(legacy_path))
        self.assertEqual(payload["providers"]["minimax"]["voice_id"], "legacy-voice")
        self.assertTrue(payload["config_exists"])

    def test_installed_config_init_writes_default_config_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            home_dir = Path(temp_dir) / "home"
            home_dir.mkdir()
            xdg_config_home = Path(temp_dir) / "xdg-config"
            expected_path = xdg_config_home / "voice-dashboard" / "config.json"

            result = self.run_ttsrun(
                "config",
                "init",
                env_overrides={
                    "HOME": str(home_dir),
                    "XDG_CONFIG_HOME": str(xdg_config_home),
                },
            )

            self.assertEqual(result.returncode, ExitCode.OK, result.stderr)
            self.assertTrue(expected_path.exists())
            self.assertIn(str(expected_path), result.stdout)

    def test_installed_config_show_prints_effective_config_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            home_dir = Path(temp_dir) / "home"
            home_dir.mkdir()
            xdg_config_home = Path(temp_dir) / "xdg-config"
            config_path = xdg_config_home / "voice-dashboard" / "config.json"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(
                json.dumps(
                    {
                        "global": {
                            "output_root": str(home_dir / "tts-output"),
                        },
                        "providers": {
                            "minimax": {
                                "voice_id": "cfg-voice",
                            }
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = self.run_ttsrun(
                "config",
                "show",
                env_overrides={
                    "HOME": str(home_dir),
                    "XDG_CONFIG_HOME": str(xdg_config_home),
                },
            )

        self.assertEqual(result.returncode, ExitCode.OK, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["providers"]["minimax"]["voice_id"], "cfg-voice")
        self.assertEqual(payload["config_path"], str(config_path))
        self.assertTrue(payload["config_exists"])

    def test_installed_run_reports_invalid_config_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            home_dir = Path(temp_dir) / "home"
            home_dir.mkdir()
            input_path = Path(temp_dir) / "input.txt"
            config_path = Path(temp_dir) / "config.json"
            input_path.write_text("第一段", encoding="utf-8")
            config_path.write_text("{invalid", encoding="utf-8")

            result = self.run_ttsrun(
                "run",
                str(input_path),
                "--config",
                str(config_path),
                env_overrides={"HOME": str(home_dir), "MINIMAX_API_KEY": "test-key"},
            )

        self.assertEqual(result.returncode, ExitCode.CONFIG)
        self.assertIn("Config file is not valid JSON", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_installed_clipboard_command_fails_when_no_backend_is_available(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            home_dir = Path(temp_dir) / "home"
            home_dir.mkdir()

            result = self.run_ttsrun(
                "--clipboard",
                env_overrides={"HOME": str(home_dir), "PATH": ""},
            )

        self.assertEqual(result.returncode, ExitCode.INPUT)
        self.assertIn("Clipboard input is not available", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_installed_run_reports_missing_input_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            home_dir = Path(temp_dir) / "home"
            home_dir.mkdir()
            missing_input_path = Path(temp_dir) / "missing.txt"

            result = self.run_ttsrun(
                str(missing_input_path),
                env_overrides={"HOME": str(home_dir), "MINIMAX_API_KEY": "test-key"},
            )

        self.assertEqual(result.returncode, ExitCode.INPUT)
        self.assertIn("Input file not found", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_installed_run_without_api_key_returns_auth_exit_code(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            home_dir = Path(temp_dir) / "home"
            home_dir.mkdir()
            input_path = Path(temp_dir) / "input.txt"
            output_dir = Path(temp_dir) / "out"
            input_path.write_text("第一段", encoding="utf-8")

            result = self.run_ttsrun(
                "run",
                str(input_path),
                "--output-dir",
                str(output_dir),
                env_overrides={"HOME": str(home_dir)},
            )

        self.assertEqual(result.returncode, ExitCode.AUTH)
        self.assertIn("MINIMAX_API_KEY is not set", result.stderr)
        self.assertEqual(result.stdout, "")
