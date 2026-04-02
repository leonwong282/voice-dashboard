import argparse
import json
import sys
from pathlib import Path

from voice_dashboard.config import AppConfig, ConfigError, example_config, load_config
from voice_dashboard.defaults import DEFAULT_FORMAT
from voice_dashboard.input_sources import (
    InputSource,
    InputSourceError,
    read_clipboard_source,
    read_file_source,
    read_stdin_source,
)
from voice_dashboard.pipeline import (
    TTSBatchError,
    TTSSettings,
    build_output_dir,
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
        help="Read text from the macOS clipboard using pbpaste.",
    )
    parser.add_argument("--config", help="Path to a JSON config file.")
    parser.add_argument(
        "--print-config-example",
        action="store_true",
        help="Print an example config JSON and exit.",
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
        parser.error("Provide exactly one input source: file path, --stdin, or --clipboard.")

    if args.input_path:
        return read_file_source(args.input_path)
    if args.stdin:
        return read_stdin_source()
    return read_clipboard_source()


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.print_config_example:
        print(json.dumps(example_config(), ensure_ascii=False, indent=2))
        return 0

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
        return 1


def main_entry() -> None:
    raise SystemExit(main())
