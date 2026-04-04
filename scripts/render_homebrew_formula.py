#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import requests

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    import tomli as tomllib


REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
TEMPLATE_PATH = REPO_ROOT / "packaging" / "homebrew" / "voice-dashboard.rb.template"


def load_project_metadata() -> dict:
    with PYPROJECT_PATH.open("rb") as fh:
        return tomllib.load(fh)["project"]


def canonicalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def venv_bin_dir(venv_path: Path) -> Path:
    candidate = venv_path / "bin"
    if candidate.exists():
        return candidate
    return venv_path / "Scripts"


def resolve_dependency_versions(python_executable: str, requirements: list[str]) -> list[tuple[str, str]]:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        venv_path = temp_path / "resolver-venv"
        report_path = temp_path / "report.json"

        subprocess.run([python_executable, "-m", "venv", str(venv_path)], check=True)
        pip_executable = venv_bin_dir(venv_path) / "pip"
        subprocess.run(
            [
                str(pip_executable),
                "install",
                "--dry-run",
                "--report",
                str(report_path),
                *requirements,
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        report = json.loads(report_path.read_text(encoding="utf-8"))
        resolved: dict[str, tuple[str, str]] = {}
        for item in report.get("install", []):
            metadata = item.get("metadata") or {}
            name = metadata.get("name")
            version = metadata.get("version")
            if not name or not version:
                continue
            resolved[canonicalize_name(name)] = (name, version)

        return [resolved[key] for key in sorted(resolved)]


def fetch_sdist_metadata(name: str, version: str) -> dict[str, str]:
    response = requests.get(
        f"https://pypi.org/pypi/{name}/{version}/json",
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()

    for file_info in payload.get("urls", []):
        if file_info.get("packagetype") != "sdist":
            continue
        return {
            "name": name,
            "version": version,
            "url": file_info["url"],
            "sha256": file_info["digests"]["sha256"],
        }

    raise RuntimeError(f"No sdist found on PyPI for {name}=={version}")


def resolve_source_distribution(
    *,
    project_name: str,
    package_version: str | None,
    source_url: str | None,
    source_sha256: str | None,
) -> dict[str, str]:
    if source_url and source_sha256:
        return {
            "name": project_name,
            "version": package_version or "unknown",
            "url": source_url,
            "sha256": source_sha256,
        }

    if package_version:
        return fetch_sdist_metadata(project_name, package_version)

    raise RuntimeError(
        "Provide either --source-url with --source-sha256, or --package-version."
    )


def render_resource_stanza(resource: dict[str, str]) -> str:
    return "\n".join(
        [
            f'  resource "{resource["name"]}" do',
            f'    url "{resource["url"]}"',
            f'    sha256 "{resource["sha256"]}"',
            "  end",
        ]
    )


def render_formula(
    *,
    source_url: str,
    source_sha256: str,
    resources: list[dict[str, str]],
) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    resource_block = "\n\n".join(render_resource_stanza(resource) for resource in resources)
    return (
        template.replace("__SOURCE_TARBALL_URL__", source_url)
        .replace("__SOURCE_TARBALL_SHA256__", source_sha256)
        .replace("__RESOURCE_STANZAS__", resource_block)
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a Homebrew formula from the repository template."
    )
    parser.add_argument(
        "--source-url",
        help="Published source tarball URL for the release.",
    )
    parser.add_argument(
        "--source-sha256",
        help="SHA256 digest for the published source tarball.",
    )
    parser.add_argument(
        "--package-version",
        help="Published package version. When set, the source sdist URL and SHA256 are fetched from PyPI.",
    )
    parser.add_argument(
        "--python-executable",
        default=sys.executable,
        help="Python used for dependency resolution. Defaults to the current interpreter.",
    )
    parser.add_argument(
        "--output",
        default="-",
        help="Write the rendered formula to this path. Defaults to stdout.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    project_metadata = load_project_metadata()
    project_name = project_metadata["name"]
    requirements = project_metadata.get("dependencies", [])
    source_distribution = resolve_source_distribution(
        project_name=project_name,
        package_version=args.package_version,
        source_url=args.source_url,
        source_sha256=args.source_sha256,
    )
    resolved_dependencies = resolve_dependency_versions(
        args.python_executable,
        requirements,
    )
    resources = [
        fetch_sdist_metadata(name, version) for name, version in resolved_dependencies
    ]
    rendered = render_formula(
        source_url=source_distribution["url"],
        source_sha256=source_distribution["sha256"],
        resources=resources,
    )

    if args.output == "-":
        print(rendered)
    else:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
        print(f"Wrote Homebrew formula to {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
