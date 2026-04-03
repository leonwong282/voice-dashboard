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
from voice_dashboard import cli, pipeline
from voice_dashboard.errors import ExitCode


class MockResponse:
    def __init__(self, status_code, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

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
        self.assertEqual(buffer.getvalue().strip(), "0.1.0")

    def test_print_config_example(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = cli.main(["--print-config-example"])

        self.assertEqual(exit_code, ExitCode.OK)
        payload = json.loads(buffer.getvalue())
        self.assertIn("defaults", payload)
        self.assertIn("voice_id", payload["defaults"])
        self.assertIn("output_root", payload["defaults"])
        self.assertIn("format", payload["defaults"])

    def test_config_example_subcommand(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = cli.main(["config", "example"])

        self.assertEqual(exit_code, ExitCode.OK)
        payload = json.loads(buffer.getvalue())
        self.assertIn("defaults", payload)
        self.assertIn("voice_id", payload["defaults"])

    def test_print_config_path_uses_resolved_path(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = cli.main(["--print-config-path"])

        self.assertEqual(exit_code, ExitCode.OK)
        self.assertTrue(buffer.getvalue().strip().endswith(".voice-dashboard.json"))

    def test_config_path_subcommand_uses_resolved_path(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = cli.main(["config", "path"])

        self.assertEqual(exit_code, ExitCode.OK)
        self.assertTrue(buffer.getvalue().strip().endswith(".voice-dashboard.json"))

    def test_init_config_writes_example_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            buffer = io.StringIO()

            with redirect_stdout(buffer):
                exit_code = cli.main(["--init-config", "--config", str(config_path)])

            self.assertEqual(exit_code, ExitCode.OK)
            self.assertTrue(config_path.exists())
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertIn("defaults", payload)
            self.assertIn("Wrote example config", buffer.getvalue())

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

    def test_doctor_reports_missing_api_key(self):
        buffer = io.StringIO()
        with patch.dict(os.environ, {}, clear=True):
            with redirect_stdout(buffer):
                exit_code = cli.main(["--doctor"])

        self.assertEqual(exit_code, ExitCode.AUTH)
        self.assertIn("MINIMAX_API_KEY", buffer.getvalue())

    def test_doctor_subcommand_reports_missing_api_key(self):
        buffer = io.StringIO()
        with patch.dict(os.environ, {}, clear=True):
            with redirect_stdout(buffer):
                exit_code = cli.main(["doctor"])

        self.assertEqual(exit_code, ExitCode.AUTH)
        self.assertIn("MINIMAX_API_KEY", buffer.getvalue())

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

    def test_main_requires_exactly_one_input_source(self):
        with self.assertRaises(SystemExit) as context:
            cli.main([])
        self.assertEqual(context.exception.code, 2)

    def test_main_rejects_non_integer_pitch(self):
        with self.assertRaises(SystemExit) as context:
            cli.main(["sample.txt", "--pitch", "0.5"])
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
            self.assertEqual(payload["defaults"]["voice_id"], "cfg-voice")
            self.assertEqual(payload["config_path"], str(config_path))
            self.assertTrue(payload["config_exists"])


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
