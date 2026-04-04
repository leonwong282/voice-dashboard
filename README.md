<a id="readme-top"></a>

<div align="center">

# 🎙️ Voice Dashboard

> A practical MiniMax batch Text-to-Speech CLI for daily workflows.

![Version](https://img.shields.io/badge/Version-0.1.0-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-GPL--3.0-red?style=for-the-badge)
![CLI](https://img.shields.io/badge/CLI-ttsrun-green?style=for-the-badge)

[🌍 English](README.md) | [🇹🇼 繁體中文](README.zh-TW.md)

[Features](#-features) • [Quick Start](#-quick-start) • [Common Options](#-common-options) • [Documentation](#-documentation)

</div>

## ✨ Features

- Plain-text paragraph splitting by empty lines, generating one MP3 per segment.
- Three input sources (choose one):
  - File path: `ttsrun <file.txt>`
  - Standard input: `ttsrun --stdin`
  - Clipboard on supported systems: `ttsrun --clipboard`
- Optional merge: only merges when `--merge` is provided.
- Output control for automation and scripting:
  - `--quiet`
  - `--verbose`
  - `--json-summary`
- Output artifacts for traceability:
  - `manifest.json`
  - `errors.jsonl`

## 🚀 Quick Start

### 1) Set API key

```bash
export MINIMAX_API_KEY="your_new_key"
```

### 2) Install

For regular local use from source:

```bash
python3 -m pip install .
```

Once the package is published to PyPI, prefer `pipx` for CLI-style installation:

```bash
pipx install voice-dashboard
```

If you explicitly want the package in an existing Python environment:

```bash
python3 -m pip install voice-dashboard
```

Homebrew support is planned but not published yet. The intended path is documented in `docs/HOMEBREW.md`.

For contributor setup, use the development guide and editable install instead.

### 3) Run

```bash
# File input
ttsrun examples/sample.txt

# Stdin input
pbpaste | ttsrun --stdin

# Merge only when you need a combined output
pbpaste | ttsrun --stdin --merge
```

## ⚙️ Common Options

- `--output-dir <dir>`: write outputs to a fixed directory.
- `--output-root <dir>`: set the default output root.
- `--name <label>`: customize job folder suffix.
- `--merge`: merge all successful segments and remove segment files.
- `--open`: open output directory after completion.
- `--config <path>`: use a specific config file.
- `--version`: print the installed CLI version.
- `doctor`: inspect config, API key, and optional dependencies.
- `config path`: print the resolved config path.
- `config show`: print the effective config as JSON.
- `config example`: print a sample config JSON.
- `config init`: write an example config file.
- `--quiet` / `--verbose`: control progress output on stderr.
- `--json-summary`: print the final manifest summary as JSON.

Preferred management commands:

```bash
ttsrun doctor
ttsrun config path
ttsrun config show
ttsrun config init
```

`ttsrun run <input_path>` is also supported as an explicit batch subcommand. The older management flags remain available as a deprecated compatibility layer.

## 📖 Documentation

- Full usage guide: [docs/USAGE.md](docs/USAGE.md)
- Development guide: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)
- Homebrew guide: [docs/HOMEBREW.md](docs/HOMEBREW.md)
- Release guide: [docs/RELEASING.md](docs/RELEASING.md)
- Product roadmap: [docs/ROADMAP.md](docs/ROADMAP.md)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## 📄 License

This project is licensed under the GPL-3.0 License - see the [LICENSE](LICENSE) file for details.

## 👥 Author

**Leon Wong** - [leonwong282](https://github.com/leonwong282)

## 🙏 Acknowledgments

- [Best-README-Template](https://github.com/othneildrew/Best-README-Template)
- [Shields.io](https://shields.io/)
- [MiniMax](https://www.minimaxi.com/)

## 📞 Support

- 📝 [Open an issue](https://github.com/leonwong282/voice-dashboard/issues/new)
- 💬 [Start a discussion](https://github.com/leonwong282/voice-dashboard/discussions)

---

<div align="center">

**⭐ Star this repository if it helped you!**

Made with ❤️ by [Leon](https://github.com/leonwong282)

</div>
