#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def venv_bin_dir(venv_path: Path) -> Path:
    candidate = venv_path / "bin"
    if candidate.exists():
        return candidate
    return venv_path / "Scripts"


def run_command(
    command: list[str],
    *,
    env: dict[str, str] | None = None,
) -> None:
    subprocess.run(command, check=True, env=env)


def verify_ttsrun(binary_path: Path) -> None:
    env = os.environ.copy()
    env["MINIMAX_API_KEY"] = "smoke-test-key"
    run_command([str(binary_path), "--help"], env=env)
    run_command([str(binary_path), "--version"], env=env)
    run_command([str(binary_path), "doctor"], env=env)
    run_command([str(binary_path), "config", "path"], env=env)
    run_command([str(binary_path), "config", "example"], env=env)


def verify_with_pip(package_spec: str, python_executable: str) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        venv_path = temp_path / "pip-venv"
        run_command([python_executable, "-m", "venv", str(venv_path)])
        bin_dir = venv_bin_dir(venv_path)
        run_command([str(bin_dir / "python"), "-m", "pip", "install", "--upgrade", "pip"])
        run_command([str(bin_dir / "python"), "-m", "pip", "install", package_spec])
        verify_ttsrun(bin_dir / "ttsrun")


def verify_with_pipx(package_spec: str, python_executable: str) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        host_venv = temp_path / "pipx-host"
        run_command([python_executable, "-m", "venv", str(host_venv)])
        host_bin = venv_bin_dir(host_venv)
        host_python = host_bin / "python"
        run_command([str(host_python), "-m", "pip", "install", "--upgrade", "pip"])
        run_command([str(host_python), "-m", "pip", "install", "pipx"])

        pipx_home = temp_path / "pipx-home"
        pipx_bin_dir = temp_path / "pipx-bin"
        env = os.environ.copy()
        env["PIPX_HOME"] = str(pipx_home)
        env["PIPX_BIN_DIR"] = str(pipx_bin_dir)

        run_command(
            [str(host_python), "-m", "pipx", "install", package_spec],
            env=env,
        )
        verify_ttsrun(pipx_bin_dir / "ttsrun")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify that a published package spec installs and runs via pip and pipx."
    )
    parser.add_argument(
        "--package-spec",
        required=True,
        help="Package spec to install, for example voice-dashboard==0.4.0 or dist/*.whl.",
    )
    parser.add_argument(
        "--python-executable",
        default=sys.executable,
        help="Python interpreter used to create the test environments.",
    )
    parser.add_argument(
        "--skip-pipx",
        action="store_true",
        help="Skip pipx verification.",
    )
    parser.add_argument(
        "--skip-pip",
        action="store_true",
        help="Skip plain pip verification.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    package_spec = args.package_spec

    if "*" in package_spec:
        matches = sorted(Path().glob(package_spec))
        if len(matches) != 1:
            raise SystemExit(f"Expected exactly one match for package spec glob: {package_spec}")
        package_spec = str(matches[0].resolve())
    elif Path(package_spec).exists():
        package_spec = str(Path(package_spec).resolve())

    if not args.skip_pip:
        print(f"Verifying pip install path for {package_spec}")
        verify_with_pip(package_spec, args.python_executable)

    if not args.skip_pipx:
        print(f"Verifying pipx install path for {package_spec}")
        verify_with_pipx(package_spec, args.python_executable)

    print("Public install verification completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
