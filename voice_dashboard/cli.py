import argparse
import json
import os
import sys
from pathlib import Path

from voice_dashboard import __version__
from voice_dashboard.config import (
    AppConfig,
    example_config,
    load_config,
    resolve_config_path,
    write_example_config,
)
from voice_dashboard.defaults import DEFAULT_FORMAT
from voice_dashboard.errors import (
    ConfigError,
    ExitCode,
    InputSourceError,
    TTSBatchError,
    exit_code_for_error,
)
from voice_dashboard.input_sources import (
    InputSource,
    detect_clipboard_reader,
    read_clipboard_source,
    read_file_source,
    read_stdin_source,
)
from voice_dashboard.pipeline import (
    TTSSettings,
    build_output_dir,
    detect_output_dir_opener,
    find_ffmpeg_path,
    get_api_key,
    open_output_dir,
    run_batch_job,
)


def parse_pitch(value: str) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "pitch must be an integer, for example 0, 1, or -1."
        ) from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Batch synthesize text into MP3 files with daily-friendly input modes."
    )
    parser.add_argument("input_path", nargs="?", help="Path to a UTF-8 text file.")
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="Read text from standard input.",
    )
    parser.add_argument(
        "--clipboard",
        action="store_true",
        help="Read text from the system clipboard when a supported clipboard tool is available.",
    )
    parser.add_argument("--config", help="Path to a JSON config file.")

    command_group = parser.add_mutually_exclusive_group()
    command_group.add_argument(
        "--version",
        action="store_true",
        help="Print the installed voice-dashboard version and exit.",
    )
    command_group.add_argument(
        "--doctor",
        action="store_true",
        help="Check environment, config, and optional dependencies.",
    )
    command_group.add_argument(
        "--print-config-example",
        action="store_true",
        help="Print an example config JSON and exit.",
    )
    command_group.add_argument(
        "--print-config-path",
        action="store_true",
        help="Print the resolved config file path and exit.",
    )
    command_group.add_argument(
        "--init-config",
        action="store_true",
        help="Write an example config file to the resolved config path and exit.",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files when supported, for example with --init-config.",
    )
    parser.add_argument(
        "--output-dir",
        help="Write results into this exact directory.",
    )
    parser.add_argument(
        "--output-root",
        help="Root directory used when --output-dir is not provided.",
    )
    parser.add_argument(
        "--name",
        help="Custom label used in the generated output folder name.",
    )
    parser.add_argument("--voice-id", help="MiniMax voice ID.")
    parser.add_argument("--speed", type=float, help="Voice speed multiplier.")
    parser.add_argument(
        "--pitch",
        type=parse_pitch,
        help="Voice pitch adjustment. MiniMax expects an integer.",
    )
    parser.add_argument("--language-boost", help="language_boost payload value.")
    parser.add_argument("--model", help="MiniMax model name.")
    parser.add_argument("--sample-rate", type=int, help="Output audio sample rate.")
    parser.add_argument(
        "--format",
        choices=[DEFAULT_FORMAT],
        help="Output audio format.",
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Merge all successful segment files into merged.mp3 and delete the segment files.",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        default=None,
        help="Open the output directory after the job finishes.",
    )
    return parser


def resolve_open_after_finish(args: argparse.Namespace, config: AppConfig) -> bool:
    if args.open is not None:
        return args.open
    return config.open_after_finish


def resolve_settings(args: argparse.Namespace, config: AppConfig) -> TTSSettings:
    return TTSSettings(
        model=args.model or config.model,
        language_boost=args.language_boost or config.language_boost,
        voice_id=args.voice_id or config.voice_id,
        speed=args.speed if args.speed is not None else config.speed,
        pitch=args.pitch if args.pitch is not None else config.pitch,
        sample_rate=(
            args.sample_rate if args.sample_rate is not None else config.sample_rate
        ),
        audio_format=args.format or config.audio_format,
    )


def resolve_input_source(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
) -> InputSource:
    selected = sum(
        [
            1 if args.input_path else 0,
            1 if args.stdin else 0,
            1 if args.clipboard else 0,
        ]
    )
    if selected != 1:
        parser.error(
            "Provide exactly one input source: file path, --stdin, or --clipboard."
        )

    if args.input_path:
        return read_file_source(args.input_path)
    if args.stdin:
        return read_stdin_source()
    return read_clipboard_source()


def print_doctor_check(status: str, label: str, detail: str) -> None:
    print(f"[{status}] {label}: {detail}")


def run_doctor(config_path: str | None) -> int:
    exit_code = ExitCode.OK
    resolved_config_path = resolve_config_path(config_path)

    print(f"voice-dashboard {__version__}")
    print(f"python: {sys.version.split()[0]}")
    print_doctor_check("ok", "config path", str(resolved_config_path))

    if resolved_config_path.exists():
        try:
            load_config(str(resolved_config_path))
        except ConfigError as exc:
            print_doctor_check("fail", "config file", str(exc))
            if exit_code == ExitCode.OK:
                exit_code = ExitCode.CONFIG
        else:
            print_doctor_check("ok", "config file", "loaded successfully")
    else:
        print_doctor_check(
            "warn",
            "config file",
            "not found; defaults will be used until you run --init-config",
        )

    api_key = os.getenv("MINIMAX_API_KEY", "").strip()
    if api_key:
        print_doctor_check("ok", "MINIMAX_API_KEY", f"set ({len(api_key)} chars)")
    else:
        print_doctor_check(
            "fail",
            "MINIMAX_API_KEY",
            "not set; export it before running ttsrun",
        )
        if exit_code == ExitCode.OK:
            exit_code = ExitCode.AUTH

    ffmpeg_path = find_ffmpeg_path()
    if ffmpeg_path:
        print_doctor_check("ok", "ffmpeg", ffmpeg_path)
    else:
        print_doctor_check(
            "warn",
            "ffmpeg",
            "not found; install it before using --merge",
        )

    clipboard_reader = detect_clipboard_reader()
    if clipboard_reader is None:
        print_doctor_check(
            "warn",
            "clipboard",
            "no supported clipboard command found (pbpaste, wl-paste, xclip, xsel)",
        )
    else:
        reader_name, _, description = clipboard_reader
        print_doctor_check("ok", "clipboard", f"{description} via {reader_name}")

    opener = detect_output_dir_opener()
    if opener is None:
        print_doctor_check(
            "warn",
            "folder opener",
            "no supported opener found (open or xdg-open)",
        )
    else:
        print_doctor_check("ok", "folder opener", opener)

    return int(exit_code)


def handle_management_command(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
) -> int | None:
    if args.force and not args.init_config:
        parser.error("--force can only be used with --init-config.")

    if args.version:
        print(__version__)
        return ExitCode.OK

    if args.print_config_example:
        print(json.dumps(example_config(), ensure_ascii=False, indent=2))
        return ExitCode.OK

    if args.print_config_path:
        print(resolve_config_path(args.config))
        return ExitCode.OK

    if args.init_config:
        path = write_example_config(args.config, overwrite=args.force)
        print(f"Wrote example config to {path}")
        return ExitCode.OK

    if args.doctor:
        return run_doctor(args.config)

    return None


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    command_result = handle_management_command(parser, args)
    if command_result is not None:
        return int(command_result)

    try:
        config = load_config(args.config)
        source = resolve_input_source(parser, args)
        settings = resolve_settings(args, config)
        output_root = (
            Path(args.output_root).expanduser()
            if args.output_root
            else config.output_root
        )
        output_dir = build_output_dir(
            source=source,
            output_root=output_root,
            explicit_output_dir=args.output_dir,
            job_name=args.name,
        )
        result = run_batch_job(
            source=source,
            output_dir=output_dir,
            settings=settings,
            api_key=get_api_key(),
            merge=args.merge,
        )
        if resolve_open_after_finish(args, config):
            try:
                open_output_dir(result.output_dir)
            except TTSBatchError as exc:
                print(f"Warning: {exc}", file=sys.stderr)
        return result.exit_code
    except (ConfigError, InputSourceError, TTSBatchError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return int(exit_code_for_error(exc))


def main_entry() -> None:
    raise SystemExit(main())
