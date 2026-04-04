import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

import requests

import voice
from voice_dashboard import __version__
from voice_dashboard import cli, pipeline
from voice_dashboard.errors import ExitCode


class MockResponse:
    def __init__(self, status_code, payload=None, text="", content=b""):
        self.status_code = status_code
        self._payload = payload
        self.text = text
        self.content = content

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class ParseSegmentsTests(unittest.TestCase):
    def test_parse_segments_returns_empty_for_empty_text(self):
        self.assertEqual(pipeline.parse_segments(""), [])

    def test_parse_segments_returns_empty_for_whitespace_only(self):
        self.assertEqual(pipeline.parse_segments(" \n\t\r\n "), [])

    def test_parse_segments_supports_single_segment(self):
        self.assertEqual(pipeline.parse_segments("hello world"), ["hello world"])

    def test_parse_segments_splits_on_blank_lines_and_preserves_internal_newlines(self):
        text = "第一段第一行\n第一段第二行\n\n\n 第二段 \n\n第三段\n保留換行 "
        self.assertEqual(
            pipeline.parse_segments(text),
            ["第一段第一行\n第一段第二行", "第二段", "第三段\n保留換行"],
        )


class CLITests(unittest.TestCase):
    def test_version_prints_installed_version(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = cli.main(["--version"])

        self.assertEqual(exit_code, ExitCode.OK)
        self.assertEqual(buffer.getvalue().strip(), __version__)

    def test_print_config_example(self):
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
            exit_code = cli.main(["--print-config-example"])

        self.assertEqual(exit_code, ExitCode.OK)
        payload = json.loads(stdout_buffer.getvalue())
        self.assertEqual(payload["provider"], "minimax")
        self.assertIn("defaults", payload)
        self.assertIn("providers", payload)
        self.assertIn("voice_id", payload["defaults"])
        self.assertIn("output_root", payload["defaults"])
        self.assertIn("format", payload["defaults"])
        self.assertIn("deprecated", stderr_buffer.getvalue())
        self.assertIn("ttsrun config example", stderr_buffer.getvalue())

    def test_config_example_subcommand(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = cli.main(["config", "example"])

        self.assertEqual(exit_code, ExitCode.OK)
        payload = json.loads(buffer.getvalue())
        self.assertEqual(payload["provider"], "minimax")
        self.assertIn("defaults", payload)
        self.assertIn("providers", payload)
        self.assertIn("voice_id", payload["defaults"])

    def test_print_config_path_uses_resolved_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            home_dir = Path(temp_dir) / "home"
            home_dir.mkdir()
            stdout_buffer = io.StringIO()
            stderr_buffer = io.StringIO()

            with patch.dict(
                os.environ,
                {"HOME": str(home_dir)},
                clear=True,
            ):
                with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                    exit_code = cli.main(["--print-config-path"])

            self.assertEqual(exit_code, ExitCode.OK)
            self.assertEqual(
                stdout_buffer.getvalue().strip(),
                str(home_dir / ".config" / "voice-dashboard" / "config.json"),
            )
            self.assertIn("deprecated", stderr_buffer.getvalue())
            self.assertIn("ttsrun config path", stderr_buffer.getvalue())

    def test_config_path_subcommand_uses_resolved_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            home_dir = Path(temp_dir) / "home"
            home_dir.mkdir()
            buffer = io.StringIO()

            with patch.dict(
                os.environ,
                {"HOME": str(home_dir)},
                clear=True,
            ):
                with redirect_stdout(buffer):
                    exit_code = cli.main(["config", "path"])

            self.assertEqual(exit_code, ExitCode.OK)
            self.assertEqual(
                buffer.getvalue().strip(),
                str(home_dir / ".config" / "voice-dashboard" / "config.json"),
            )

    def test_config_path_subcommand_uses_new_default_location_for_new_users(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            home_dir = Path(temp_dir) / "home"
            home_dir.mkdir()
            buffer = io.StringIO()

            with patch.dict(
                os.environ,
                {"HOME": str(home_dir)},
                clear=True,
            ):
                with redirect_stdout(buffer):
                    exit_code = cli.main(["config", "path"])

            self.assertEqual(exit_code, ExitCode.OK)
            self.assertEqual(
                buffer.getvalue().strip(),
                str(home_dir / ".config" / "voice-dashboard" / "config.json"),
            )

    def test_config_path_subcommand_prefers_legacy_file_when_present(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            home_dir = Path(temp_dir) / "home"
            home_dir.mkdir()
            legacy_path = home_dir / ".voice-dashboard.json"
            legacy_path.write_text("{}", encoding="utf-8")
            buffer = io.StringIO()

            with patch.dict(
                os.environ,
                {"HOME": str(home_dir)},
                clear=True,
            ):
                with redirect_stdout(buffer):
                    exit_code = cli.main(["config", "path"])

            self.assertEqual(exit_code, ExitCode.OK)
            self.assertEqual(buffer.getvalue().strip(), str(legacy_path))

    def test_init_config_writes_example_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            stdout_buffer = io.StringIO()
            stderr_buffer = io.StringIO()

            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                exit_code = cli.main(["--init-config", "--config", str(config_path)])

            self.assertEqual(exit_code, ExitCode.OK)
            self.assertTrue(config_path.exists())
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertIn("defaults", payload)
            self.assertIn("Wrote example config", stdout_buffer.getvalue())
            self.assertIn("deprecated", stderr_buffer.getvalue())
            self.assertIn("ttsrun config init", stderr_buffer.getvalue())

    def test_config_init_subcommand_writes_example_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            buffer = io.StringIO()

            with redirect_stdout(buffer):
                exit_code = cli.main(
                    ["config", "init", "--config", str(config_path)]
                )

            self.assertEqual(exit_code, ExitCode.OK)
            self.assertTrue(config_path.exists())
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertIn("defaults", payload)
            self.assertIn("Wrote example config", buffer.getvalue())

    def test_config_init_subcommand_writes_new_default_path_for_new_users(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            home_dir = Path(temp_dir) / "home"
            home_dir.mkdir()
            buffer = io.StringIO()
            expected_path = home_dir / ".config" / "voice-dashboard" / "config.json"

            with patch.dict(
                os.environ,
                {"HOME": str(home_dir)},
                clear=True,
            ):
                with redirect_stdout(buffer):
                    exit_code = cli.main(["config", "init"])

            self.assertEqual(exit_code, ExitCode.OK)
            self.assertTrue(expected_path.exists())
            self.assertIn(str(expected_path), buffer.getvalue())

    def test_doctor_reports_missing_api_key(self):
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        with patch.dict(os.environ, {}, clear=True):
            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                exit_code = cli.main(["--doctor"])

        self.assertEqual(exit_code, ExitCode.AUTH)
        self.assertIn("MINIMAX_API_KEY", stdout_buffer.getvalue())
        self.assertIn("deprecated", stderr_buffer.getvalue())
        self.assertIn("ttsrun doctor", stderr_buffer.getvalue())

    def test_doctor_subcommand_reports_missing_api_key(self):
        buffer = io.StringIO()
        with patch.dict(os.environ, {}, clear=True):
            with redirect_stdout(buffer):
                exit_code = cli.main(["doctor"])

        self.assertEqual(exit_code, ExitCode.AUTH)
        self.assertIn("MINIMAX_API_KEY", buffer.getvalue())

    def test_doctor_subcommand_honors_provider_override(self):
        buffer = io.StringIO()
        with patch.dict(os.environ, {}, clear=True):
            with redirect_stdout(buffer):
                exit_code = cli.main(["doctor", "--provider", "elevenlabs"])

        self.assertEqual(exit_code, ExitCode.AUTH)
        self.assertIn("provider", buffer.getvalue())
        self.assertIn("elevenlabs", buffer.getvalue())
        self.assertIn("ELEVENLABS_API_KEY", buffer.getvalue())

    def test_doctor_reports_inactive_provider_key_as_info(self):
        buffer = io.StringIO()
        with patch.dict(
            os.environ,
            {
                "MINIMAX_API_KEY": "minimax-key",
                "ELEVENLABS_API_KEY": "elevenlabs-key",
            },
            clear=True,
        ):
            with redirect_stdout(buffer):
                exit_code = cli.main(["doctor"])

        self.assertEqual(exit_code, ExitCode.OK)
        self.assertIn("MINIMAX_API_KEY", buffer.getvalue())
        self.assertIn("ELEVENLABS_API_KEY", buffer.getvalue())
        self.assertIn("inactive provider", buffer.getvalue())

    def test_invalid_config_returns_config_exit_code(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.txt"
            config_path = Path(temp_dir) / "config.json"
            input_path.write_text("第一段", encoding="utf-8")
            config_path.write_text("{invalid", encoding="utf-8")

            with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True):
                exit_code = cli.main([str(input_path), "--config", str(config_path)])

        self.assertEqual(exit_code, ExitCode.CONFIG)

    def test_missing_api_key_returns_auth_exit_code(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.txt"
            input_path.write_text("第一段", encoding="utf-8")

            with patch.dict(os.environ, {}, clear=True):
                exit_code = cli.main([str(input_path)])

        self.assertEqual(exit_code, ExitCode.AUTH)

    def test_force_output_dir_requires_explicit_output_dir(self):
        with self.assertRaises(SystemExit) as context:
            cli.main(["--stdin", "--force-output-dir"])
        self.assertEqual(context.exception.code, 2)

    def test_main_requires_exactly_one_input_source(self):
        with self.assertRaises(SystemExit) as context:
            cli.main([])
        self.assertEqual(context.exception.code, 2)

    def test_main_rejects_non_integer_pitch(self):
        with self.assertRaises(SystemExit) as context:
            cli.main(["sample.txt", "--pitch", "0.5"])
        self.assertEqual(context.exception.code, 2)

    def test_elevenlabs_rejects_pitch_flag(self):
        with self.assertRaises(SystemExit) as context:
            cli.main(["sample.txt", "--provider", "elevenlabs", "--pitch", "1"])
        self.assertEqual(context.exception.code, 2)

    def test_elevenlabs_rejects_language_boost_flag(self):
        with self.assertRaises(SystemExit) as context:
            cli.main(
                ["sample.txt", "--provider", "elevenlabs", "--language-boost", "Chinese,Yue"]
            )
        self.assertEqual(context.exception.code, 2)

    def test_elevenlabs_rejects_sample_rate_flag(self):
        with self.assertRaises(SystemExit) as context:
            cli.main(["sample.txt", "--provider", "elevenlabs", "--sample-rate", "32000"])
        self.assertEqual(context.exception.code, 2)

    def test_wrapper_voice_py_uses_new_cli(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.txt"
            output_dir = Path(temp_dir) / "out"
            input_path.write_text("第一段", encoding="utf-8")
            response = MockResponse(
                200,
                {"base_resp": {"status_code": 0}, "data": {"audio": "414243"}},
            )

            with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True):
                with patch("voice_dashboard.pipeline.requests.post", return_value=response):
                    exit_code = voice.main([str(input_path), "--output-dir", str(output_dir)])
            self.assertEqual(exit_code, ExitCode.OK)
            self.assertTrue((output_dir / "0001.mp3").exists())

    def test_run_subcommand_executes_batch_flow(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.txt"
            output_dir = Path(temp_dir) / "out"
            input_path.write_text("第一段", encoding="utf-8")
            response = MockResponse(
                200,
                {"base_resp": {"status_code": 0}, "data": {"audio": "414243"}},
            )

            with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True):
                with patch("voice_dashboard.pipeline.requests.post", return_value=response):
                    exit_code = cli.main(
                        ["run", str(input_path), "--output-dir", str(output_dir)]
                    )
            self.assertEqual(exit_code, ExitCode.OK)
            self.assertTrue((output_dir / "0001.mp3").exists())

    def test_existing_output_dir_requires_force_output_dir(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.txt"
            output_dir = Path(temp_dir) / "out"
            input_path.write_text("第一段", encoding="utf-8")
            output_dir.mkdir()
            (output_dir / "stale.txt").write_text("keep", encoding="utf-8")
            stderr_buffer = io.StringIO()

            with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True):
                with redirect_stderr(stderr_buffer):
                    exit_code = cli.main(
                        [str(input_path), "--output-dir", str(output_dir)]
                    )

            self.assertEqual(exit_code, ExitCode.INPUT)
            self.assertIn("already exists and is not empty", stderr_buffer.getvalue())

    def test_force_output_dir_allows_existing_output_dir(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.txt"
            output_dir = Path(temp_dir) / "out"
            input_path.write_text("第一段", encoding="utf-8")
            output_dir.mkdir()
            (output_dir / "stale.txt").write_text("keep", encoding="utf-8")
            response = MockResponse(
                200,
                {"base_resp": {"status_code": 0}, "data": {"audio": "414243"}},
            )

            with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True):
                with patch("voice_dashboard.pipeline.requests.post", return_value=response):
                    exit_code = cli.main(
                        [
                            str(input_path),
                            "--output-dir",
                            str(output_dir),
                            "--force-output-dir",
                        ]
                    )

            self.assertEqual(exit_code, ExitCode.OK)
            self.assertTrue((output_dir / "0001.mp3").exists())
            self.assertTrue((output_dir / "stale.txt").exists())

    def test_config_values_are_used_when_cli_flags_are_absent(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.txt"
            config_path = Path(temp_dir) / "config.json"
            custom_root = Path(temp_dir) / "custom-out"
            input_path.write_text("第一段", encoding="utf-8")
            config_path.write_text(
                json.dumps(
                    {
                        "defaults": {
                            "voice_id": "cfg-voice",
                            "speed": 1.6,
                            "pitch": 2,
                            "language_boost": "Chinese,Mandarin",
                            "model": "cfg-model",
                            "sample_rate": 44100,
                            "output_root": str(custom_root),
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            response = MockResponse(
                200,
                {"base_resp": {"status_code": 0}, "data": {"audio": "414243"}},
            )

            with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True):
                with patch(
                    "voice_dashboard.pipeline.requests.post", return_value=response
                ) as mock_post:
                    exit_code = cli.main([str(input_path), "--config", str(config_path)])
            self.assertEqual(exit_code, ExitCode.OK)
            payload = mock_post.call_args.kwargs["json"]
            self.assertEqual(payload["model"], "cfg-model")
            self.assertEqual(payload["language_boost"], "Chinese,Mandarin")
            self.assertEqual(payload["voice_setting"]["voice_id"], "cfg-voice")
            self.assertEqual(payload["voice_setting"]["speed"], 1.6)
            self.assertEqual(payload["voice_setting"]["pitch"], 2)
            self.assertEqual(payload["audio_setting"]["sample_rate"], 44100)

    def test_provider_scoped_config_values_are_used_when_cli_flags_are_absent(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.txt"
            config_path = Path(temp_dir) / "config.json"
            custom_root = Path(temp_dir) / "custom-out"
            input_path.write_text("第一段", encoding="utf-8")
            config_path.write_text(
                json.dumps(
                    {
                        "provider": "minimax",
                        "defaults": {
                            "voice_id": "cfg-voice",
                            "speed": 1.6,
                            "model": "cfg-model",
                            "output_root": str(custom_root),
                        },
                        "providers": {
                            "minimax": {
                                "pitch": 2,
                                "language_boost": "Chinese,Mandarin",
                                "sample_rate": 44100,
                            }
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            response = MockResponse(
                200,
                {"base_resp": {"status_code": 0}, "data": {"audio": "414243"}},
            )

            with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True):
                with patch(
                    "voice_dashboard.pipeline.requests.post", return_value=response
                ) as mock_post:
                    exit_code = cli.main([str(input_path), "--config", str(config_path)])
            self.assertEqual(exit_code, ExitCode.OK)
            payload = mock_post.call_args.kwargs["json"]
            self.assertEqual(payload["model"], "cfg-model")
            self.assertEqual(payload["language_boost"], "Chinese,Mandarin")
            self.assertEqual(payload["voice_setting"]["voice_id"], "cfg-voice")
            self.assertEqual(payload["voice_setting"]["speed"], 1.6)
            self.assertEqual(payload["voice_setting"]["pitch"], 2)
            self.assertEqual(payload["audio_setting"]["sample_rate"], 44100)

    def test_config_runtime_values_are_used_when_cli_flags_are_absent(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.txt"
            config_path = Path(temp_dir) / "config.json"
            input_path.write_text("第一段", encoding="utf-8")
            config_path.write_text(
                json.dumps(
                    {
                        "defaults": {
                            "request_timeout_seconds": 7,
                            "max_retries": 2,
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            success_response = MockResponse(
                200,
                {"base_resp": {"status_code": 0}, "data": {"audio": "414243"}},
            )

            with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True):
                with patch(
                    "voice_dashboard.pipeline.requests.post",
                    side_effect=[requests.ConnectionError("temporary"), success_response],
                ) as mock_post:
                    with patch("voice_dashboard.pipeline.time.sleep"):
                        exit_code = cli.main(
                            [str(input_path), "--config", str(config_path)]
                        )

            self.assertEqual(exit_code, ExitCode.OK)
            self.assertEqual(mock_post.call_count, 2)
            self.assertEqual(mock_post.call_args.kwargs["timeout"], 7)

    def test_cli_runtime_flags_override_config_values(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.txt"
            config_path = Path(temp_dir) / "config.json"
            input_path.write_text("第一段", encoding="utf-8")
            config_path.write_text(
                json.dumps(
                    {
                        "defaults": {
                            "request_timeout_seconds": 30,
                            "max_retries": 1,
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            success_response = MockResponse(
                200,
                {"base_resp": {"status_code": 0}, "data": {"audio": "414243"}},
            )

            with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True):
                with patch(
                    "voice_dashboard.pipeline.requests.post",
                    side_effect=[requests.ConnectionError("temporary"), success_response],
                ) as mock_post:
                    with patch("voice_dashboard.pipeline.time.sleep"):
                        exit_code = cli.main(
                            [
                                str(input_path),
                                "--config",
                                str(config_path),
                                "--request-timeout",
                                "9",
                                "--max-retries",
                                "2",
                            ]
                        )

            self.assertEqual(exit_code, ExitCode.OK)
            self.assertEqual(mock_post.call_count, 2)
            self.assertEqual(mock_post.call_args.kwargs["timeout"], 9)

    def test_config_show_subcommand_prints_effective_config(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "defaults": {
                            "voice_id": "cfg-voice",
                            "output_root": str(Path(temp_dir) / "tts-output"),
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            buffer = io.StringIO()

            with redirect_stdout(buffer):
                exit_code = cli.main(
                    ["config", "show", "--config", str(config_path)]
                )

            self.assertEqual(exit_code, ExitCode.OK)
            payload = json.loads(buffer.getvalue())
            self.assertEqual(payload["provider"], "minimax")
            self.assertEqual(payload["defaults"]["voice_id"], "cfg-voice")
            self.assertEqual(payload["config_path"], str(config_path))
            self.assertTrue(payload["config_exists"])

    def test_config_show_reports_explicit_provider(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "provider": "elevenlabs",
                        "defaults": {
                            "voice_id": "voice-123",
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            buffer = io.StringIO()

            with redirect_stdout(buffer):
                exit_code = cli.main(
                    ["config", "show", "--config", str(config_path)]
                )

            self.assertEqual(exit_code, ExitCode.OK)
            payload = json.loads(buffer.getvalue())
            self.assertEqual(payload["provider"], "elevenlabs")
            self.assertEqual(payload["defaults"]["voice_id"], "voice-123")

    def test_config_show_includes_runtime_defaults(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "defaults": {
                            "request_timeout_seconds": 12,
                            "max_retries": 4,
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            buffer = io.StringIO()

            with redirect_stdout(buffer):
                exit_code = cli.main(
                    ["config", "show", "--config", str(config_path)]
                )

            self.assertEqual(exit_code, ExitCode.OK)
            payload = json.loads(buffer.getvalue())
            self.assertEqual(payload["defaults"]["request_timeout_seconds"], 12)
            self.assertEqual(payload["defaults"]["max_retries"], 4)

    def test_config_show_reports_legacy_resolution_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            home_dir = Path(temp_dir) / "home"
            home_dir.mkdir()
            legacy_path = home_dir / ".voice-dashboard.json"
            legacy_path.write_text("{}", encoding="utf-8")
            buffer = io.StringIO()

            with patch.dict(
                os.environ,
                {"HOME": str(home_dir)},
                clear=True,
            ):
                with redirect_stdout(buffer):
                    exit_code = cli.main(["config", "show"])

            self.assertEqual(exit_code, ExitCode.OK)
            payload = json.loads(buffer.getvalue())
            self.assertEqual(payload["config_path"], str(legacy_path))
            self.assertEqual(
                payload["preferred_config_path"],
                str(home_dir / ".config" / "voice-dashboard" / "config.json"),
            )
            self.assertEqual(payload["legacy_config_path"], str(legacy_path))
            self.assertTrue(payload["using_legacy_config_path"])


class InputSourceTests(unittest.TestCase):
    def test_stdin_input_is_supported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "out"
            response = MockResponse(
                200,
                {"base_resp": {"status_code": 0}, "data": {"audio": "414243"}},
            )

            with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True):
                with patch("sys.stdin", io.StringIO("第一段\n\n第二段\n")):
                    with patch(
                        "voice_dashboard.pipeline.requests.post", return_value=response
                    ):
                        exit_code = cli.main(["--stdin", "--output-dir", str(output_dir)])
            self.assertEqual(exit_code, ExitCode.OK)
            self.assertTrue((output_dir / "0001.mp3").exists())
            self.assertTrue((output_dir / "0002.mp3").exists())

    def test_clipboard_input_is_supported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "out"
            response = MockResponse(
                200,
                {"base_resp": {"status_code": 0}, "data": {"audio": "414243"}},
            )

            with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True):
                with patch(
                    "voice_dashboard.input_sources.shutil.which",
                    return_value="/usr/bin/pbpaste",
                ):
                    with patch(
                        "voice_dashboard.input_sources.subprocess.run",
                        return_value=CompletedProcess(
                            ["pbpaste"], 0, stdout="第一段\n\n第二段", stderr=""
                        ),
                    ):
                        with patch(
                            "voice_dashboard.pipeline.requests.post",
                            return_value=response,
                        ):
                            exit_code = cli.main(
                                ["--clipboard", "--output-dir", str(output_dir)]
                            )
            self.assertEqual(exit_code, ExitCode.OK)
            self.assertTrue((output_dir / "0001.mp3").exists())
            self.assertTrue((output_dir / "0002.mp3").exists())

    def test_clipboard_input_supports_linux_fallback_command(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "out"
            response = MockResponse(
                200,
                {"base_resp": {"status_code": 0}, "data": {"audio": "414243"}},
            )

            def which_side_effect(name):
                if name == "xclip":
                    return "/usr/bin/xclip"
                return None

            with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True):
                with patch(
                    "voice_dashboard.input_sources.shutil.which",
                    side_effect=which_side_effect,
                ):
                    with patch(
                        "voice_dashboard.input_sources.subprocess.run",
                        return_value=CompletedProcess(
                            ["xclip"], 0, stdout="第一段\n\n第二段", stderr=""
                        ),
                    ):
                        with patch(
                            "voice_dashboard.pipeline.requests.post",
                            return_value=response,
                        ):
                            exit_code = cli.main(
                                ["--clipboard", "--output-dir", str(output_dir)]
                            )
            self.assertEqual(exit_code, ExitCode.OK)
            self.assertTrue((output_dir / "0001.mp3").exists())
            self.assertTrue((output_dir / "0002.mp3").exists())


class BatchFlowTests(unittest.TestCase):
    def _mock_successful_merge(self, mock_subprocess_run):
        def fake_run(cmd, capture_output, text, check):
            Path(cmd[-1]).write_bytes(b"merged-audio")
            return CompletedProcess(cmd, 0, stdout="", stderr="")

        mock_subprocess_run.side_effect = fake_run

    def test_merge_is_optional_and_disabled_by_default(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.txt"
            output_dir = Path(temp_dir) / "out"
            input_path.write_text("第一段\n\n第二段", encoding="utf-8")
            response = MockResponse(
                200,
                {"base_resp": {"status_code": 0}, "data": {"audio": "414243"}},
            )

            with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True):
                with patch(
                    "voice_dashboard.pipeline.requests.post", return_value=response
                ):
                    with patch(
                        "voice_dashboard.pipeline.subprocess.run"
                    ) as mock_subprocess_run:
                        exit_code = cli.main([str(input_path), "--output-dir", str(output_dir)])
                manifest = json.loads(
                    (output_dir / "manifest.json").read_text(encoding="utf-8")
                )
                self.assertEqual(exit_code, ExitCode.OK)
                self.assertTrue((output_dir / "0001.mp3").exists())
                self.assertTrue((output_dir / "0002.mp3").exists())
                self.assertFalse((output_dir / "merged.mp3").exists())
                self.assertEqual(manifest["settings"]["provider"], "minimax")
                self.assertEqual(manifest["summary"]["merge_status"], "skipped")
                self.assertEqual(manifest["summary"]["cleanup_status"], "skipped")
                mock_subprocess_run.assert_not_called()

    def test_batch_continues_after_segment_failure_and_skips_merge(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.txt"
            output_dir = Path(temp_dir) / "out"
            input_path.write_text("第一段\n\n第二段\n\n第三段", encoding="utf-8")

            success_response = MockResponse(
                200,
                {"base_resp": {"status_code": 0}, "data": {"audio": "414243"}},
            )
            failure_response = MockResponse(
                400,
                {"base_resp": {"status_msg": "invalid text"}},
            )

            with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True):
                with patch(
                    "voice_dashboard.pipeline.requests.post",
                    side_effect=[success_response, failure_response, success_response],
                ):
                    with patch(
                        "voice_dashboard.pipeline.subprocess.run"
                    ) as mock_subprocess_run:
                        exit_code = cli.main(
                            [str(input_path), "--output-dir", str(output_dir), "--merge"]
                        )
                manifest = json.loads(
                    (output_dir / "manifest.json").read_text(encoding="utf-8")
                )
                errors_lines = (
                    output_dir / "errors.jsonl"
                ).read_text(encoding="utf-8").splitlines()
                self.assertEqual(exit_code, ExitCode.API)
                self.assertTrue((output_dir / "0001.mp3").exists())
                self.assertFalse((output_dir / "0002.mp3").exists())
                self.assertTrue((output_dir / "0003.mp3").exists())
                self.assertEqual(manifest["summary"]["merge_status"], "skipped")
                self.assertEqual(manifest["summary"]["cleanup_status"], "skipped")
                mock_subprocess_run.assert_not_called()
                self.assertEqual(len(errors_lines), 1)
                self.assertIn("invalid text", errors_lines[0])

    def test_merge_fails_when_ffmpeg_is_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.txt"
            output_dir = Path(temp_dir) / "out"
            input_path.write_text("第一段\n\n第二段", encoding="utf-8")
            response = MockResponse(
                200,
                {"base_resp": {"status_code": 0}, "data": {"audio": "414243"}},
            )

            with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True):
                with patch(
                    "voice_dashboard.pipeline.requests.post", return_value=response
                ):
                    with patch("voice_dashboard.pipeline.shutil.which", return_value=None):
                        exit_code = cli.main(
                            [str(input_path), "--output-dir", str(output_dir), "--merge"]
                        )
                manifest = json.loads(
                    (output_dir / "manifest.json").read_text(encoding="utf-8")
                )
                self.assertEqual(exit_code, ExitCode.DEPENDENCY)
                self.assertTrue((output_dir / "0001.mp3").exists())
                self.assertTrue((output_dir / "0002.mp3").exists())
                self.assertFalse((output_dir / "merged.mp3").exists())
                self.assertEqual(manifest["summary"]["merge_status"], "failed")
                self.assertEqual(manifest["summary"]["cleanup_status"], "skipped")
                self.assertIn("ffmpeg", manifest["summary"]["merge_error"])

    def test_merge_success_deletes_segments(self):
        sample_path = Path(__file__).resolve().parent.parent / "examples" / "sample.txt"
        expected_segments = pipeline.parse_segments(sample_path.read_text(encoding="utf-8"))

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "sample-output"
            response = MockResponse(
                200,
                {"base_resp": {"status_code": 0}, "data": {"audio": "414243"}},
            )

            with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True):
                with patch(
                    "voice_dashboard.pipeline.requests.post", return_value=response
                ):
                    with patch(
                        "voice_dashboard.pipeline.shutil.which",
                        return_value="/opt/homebrew/bin/ffmpeg",
                    ):
                        with patch(
                            "voice_dashboard.pipeline.subprocess.run"
                        ) as mock_subprocess_run:
                            self._mock_successful_merge(mock_subprocess_run)
                            exit_code = cli.main(
                                [str(sample_path), "--output-dir", str(output_dir), "--merge"]
                            )
                manifest = json.loads(
                    (output_dir / "manifest.json").read_text(encoding="utf-8")
                )
                self.assertEqual(exit_code, ExitCode.OK)
                self.assertEqual(len(manifest["segments"]), len(expected_segments))
                self.assertEqual(manifest["summary"]["merge_status"], "success")
                self.assertEqual(manifest["summary"]["cleanup_status"], "success")
                self.assertEqual(
                    manifest["summary"]["merged_output_file"], "merged.mp3"
                )
                self.assertTrue((output_dir / "merged.mp3").exists())
                for index, segment in enumerate(expected_segments, start=1):
                    filename = f"{index:04d}.mp3"
                    self.assertFalse((output_dir / filename).exists())
                    self.assertEqual(
                        manifest["segments"][index - 1]["output_file"], filename
                    )
                    self.assertEqual(
                        manifest["segments"][index - 1]["text"], segment
                    )

    def test_cleanup_failure_restores_segments_when_move_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.txt"
            output_dir = Path(temp_dir) / "out"
            input_path.write_text("第一段\n\n第二段", encoding="utf-8")
            response = MockResponse(
                200,
                {"base_resp": {"status_code": 0}, "data": {"audio": "414243"}},
            )
            real_move = pipeline.shutil.move

            def flaky_move(src, dst):
                if Path(src).name == "0002.mp3":
                    raise OSError("permission denied")
                return real_move(src, dst)

            with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True):
                with patch(
                    "voice_dashboard.pipeline.requests.post", return_value=response
                ):
                    with patch(
                        "voice_dashboard.pipeline.shutil.which",
                        return_value="/opt/homebrew/bin/ffmpeg",
                    ):
                        with patch(
                            "voice_dashboard.pipeline.subprocess.run"
                        ) as mock_subprocess_run:
                            with patch(
                                "voice_dashboard.pipeline.shutil.move",
                                side_effect=flaky_move,
                            ):
                                self._mock_successful_merge(mock_subprocess_run)
                                exit_code = cli.main(
                                    [
                                        str(input_path),
                                        "--output-dir",
                                        str(output_dir),
                                        "--merge",
                                    ]
                                )

            manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(exit_code, ExitCode.RUNTIME)
            self.assertEqual(manifest["summary"]["merge_status"], "success")
            self.assertEqual(manifest["summary"]["cleanup_status"], "failed")
            self.assertIn("permission denied", manifest["summary"]["cleanup_error"])
            self.assertIsNone(manifest["summary"]["cleanup_backup_dir"])
            self.assertTrue((output_dir / "merged.mp3").exists())
            self.assertTrue((output_dir / "0001.mp3").exists())
            self.assertTrue((output_dir / "0002.mp3").exists())

    def test_cleanup_failure_preserves_backup_directory_when_removal_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.txt"
            output_dir = Path(temp_dir) / "out"
            input_path.write_text("第一段\n\n第二段", encoding="utf-8")
            response = MockResponse(
                200,
                {"base_resp": {"status_code": 0}, "data": {"audio": "414243"}},
            )

            with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True):
                with patch(
                    "voice_dashboard.pipeline.requests.post", return_value=response
                ):
                    with patch(
                        "voice_dashboard.pipeline.shutil.which",
                        return_value="/opt/homebrew/bin/ffmpeg",
                    ):
                        with patch(
                            "voice_dashboard.pipeline.subprocess.run"
                        ) as mock_subprocess_run:
                            with patch(
                                "voice_dashboard.pipeline.shutil.rmtree",
                                side_effect=OSError("resource busy"),
                            ):
                                self._mock_successful_merge(mock_subprocess_run)
                                exit_code = cli.main(
                                    [
                                        str(input_path),
                                        "--output-dir",
                                        str(output_dir),
                                        "--merge",
                                    ]
                                )

            manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
            backup_dir = Path(manifest["summary"]["cleanup_backup_dir"])
            self.assertEqual(exit_code, ExitCode.RUNTIME)
            self.assertEqual(manifest["summary"]["merge_status"], "success")
            self.assertEqual(manifest["summary"]["cleanup_status"], "failed")
            self.assertIn("resource busy", manifest["summary"]["cleanup_error"])
            self.assertTrue((output_dir / "merged.mp3").exists())
            self.assertFalse((output_dir / "0001.mp3").exists())
            self.assertFalse((output_dir / "0002.mp3").exists())
            self.assertTrue(backup_dir.exists())
            self.assertTrue((backup_dir / "0001.mp3").exists())
            self.assertTrue((backup_dir / "0002.mp3").exists())

    def test_sample_file_without_merge_keeps_segment_outputs(self):
        sample_path = Path(__file__).resolve().parent.parent / "examples" / "sample.txt"
        expected_segments = pipeline.parse_segments(sample_path.read_text(encoding="utf-8"))

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "sample-output"
            response = MockResponse(
                200,
                {"base_resp": {"status_code": 0}, "data": {"audio": "414243"}},
            )

            with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True):
                with patch(
                    "voice_dashboard.pipeline.requests.post", return_value=response
                ):
                    with patch(
                        "voice_dashboard.pipeline.subprocess.run"
                    ) as mock_subprocess_run:
                        exit_code = cli.main([str(sample_path), "--output-dir", str(output_dir)])
                manifest = json.loads(
                    (output_dir / "manifest.json").read_text(encoding="utf-8")
                )
                self.assertEqual(exit_code, ExitCode.OK)
                self.assertEqual(manifest["summary"]["merge_status"], "skipped")
                self.assertEqual(manifest["summary"]["cleanup_status"], "skipped")
                self.assertFalse((output_dir / "merged.mp3").exists())
                mock_subprocess_run.assert_not_called()
                for index, segment in enumerate(expected_segments, start=1):
                    filename = f"{index:04d}.mp3"
                    self.assertTrue((output_dir / filename).exists())
                    self.assertEqual(
                        manifest["segments"][index - 1]["output_file"], filename
                    )
                    self.assertEqual(
                        manifest["segments"][index - 1]["text"], segment
                    )

    def test_retryable_request_is_retried(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.txt"
            output_dir = Path(temp_dir) / "out"
            input_path.write_text("第一段", encoding="utf-8")
            success_response = MockResponse(
                200,
                {"base_resp": {"status_code": 0}, "data": {"audio": "414243"}},
            )

            with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True):
                with patch(
                    "voice_dashboard.pipeline.requests.post",
                    side_effect=[requests.ConnectionError("temporary"), success_response],
                ) as mock_post:
                    with patch("voice_dashboard.pipeline.time.sleep"):
                        exit_code = cli.main([str(input_path), "--output-dir", str(output_dir)])
            self.assertEqual(exit_code, ExitCode.OK)
            self.assertEqual(mock_post.call_count, 2)

    def test_config_provider_is_used_when_cli_provider_is_absent(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.txt"
            output_dir = Path(temp_dir) / "out"
            config_path = Path(temp_dir) / "config.json"
            input_path.write_text("第一段", encoding="utf-8")
            config_path.write_text(
                json.dumps(
                    {
                        "provider": "elevenlabs",
                        "defaults": {
                            "voice_id": "voice-123",
                            "model": "eleven-model",
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            response = MockResponse(200, content=b"ELVN")

            with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test-key"}, clear=True):
                with patch(
                    "voice_dashboard.providers.elevenlabs.requests.post",
                    return_value=response,
                ) as mock_post:
                    exit_code = cli.main(
                        [
                            str(input_path),
                            "--config",
                            str(config_path),
                            "--output-dir",
                            str(output_dir),
                        ]
                    )

            self.assertEqual(exit_code, ExitCode.OK)
            self.assertEqual((output_dir / "0001.mp3").read_bytes(), b"ELVN")
            self.assertEqual(
                mock_post.call_args.args[0],
                "https://api.elevenlabs.io/v1/text-to-speech/voice-123",
            )
            self.assertEqual(
                mock_post.call_args.kwargs["headers"]["xi-api-key"], "test-key"
            )
            self.assertEqual(
                mock_post.call_args.kwargs["params"]["output_format"],
                "mp3_44100_128",
            )
            self.assertEqual(
                mock_post.call_args.kwargs["json"]["model_id"],
                "eleven-model",
            )
            self.assertEqual(
                mock_post.call_args.kwargs["json"]["voice_settings"]["speed"],
                1.2,
            )

    def test_cli_provider_overrides_config_provider(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.txt"
            output_dir = Path(temp_dir) / "out"
            config_path = Path(temp_dir) / "config.json"
            input_path.write_text("第一段", encoding="utf-8")
            config_path.write_text(
                json.dumps(
                    {
                        "provider": "minimax",
                        "defaults": {
                            "voice_id": "voice-123",
                            "model": "cfg-model",
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            response = MockResponse(200, content=b"ELVN")

            with patch.dict(
                os.environ,
                {
                    "MINIMAX_API_KEY": "minimax-key",
                    "ELEVENLABS_API_KEY": "elevenlabs-key",
                },
                clear=True,
            ):
                with patch("voice_dashboard.pipeline.requests.post") as minimax_post:
                    with patch(
                        "voice_dashboard.providers.elevenlabs.requests.post",
                        return_value=response,
                    ) as elevenlabs_post:
                        exit_code = cli.main(
                            [
                                str(input_path),
                                "--config",
                                str(config_path),
                                "--provider",
                                "elevenlabs",
                                "--output-dir",
                                str(output_dir),
                            ]
                        )

            self.assertEqual(exit_code, ExitCode.OK)
            self.assertEqual(minimax_post.call_count, 0)
            self.assertEqual(elevenlabs_post.call_count, 1)
            self.assertTrue((output_dir / "0001.mp3").exists())

    def test_elevenlabs_uses_provider_default_model_when_legacy_default_model_is_present(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.txt"
            output_dir = Path(temp_dir) / "out"
            config_path = Path(temp_dir) / "config.json"
            input_path.write_text("第一段", encoding="utf-8")
            config_path.write_text(
                json.dumps(
                    {
                        "provider": "elevenlabs",
                        "defaults": {
                            "voice_id": "voice-123",
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            response = MockResponse(200, content=b"ELVN")

            with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test-key"}, clear=True):
                with patch(
                    "voice_dashboard.providers.elevenlabs.requests.post",
                    return_value=response,
                ) as mock_post:
                    exit_code = cli.main(
                        [
                            str(input_path),
                            "--config",
                            str(config_path),
                            "--output-dir",
                            str(output_dir),
                        ]
                    )

            self.assertEqual(exit_code, ExitCode.OK)
            manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["settings"]["provider"], "elevenlabs")
            self.assertEqual(
                mock_post.call_args.kwargs["json"]["model_id"],
                "eleven_multilingual_v2",
            )

    def test_elevenlabs_auth_failure_returns_auth_exit_code(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.txt"
            output_dir = Path(temp_dir) / "out"
            input_path.write_text("第一段", encoding="utf-8")
            response = MockResponse(
                401,
                payload={"detail": {"message": "Unauthorized"}},
                text='{"detail":{"message":"Unauthorized"}}',
            )

            with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test-key"}, clear=True):
                with patch(
                    "voice_dashboard.providers.elevenlabs.requests.post",
                    return_value=response,
                ):
                    exit_code = cli.main(
                        [
                            str(input_path),
                            "--provider",
                            "elevenlabs",
                            "--voice-id",
                            "voice-123",
                            "--model",
                            "eleven-model",
                            "--output-dir",
                            str(output_dir),
                        ]
                    )

            self.assertEqual(exit_code, ExitCode.AUTH)

    def test_elevenlabs_403_returns_auth_exit_code(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.txt"
            output_dir = Path(temp_dir) / "out"
            input_path.write_text("第一段", encoding="utf-8")
            response = MockResponse(
                403,
                payload={"detail": {"message": "Forbidden"}},
                text='{"detail":{"message":"Forbidden"}}',
            )

            with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test-key"}, clear=True):
                with patch(
                    "voice_dashboard.providers.elevenlabs.requests.post",
                    return_value=response,
                ):
                    exit_code = cli.main(
                        [
                            str(input_path),
                            "--provider",
                            "elevenlabs",
                            "--voice-id",
                            "voice-123",
                            "--model",
                            "eleven-model",
                            "--output-dir",
                            str(output_dir),
                        ]
                    )

            self.assertEqual(exit_code, ExitCode.AUTH)

    def test_elevenlabs_retryable_request_is_retried(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.txt"
            output_dir = Path(temp_dir) / "out"
            input_path.write_text("第一段", encoding="utf-8")
            success_response = MockResponse(200, content=b"ELVN")

            with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test-key"}, clear=True):
                with patch(
                    "voice_dashboard.providers.elevenlabs.requests.post",
                    side_effect=[requests.ConnectionError("temporary"), success_response],
                ) as mock_post:
                    with patch("voice_dashboard.pipeline.time.sleep"):
                        exit_code = cli.main(
                            [
                                str(input_path),
                                "--provider",
                                "elevenlabs",
                                "--voice-id",
                                "voice-123",
                                "--model",
                                "eleven-model",
                                "--output-dir",
                                str(output_dir),
                            ]
                        )
            self.assertEqual(exit_code, ExitCode.OK)
            self.assertEqual(mock_post.call_count, 2)

    def test_elevenlabs_http_503_is_retried(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.txt"
            output_dir = Path(temp_dir) / "out"
            input_path.write_text("第一段", encoding="utf-8")
            retry_response = MockResponse(
                503,
                payload={"detail": {"message": "temporary outage"}},
                text='{"detail":{"message":"temporary outage"}}',
            )
            success_response = MockResponse(200, content=b"ELVN")

            with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test-key"}, clear=True):
                with patch(
                    "voice_dashboard.providers.elevenlabs.requests.post",
                    side_effect=[retry_response, success_response],
                ) as mock_post:
                    with patch("voice_dashboard.pipeline.time.sleep"):
                        exit_code = cli.main(
                            [
                                str(input_path),
                                "--provider",
                                "elevenlabs",
                                "--voice-id",
                                "voice-123",
                                "--model",
                                "eleven-model",
                                "--output-dir",
                                str(output_dir),
                            ]
                        )
            self.assertEqual(exit_code, ExitCode.OK)
            self.assertEqual(mock_post.call_count, 2)

    def test_json_summary_prints_summary_to_stdout(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.txt"
            output_dir = Path(temp_dir) / "out"
            input_path.write_text("第一段\n\n第二段", encoding="utf-8")
            response = MockResponse(
                200,
                {"base_resp": {"status_code": 0}, "data": {"audio": "414243"}},
            )
            stdout_buffer = io.StringIO()
            stderr_buffer = io.StringIO()

            with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True):
                with patch(
                    "voice_dashboard.pipeline.requests.post", return_value=response
                ):
                    with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                        exit_code = cli.main(
                            [
                                str(input_path),
                                "--output-dir",
                                str(output_dir),
                                "--json-summary",
                            ]
                        )

            self.assertEqual(exit_code, ExitCode.OK)
            payload = json.loads(stdout_buffer.getvalue())
            self.assertEqual(payload["succeeded"], 2)
            self.assertEqual(payload["failed"], 0)
            self.assertIn("Loaded 2 segments", stderr_buffer.getvalue())

    def test_quiet_suppresses_progress_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.txt"
            output_dir = Path(temp_dir) / "out"
            input_path.write_text("第一段", encoding="utf-8")
            response = MockResponse(
                200,
                {"base_resp": {"status_code": 0}, "data": {"audio": "414243"}},
            )
            stderr_buffer = io.StringIO()

            with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True):
                with patch(
                    "voice_dashboard.pipeline.requests.post", return_value=response
                ):
                    with redirect_stderr(stderr_buffer):
                        exit_code = cli.main(
                            [str(input_path), "--output-dir", str(output_dir), "--quiet"]
                        )

            self.assertEqual(exit_code, ExitCode.OK)
            self.assertEqual(stderr_buffer.getvalue(), "")

    def test_verbose_prints_settings_detail(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.txt"
            output_dir = Path(temp_dir) / "out"
            input_path.write_text("第一段", encoding="utf-8")
            response = MockResponse(
                200,
                {"base_resp": {"status_code": 0}, "data": {"audio": "414243"}},
            )
            stderr_buffer = io.StringIO()

            with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True):
                with patch(
                    "voice_dashboard.pipeline.requests.post", return_value=response
                ):
                    with redirect_stderr(stderr_buffer):
                        exit_code = cli.main(
                            [str(input_path), "--output-dir", str(output_dir), "--verbose"]
                        )

            self.assertEqual(exit_code, ExitCode.OK)
            self.assertIn("Settings:", stderr_buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
