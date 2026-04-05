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
    serialize_config,
    write_example_config,
)
from voice_dashboard.defaults import (
    DEFAULT_FORMAT,
)
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
    ProgressReporter,
    RequestSettings,
    build_output_dir,
    detect_output_dir_opener,
    find_ffmpeg_path,
    get_api_key,
    open_output_dir,
    prepare_output_dir,
    run_batch_job,
)
from voice_dashboard.providers.base import (
    CommonTTSSettings,
    ElevenLabsTTSSettings,
    MiniMaxTTSSettings,
    ProviderTTSSettings,
)
from voice_dashboard.providers.registry import (
    DEFAULT_PROVIDER_NAME,
    SUPPORTED_PROVIDER_NAMES,
)


COMMAND_EPILOG = """Management commands:
  ttsrun doctor
  ttsrun config path
  ttsrun config show
  ttsrun config init
  ttsrun config example

Explicit run command:
  ttsrun run <input_path>
"""


LEGACY_FLAG_REPLACEMENTS = {
    "--doctor": "ttsrun doctor",
    "--print-config-path": "ttsrun config path",
    "--print-config-example": "ttsrun config example",
    "--init-config": "ttsrun config init",
}


def parse_pitch(value: str) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "pitch must be an integer, for example 0, 1, or -1."
        ) from exc


def parse_positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("value must be a positive integer.") from exc

    if parsed < 1:
        raise argparse.ArgumentTypeError("value must be a positive integer.")
    return parsed


def add_config_option(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", help="Path to a JSON config file.")


def add_run_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("input_path", nargs="?", help="Path to a UTF-8 text file.")
    parser.add_argument(
        "--provider",
        choices=SUPPORTED_PROVIDER_NAMES,
        help=f"TTS provider to use. Defaults to {DEFAULT_PROVIDER_NAME}.",
    )
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
    add_config_option(parser)
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print the installed voice-dashboard version and exit.",
    )

    parser.add_argument(
        "--doctor",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--print-config-example",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--print-config-path",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--init-config",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=argparse.SUPPRESS,
    )

    parser.add_argument(
        "--output-dir",
        help="Write results into this exact directory. Existing non-empty directories require --force-output-dir.",
    )
    parser.add_argument(
        "--force-output-dir",
        action="store_true",
        help="Allow writing into an existing non-empty --output-dir. Existing generated files may be overwritten.",
    )
    parser.add_argument(
        "--output-root",
        help="Root directory used when --output-dir is not provided.",
    )
    parser.add_argument(
        "--name",
        help="Custom label used in the generated output folder name.",
    )
    parser.add_argument("--voice-id", help="Voice ID for the active provider.")
    parser.add_argument("--speed", type=float, help="Voice speed multiplier.")
    parser.add_argument(
        "--pitch",
        type=parse_pitch,
        help="Voice pitch adjustment. MiniMax expects an integer.",
    )
    parser.add_argument("--language-boost", help="language_boost payload value.")
    parser.add_argument("--model", help="Model name for the active provider.")
    parser.add_argument("--sample-rate", type=int, help="Output audio sample rate.")
    parser.add_argument(
        "--request-timeout",
        type=parse_positive_int,
        help="HTTP request timeout in seconds for each provider attempt.",
    )
    parser.add_argument(
        "--max-retries",
        type=parse_positive_int,
        help="Maximum provider request attempts per segment, including the first attempt.",
    )
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
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output and only print warnings or errors.",
    )
    output_group.add_argument(
        "--verbose",
        action="store_true",
        help="Print additional progress details to stderr.",
    )
    parser.add_argument(
        "--json-summary",
        action="store_true",
        help="Print the final manifest summary as JSON to stdout after the run.",
    )


def build_run_parser(
    prog: str = "ttsrun",
    show_commands: bool = True,
) -> argparse.ArgumentParser:
    return_parser = argparse.ArgumentParser(
        prog=prog,
        description="Batch synthesize text into MP3 files with daily-friendly input modes.",
        epilog=COMMAND_EPILOG if show_commands else None,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_run_options(return_parser)
    return return_parser


def build_doctor_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ttsrun doctor",
        description="Check environment, config, and optional dependencies.",
    )
    add_config_option(parser)
    parser.add_argument(
        "--provider",
        choices=SUPPORTED_PROVIDER_NAMES,
        help="Override the configured provider for doctor checks.",
    )
    return parser


def build_config_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ttsrun config",
        description="Inspect or initialize voice-dashboard configuration.",
    )
    subparsers = parser.add_subparsers(dest="config_command")
    subparsers.required = True

    path_parser = subparsers.add_parser(
        "path",
        help="Print the resolved config file path.",
    )
    add_config_option(path_parser)

    show_parser = subparsers.add_parser(
        "show",
        help="Print the effective configuration as JSON.",
    )
    add_config_option(show_parser)

    init_parser = subparsers.add_parser(
        "init",
        help="Write an example config file.",
    )
    add_config_option(init_parser)
    init_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing config file.",
    )

    example_parser = subparsers.add_parser(
        "example",
        help="Print an example config JSON document.",
    )
    add_config_option(example_parser)

    return parser


def resolve_open_after_finish(args: argparse.Namespace, config: AppConfig) -> bool:
    if args.open is not None:
        return args.open
    return config.open_after_finish


def resolve_provider(args: argparse.Namespace, config: AppConfig) -> str:
    return args.provider or config.provider or DEFAULT_PROVIDER_NAME


def validate_provider_options(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
    provider_name: str,
) -> None:
    if provider_name != "elevenlabs":
        return

    invalid_flags: list[str] = []
    if args.pitch is not None:
        invalid_flags.append("--pitch")
    if args.language_boost is not None:
        invalid_flags.append("--language-boost")
    if args.sample_rate is not None:
        invalid_flags.append("--sample-rate")

    if invalid_flags:
        parser.error(
            f"{', '.join(invalid_flags)} can only be used with --provider=minimax."
        )


def resolve_settings(
    args: argparse.Namespace,
    config: AppConfig,
    provider_name: str,
) -> ProviderTTSSettings:
    provider_config = config.provider_config(provider_name)
    common = CommonTTSSettings(
        model=args.model or provider_config.model,
        voice_id=args.voice_id or provider_config.voice_id,
        speed=args.speed if args.speed is not None else provider_config.speed,
        audio_format=args.format or config.audio_format,
    )

    if provider_name == "minimax":
        return MiniMaxTTSSettings(
            common=common,
            language_boost=args.language_boost or config.minimax.language_boost,
            pitch=args.pitch if args.pitch is not None else config.minimax.pitch,
            sample_rate=(
                args.sample_rate
                if args.sample_rate is not None
                else config.minimax.sample_rate
            ),
        )

    if provider_name == "elevenlabs":
        return ElevenLabsTTSSettings(common=common)

    raise ConfigError(f"Unsupported provider: {provider_name}")


def resolve_request_settings(
    args: argparse.Namespace,
    config: AppConfig,
) -> RequestSettings:
    return RequestSettings(
        timeout_seconds=(
            args.request_timeout
            if args.request_timeout is not None
            else config.request_timeout_seconds
        ),
        max_retries=(
            args.max_retries if args.max_retries is not None else config.max_retries
        ),
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


def print_legacy_flag_warning(flag: str) -> None:
    replacement = LEGACY_FLAG_REPLACEMENTS[flag]
    print(
        f"Warning: {flag} is deprecated and will be removed in a future release. "
        f"Use `{replacement}` instead.",
        file=sys.stderr,
    )


def build_reporter(args: argparse.Namespace) -> ProgressReporter:
    return ProgressReporter(
        quiet=args.quiet,
        verbose=args.verbose,
        stream=sys.stderr,
    )


def run_doctor(config_path: str | None, provider_override: str | None = None) -> int:
    exit_code = ExitCode.OK
    resolved_config_path = resolve_config_path(config_path)
    resolved_provider = DEFAULT_PROVIDER_NAME

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
            resolved_provider = provider_override or load_config(str(resolved_config_path)).provider
    else:
        print_doctor_check(
            "warn",
            "config file",
            "not found; defaults will be used until you run `ttsrun config init`",
        )
        if provider_override:
            resolved_provider = provider_override

    if provider_override and resolved_config_path.exists():
        resolved_provider = provider_override

    print_doctor_check("ok", "provider", resolved_provider)

    api_key_label = (
        "MINIMAX_API_KEY"
        if resolved_provider == "minimax"
        else "ELEVENLABS_API_KEY"
    )
    inactive_api_key_label = (
        "ELEVENLABS_API_KEY"
        if resolved_provider == "minimax"
        else "MINIMAX_API_KEY"
    )
    api_key = os.getenv(api_key_label, "").strip()
    if api_key:
        print_doctor_check("ok", api_key_label, f"set ({len(api_key)} chars)")
    else:
        print_doctor_check(
            "fail",
            api_key_label,
            "not set; export it before running ttsrun",
        )
        if exit_code == ExitCode.OK:
            exit_code = ExitCode.AUTH

    inactive_api_key = os.getenv(inactive_api_key_label, "").strip()
    if inactive_api_key:
        print_doctor_check(
            "info",
            inactive_api_key_label,
            f"set ({len(inactive_api_key)} chars, inactive provider)",
        )
    else:
        print_doctor_check(
            "info",
            inactive_api_key_label,
            "not set (inactive provider)",
        )

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


def handle_legacy_management_command(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
) -> int | None:
    if args.force and not args.init_config:
        parser.error("--force can only be used with --init-config.")

    if args.version:
        print(__version__)
        return ExitCode.OK

    if args.print_config_example:
        print_legacy_flag_warning("--print-config-example")
        print(json.dumps(example_config(), ensure_ascii=False, indent=2))
        return ExitCode.OK

    if args.print_config_path:
        print_legacy_flag_warning("--print-config-path")
        print(resolve_config_path(args.config))
        return ExitCode.OK

    if args.init_config:
        print_legacy_flag_warning("--init-config")
        path = write_example_config(args.config, overwrite=args.force)
        print(f"Wrote example config to {path}")
        return ExitCode.OK

    if args.doctor:
        print_legacy_flag_warning("--doctor")
        return run_doctor(args.config, provider_override=args.provider)

    return None


def run_config_command(argv: list[str]) -> int:
    parser = build_config_parser()
    args = parser.parse_args(argv)

    if args.config_command == "path":
        print(resolve_config_path(args.config))
        return ExitCode.OK

    if args.config_command == "show":
        config = load_config(args.config)
        print(
            json.dumps(
                serialize_config(config, include_metadata=True),
                ensure_ascii=False,
                indent=2,
            )
        )
        return ExitCode.OK

    if args.config_command == "init":
        path = write_example_config(args.config, overwrite=args.force)
        print(f"Wrote example config to {path}")
        return ExitCode.OK

    if args.config_command == "example":
        print(json.dumps(example_config(), ensure_ascii=False, indent=2))
        return ExitCode.OK

    parser.error("Unknown config command.")
    return ExitCode.USAGE


def run_doctor_command(argv: list[str]) -> int:
    parser = build_doctor_parser()
    args = parser.parse_args(argv)
    return run_doctor(args.config, provider_override=args.provider)


def run_batch_command(
    argv: list[str],
    prog: str = "ttsrun",
    show_commands: bool = True,
) -> int:
    parser = build_run_parser(prog=prog, show_commands=show_commands)
    args = parser.parse_args(argv)

    if args.force_output_dir and not args.output_dir:
        parser.error("--force-output-dir can only be used with --output-dir.")

    command_result = handle_legacy_management_command(parser, args)
    if command_result is not None:
        return int(command_result)

    config = load_config(args.config)
    provider_name = resolve_provider(args, config)
    validate_provider_options(parser, args, provider_name)
    source = resolve_input_source(parser, args)
    settings = resolve_settings(args, config, provider_name)
    request_settings = resolve_request_settings(args, config)
    output_root = (
        Path(args.output_root).expanduser() if args.output_root else config.output_root
    )
    candidate_output_dir = build_output_dir(
        source=source,
        output_root=output_root,
        explicit_output_dir=args.output_dir,
        job_name=args.name,
    )
    output_dir = prepare_output_dir(
        candidate_output_dir,
        explicit=bool(args.output_dir),
        overwrite=args.force_output_dir,
    )
    result = run_batch_job(
        source=source,
        output_dir=output_dir,
        settings=settings,
        request_settings=request_settings,
        api_key=get_api_key(provider_name),
        merge=args.merge,
        reporter=build_reporter(args),
        provider_name=provider_name,
    )
    if args.json_summary:
        print(json.dumps(result.manifest["summary"], ensure_ascii=False))
    if resolve_open_after_finish(args, config):
        try:
            open_output_dir(result.output_dir)
        except TTSBatchError as exc:
            print(f"Warning: {exc}", file=sys.stderr)
    return result.exit_code


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    try:
        if argv and argv[0] == "run":
            return run_batch_command(argv[1:], prog="ttsrun run", show_commands=False)
        if argv and argv[0] == "doctor":
            return run_doctor_command(argv[1:])
        if argv and argv[0] == "config":
            return run_config_command(argv[1:])
        return run_batch_command(argv)
    except (ConfigError, InputSourceError, TTSBatchError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return int(exit_code_for_error(exc))


def main_entry() -> None:
    raise SystemExit(main())
