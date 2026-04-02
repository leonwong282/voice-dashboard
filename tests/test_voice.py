import json
import os
import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

import requests

import voice


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
        self.assertEqual(voice.parse_segments(""), [])

    def test_parse_segments_returns_empty_for_whitespace_only(self):
        self.assertEqual(voice.parse_segments(" \n\t\r\n "), [])

    def test_parse_segments_supports_single_segment(self):
        self.assertEqual(voice.parse_segments("hello world"), ["hello world"])

    def test_parse_segments_splits_on_blank_lines_and_preserves_internal_newlines(self):
        text = "第一段第一行\n第一段第二行\n\n\n 第二段 \n\n第三段\n保留換行 "
        self.assertEqual(
            voice.parse_segments(text),
            ["第一段第一行\n第一段第二行", "第二段", "第三段\n保留換行"],
        )


class CLITests(unittest.TestCase):
    def test_main_requires_input_argument(self):
        with self.assertRaises(SystemExit) as context:
            voice.main([])
        self.assertEqual(context.exception.code, 2)

    def test_main_returns_error_when_input_file_is_missing(self):
        with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True):
            exit_code = voice.main(["--input", "missing.txt"])
        self.assertEqual(exit_code, 1)

    def test_main_returns_error_when_api_key_is_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.txt"
            input_path.write_text("one paragraph", encoding="utf-8")

            with patch.dict(os.environ, {}, clear=True):
                exit_code = voice.main(["--input", str(input_path)])

        self.assertEqual(exit_code, 1)

    def test_main_rejects_non_integer_pitch(self):
        with self.assertRaises(SystemExit) as context:
            voice.main(["--input", "example.txt", "--pitch", "0.5"])
        self.assertEqual(context.exception.code, 2)

    def test_custom_voice_settings_are_sent_to_api(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.txt"
            output_dir = Path(temp_dir) / "out"
            input_path.write_text("第一段", encoding="utf-8")

            response = MockResponse(
                200,
                {"base_resp": {"status_code": 0}, "data": {"audio": "414243"}},
            )

            with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True):
                with patch("voice.requests.post", return_value=response) as mock_post:
                    exit_code = voice.main(
                        [
                            "--input",
                            str(input_path),
                            "--output-dir",
                            str(output_dir),
                            "--voice-id",
                            "custom-voice",
                            "--speed",
                            "1.5",
                            "--pitch",
                            "1",
                            "--language-boost",
                            "Chinese,Mandarin",
                            "--model",
                            "speech-custom",
                            "--sample-rate",
                            "44100",
                        ]
                    )

        self.assertEqual(exit_code, 0)
        self.assertEqual(mock_post.call_count, 1)
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["model"], "speech-custom")
        self.assertEqual(payload["language_boost"], "Chinese,Mandarin")
        self.assertEqual(payload["voice_setting"]["voice_id"], "custom-voice")
        self.assertEqual(payload["voice_setting"]["speed"], 1.5)
        self.assertEqual(payload["voice_setting"]["pitch"], 1)
        self.assertEqual(payload["audio_setting"]["sample_rate"], 44100)


class BatchFlowTests(unittest.TestCase):
    def _mock_successful_merge(self, mock_subprocess_run, output_dir):
        def fake_run(cmd, capture_output, text, check):
            Path(cmd[-1]).write_bytes(b"merged-audio")
            return CompletedProcess(cmd, 0, stdout="", stderr="")

        mock_subprocess_run.side_effect = fake_run
        return output_dir / "merged.mp3"

    def test_retryable_request_is_retried_and_succeeds(self):
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
                    "voice.requests.post",
                    side_effect=[
                        requests.ConnectionError("temporary"),
                        success_response,
                    ],
                ) as mock_post:
                    with patch("voice.time.sleep"):
                        exit_code = voice.main(
                            [
                                "--input",
                                str(input_path),
                                "--output-dir",
                                str(output_dir),
                            ]
                        )

            self.assertEqual(exit_code, 0)
            self.assertEqual(mock_post.call_count, 2)
            self.assertTrue((output_dir / "0001.mp3").exists())
            self.assertFalse((output_dir / "merged.mp3").exists())

    def test_merge_is_optional_and_disabled_by_default(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.txt"
            output_dir = Path(temp_dir) / "out"
            input_path.write_text("第一段\n\n第二段", encoding="utf-8")

            success_response = MockResponse(
                200,
                {"base_resp": {"status_code": 0}, "data": {"audio": "414243"}},
            )

            with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True):
                with patch("voice.requests.post", return_value=success_response):
                    with patch("voice.subprocess.run") as mock_subprocess_run:
                        exit_code = voice.main(
                            [
                                "--input",
                                str(input_path),
                                "--output-dir",
                                str(output_dir),
                            ]
                        )

            manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(exit_code, 0)
            self.assertTrue((output_dir / "0001.mp3").exists())
            self.assertTrue((output_dir / "0002.mp3").exists())
            self.assertFalse((output_dir / "merged.mp3").exists())
            self.assertEqual(manifest["summary"]["merge_status"], "skipped")
            self.assertEqual(manifest["summary"]["cleanup_status"], "skipped")
            self.assertIsNone(manifest["summary"]["merged_output_file"])
            mock_subprocess_run.assert_not_called()

    def test_batch_continues_after_segment_failure_and_writes_error_files(self):
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
                    "voice.requests.post",
                    side_effect=[success_response, failure_response, success_response],
                ):
                    with patch("voice.subprocess.run") as mock_subprocess_run:
                        exit_code = voice.main(
                            [
                                "--input",
                                str(input_path),
                                "--output-dir",
                                str(output_dir),
                                "--merge",
                            ]
                        )

            manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
            errors_lines = (output_dir / "errors.jsonl").read_text(encoding="utf-8").splitlines()

            self.assertEqual(exit_code, 1)
            self.assertTrue((output_dir / "0001.mp3").exists())
            self.assertFalse((output_dir / "0002.mp3").exists())
            self.assertTrue((output_dir / "0003.mp3").exists())
            self.assertEqual(manifest["summary"]["succeeded"], 2)
            self.assertEqual(manifest["summary"]["failed"], 1)
            self.assertEqual(manifest["segments"][1]["status"], "failed")
            self.assertIsNone(manifest["segments"][1]["output_file"])
            self.assertEqual(manifest["summary"]["merge_status"], "skipped")
            self.assertEqual(manifest["summary"]["cleanup_status"], "skipped")
            self.assertIsNone(manifest["summary"]["merged_output_file"])
            mock_subprocess_run.assert_not_called()
            self.assertEqual(len(errors_lines), 1)
            self.assertIn("invalid text", errors_lines[0])

    def test_merge_fails_when_ffmpeg_is_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.txt"
            output_dir = Path(temp_dir) / "out"
            input_path.write_text("第一段\n\n第二段", encoding="utf-8")

            success_response = MockResponse(
                200,
                {"base_resp": {"status_code": 0}, "data": {"audio": "414243"}},
            )

            with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True):
                with patch("voice.requests.post", return_value=success_response):
                    with patch("voice.shutil.which", return_value=None):
                        exit_code = voice.main(
                            [
                                "--input",
                                str(input_path),
                                "--output-dir",
                                str(output_dir),
                                "--merge",
                            ]
                        )

            manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(exit_code, 1)
            self.assertTrue((output_dir / "0001.mp3").exists())
            self.assertTrue((output_dir / "0002.mp3").exists())
            self.assertFalse((output_dir / "merged.mp3").exists())
            self.assertEqual(manifest["summary"]["merge_status"], "failed")
            self.assertEqual(manifest["summary"]["cleanup_status"], "skipped")
            self.assertIn("ffmpeg", manifest["summary"]["merge_error"])

    def test_merge_failure_keeps_segment_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.txt"
            output_dir = Path(temp_dir) / "out"
            input_path.write_text("第一段\n\n第二段", encoding="utf-8")

            success_response = MockResponse(
                200,
                {"base_resp": {"status_code": 0}, "data": {"audio": "414243"}},
            )

            with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True):
                with patch("voice.requests.post", return_value=success_response):
                    with patch("voice.shutil.which", return_value="/opt/homebrew/bin/ffmpeg"):
                        with patch(
                            "voice.subprocess.run",
                            return_value=CompletedProcess(
                                ["ffmpeg"], 1, stdout="", stderr="concat failed"
                            ),
                        ):
                            exit_code = voice.main(
                                [
                                    "--input",
                                    str(input_path),
                                    "--output-dir",
                                    str(output_dir),
                                    "--merge",
                                ]
                            )

            manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(exit_code, 1)
            self.assertTrue((output_dir / "0001.mp3").exists())
            self.assertTrue((output_dir / "0002.mp3").exists())
            self.assertFalse((output_dir / "merged.mp3").exists())
            self.assertEqual(manifest["summary"]["merge_status"], "failed")
            self.assertEqual(manifest["summary"]["cleanup_status"], "skipped")
            self.assertEqual(manifest["summary"]["merge_error"], "concat failed")

    def test_cleanup_failure_preserves_merged_output_and_returns_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.txt"
            output_dir = Path(temp_dir) / "out"
            input_path.write_text("第一段\n\n第二段", encoding="utf-8")

            success_response = MockResponse(
                200,
                {"base_resp": {"status_code": 0}, "data": {"audio": "414243"}},
            )

            with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True):
                with patch("voice.requests.post", return_value=success_response):
                    with patch("voice.shutil.which", return_value="/opt/homebrew/bin/ffmpeg"):
                        with patch("voice.subprocess.run") as mock_subprocess_run:
                            self._mock_successful_merge(mock_subprocess_run, output_dir)
                            with patch(
                                "voice.delete_segment_files",
                                return_value=(
                                    1,
                                    ["Failed to delete 0001.mp3: permission denied"],
                                ),
                            ):
                                exit_code = voice.main(
                                    [
                                        "--input",
                                        str(input_path),
                                        "--output-dir",
                                        str(output_dir),
                                        "--merge",
                                    ]
                                )

            manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(exit_code, 1)
            self.assertTrue((output_dir / "merged.mp3").exists())
            self.assertEqual(manifest["summary"]["merge_status"], "success")
            self.assertEqual(manifest["summary"]["cleanup_status"], "failed")
            self.assertEqual(manifest["summary"]["deleted_segment_files"], 1)
            self.assertIn("permission denied", manifest["summary"]["merge_error"])

    def test_sample_file_generates_expected_outputs(self):
        sample_path = Path(__file__).resolve().parent.parent / "examples" / "sample.txt"
        expected_segments = voice.parse_segments(sample_path.read_text(encoding="utf-8"))

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "sample-output"
            success_response = MockResponse(
                200,
                {"base_resp": {"status_code": 0}, "data": {"audio": "414243"}},
            )

            with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True):
                with patch("voice.requests.post", return_value=success_response):
                    with patch("voice.shutil.which", return_value="/opt/homebrew/bin/ffmpeg"):
                        with patch("voice.subprocess.run") as mock_subprocess_run:
                            self._mock_successful_merge(mock_subprocess_run, output_dir)
                            exit_code = voice.main(
                                [
                                    "--input",
                                    str(sample_path),
                                    "--output-dir",
                                    str(output_dir),
                                    "--merge",
                                ]
                            )

            manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))

            self.assertEqual(exit_code, 0)
            self.assertEqual(len(manifest["segments"]), len(expected_segments))
            self.assertEqual(manifest["summary"]["total_segments"], len(expected_segments))
            self.assertEqual(manifest["summary"]["merge_status"], "success")
            self.assertEqual(manifest["summary"]["cleanup_status"], "success")
            self.assertEqual(manifest["summary"]["merged_output_file"], "merged.mp3")
            self.assertTrue((output_dir / "merged.mp3").exists())
            for index, segment in enumerate(expected_segments, start=1):
                filename = f"{index:04d}.mp3"
                self.assertFalse((output_dir / filename).exists())
                self.assertEqual(manifest["segments"][index - 1]["output_file"], filename)
                self.assertEqual(manifest["segments"][index - 1]["text"], segment)

    def test_sample_file_without_merge_keeps_segment_outputs(self):
        sample_path = Path(__file__).resolve().parent.parent / "examples" / "sample.txt"
        expected_segments = voice.parse_segments(sample_path.read_text(encoding="utf-8"))

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "sample-output"
            success_response = MockResponse(
                200,
                {"base_resp": {"status_code": 0}, "data": {"audio": "414243"}},
            )

            with patch.dict(os.environ, {"MINIMAX_API_KEY": "test-key"}, clear=True):
                with patch("voice.requests.post", return_value=success_response):
                    with patch("voice.subprocess.run") as mock_subprocess_run:
                        exit_code = voice.main(
                            [
                                "--input",
                                str(sample_path),
                                "--output-dir",
                                str(output_dir),
                            ]
                        )

            manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))

            self.assertEqual(exit_code, 0)
            self.assertEqual(manifest["summary"]["merge_status"], "skipped")
            self.assertEqual(manifest["summary"]["cleanup_status"], "skipped")
            self.assertFalse((output_dir / "merged.mp3").exists())
            mock_subprocess_run.assert_not_called()
            for index, segment in enumerate(expected_segments, start=1):
                filename = f"{index:04d}.mp3"
                self.assertTrue((output_dir / filename).exists())
                self.assertEqual(manifest["segments"][index - 1]["output_file"], filename)
                self.assertEqual(manifest["segments"][index - 1]["text"], segment)


if __name__ == "__main__":
    unittest.main()
