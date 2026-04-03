<a id="readme-top"></a>

<div align="center">

# 🎙️ voice-dashboard

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
  - Clipboard on macOS: `ttsrun --clipboard`
- Optional merge: only merges when `--merge` is provided.
- Output artifacts for traceability:
  - `manifest.json`
  - `errors.jsonl`

## 🚀 Quick Start

### 1) Set API key

```bash
export MINIMAX_API_KEY="your_new_key"
```

### 2) Install (editable mode)

```bash
python3 -m pip install -e .
```

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
- `--print-config-example`: print a sample config JSON.

## 📖 Documentation

- Full usage guide: [docs/USAGE.md](docs/USAGE.md)
- Development guide: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)
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
