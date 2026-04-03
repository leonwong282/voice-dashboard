<a id="readme-top"></a>

<div align="center">

# 🎙️ voice-dashboard

> 日常可用的 MiniMax 批量文字轉語音（TTS）命令列工具。

![Version](https://img.shields.io/badge/Version-0.1.0-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-GPL--3.0-red?style=for-the-badge)
![CLI](https://img.shields.io/badge/CLI-ttsrun-green?style=for-the-badge)

[🌍 English](README.md) | [🇹🇼 繁體中文](README.zh-TW.md)

[核心能力](#-核心能力) • [快速開始](#-快速開始) • [常用參數](#-常用參數) • [文件](#-文件)

</div>

## ✨ 核心能力

- 純文本以空行分段，逐段產生 MP3。
- 三種輸入來源（三選一）：
  - 檔案：`ttsrun <file.txt>`
  - 標準輸入：`ttsrun --stdin`
  - 剪貼簿（支援的系統上）：`ttsrun --clipboard`
- 可選合併：只有加上 `--merge` 才會合併為單一檔案。
- 為自動化與腳本提供輸出控制：
  - `--quiet`
  - `--verbose`
  - `--json-summary`
- 產出追蹤檔案：
  - `manifest.json`
  - `errors.jsonl`

## 🚀 快速開始

### 1) 設定 API Key

```bash
export MINIMAX_API_KEY="你的新 key"
```

### 2) 安裝

一般本地使用原始碼時：

```bash
python3 -m pip install .
```

如果是要參與開發，請改看開發指南並使用 editable install。

### 3) 執行

```bash
# 檔案輸入
ttsrun examples/sample.txt

# stdin 輸入
pbpaste | ttsrun --stdin

# 需要總音檔時才加 --merge
pbpaste | ttsrun --stdin --merge
```

## ⚙️ 常用參數

- `--output-dir <dir>`：輸出到固定目錄。
- `--output-root <dir>`：設定預設輸出根目錄。
- `--name <label>`：自訂任務資料夾尾碼。
- `--merge`：全部成功後合併，並刪除分段檔。
- `--open`：完成後嘗試打開輸出目錄。
- `--config <path>`：使用指定設定檔。
- `--version`：輸出目前 CLI 版本。
- `--doctor`：檢查設定檔、API key 與可選依賴。
- `--print-config-path`：輸出實際設定檔路徑。
- `--print-config-example`：輸出設定檔範例。
- `--init-config`：寫入一份設定檔範例。
- `--force`：搭配 `--init-config` 覆寫既有設定檔。
- `--quiet` / `--verbose`：控制 stderr 上的進度輸出。
- `--json-summary`：以 JSON 輸出最終摘要。

## 📖 文件

- 完整使用說明（英文）：[docs/USAGE.md](docs/USAGE.md)
- 開發指南（英文）：[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)
- 產品化路線圖：[docs/ROADMAP.md](docs/ROADMAP.md)

<p align="right">(<a href="#readme-top">回到頂部</a>)</p>

## 📄 授權條款

本專案採用 GPL-3.0 授權條款 - 詳情請見 [LICENSE](LICENSE)。

## 👥 作者

**Leon Wong** - [leonwong282](https://github.com/leonwong282)

## 🙏 致謝

- [Best-README-Template](https://github.com/othneildrew/Best-README-Template)
- [Shields.io](https://shields.io/)
- [MiniMax](https://www.minimaxi.com/)

## 📞 支援

- 📝 [開啟 issue](https://github.com/leonwong282/voice-dashboard/issues/new)
- 💬 [開始討論](https://github.com/leonwong282/voice-dashboard/discussions)

---

<div align="center">

**⭐ 如果這個儲存庫對你有幫助，歡迎給一顆星！**

由 [Leon](https://github.com/leonwong282) 用 ❤️ 製作

</div>
