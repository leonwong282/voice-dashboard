import io
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import verify_public_install as install_verifier  # noqa: E402


class VerifyWithRetriesTests(unittest.TestCase):
    def test_verify_with_retries_retries_then_succeeds(self):
        with patch.object(
            install_verifier,
            "verify_with_pip",
            side_effect=[
                subprocess.CalledProcessError(1, ["pip", "install"]),
                None,
            ],
        ) as mock_verify_with_pip:
            with patch.object(install_verifier.time, "sleep") as mock_sleep:
                with patch("sys.stdout", new=io.StringIO()), patch(
                    "sys.stderr", new=io.StringIO()
                ):
                    install_verifier.verify_with_retries(
                        package_spec="voice-dashboard==0.4.5",
                        python_executable="/usr/bin/python3",
                        skip_pip=False,
                        skip_pipx=True,
                        attempts=2,
                        retry_delay_seconds=7,
                    )

        self.assertEqual(mock_verify_with_pip.call_count, 2)
        mock_sleep.assert_called_once_with(7)

    def test_verify_with_retries_raises_last_error_after_exhaustion(self):
        error = subprocess.CalledProcessError(1, ["pipx", "install"])

        with patch.object(
            install_verifier,
            "verify_with_pipx",
            side_effect=[error, error, error],
        ) as mock_verify_with_pipx:
            with patch.object(install_verifier.time, "sleep") as mock_sleep:
                with patch("sys.stdout", new=io.StringIO()), patch(
                    "sys.stderr", new=io.StringIO()
                ):
                    with self.assertRaises(subprocess.CalledProcessError):
                        install_verifier.verify_with_retries(
                            package_spec="voice-dashboard==0.4.5",
                            python_executable="/usr/bin/python3",
                            skip_pip=True,
                            skip_pipx=False,
                            attempts=3,
                            retry_delay_seconds=5,
                        )

        self.assertEqual(mock_verify_with_pipx.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)
