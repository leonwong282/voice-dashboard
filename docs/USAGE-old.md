# ttsrun 使用文檔

本文檔說明如何使用目前專案內的 `ttsrun` 工作流完成日常批量 TTS 轉換。

## 1. 功能概覽

`ttsrun` 支持：

- 三種輸入來源（三選一）：
  - 文字檔路徑（位置參數）
  - `--stdin`（標準輸入）
  - `--clipboard`（macOS `pbpaste`）
- 純文本空行分段（每段輸出一個 mp3）
- `--merge` 可選合併（不加參數時預設不合併）
- `manifest.json` + `errors.jsonl` 產出
- 可透過設定檔保存預設參數

## 2. 前置條件

- Python 3.10+
- 環境變數 `MINIMAX_API_KEY`
- 若要使用 `--merge`，系統需安裝 `ffmpeg`
- 若要使用 `--clipboard`，需在 macOS 環境可用 `pbpaste`

設定 API Key（macOS/Linux）：

```bash
export MINIMAX_API_KEY="你的新key"
```

> 提醒：舊版硬編碼 key 如已暴露，請先作廢並更換。

## 3. 安裝與入口

專案已提供 `console_scripts`，命令名稱為 `ttsrun`。

### 3.1 開發模式安裝（推薦）

在專案根目錄執行：

```bash
python3 -m pip install -e .
```

安裝成功後即可在任意目錄使用：

```bash
ttsrun --help
```

### 3.2 直接腳本入口

若你暫時不使用全域命令，也可以：

```bash
python3 voice.py --help
```

`voice.py` 目前是薄封裝入口，實際邏輯仍走 `voice_dashboard.cli`。

## 4. 最常用工作流

## 4.1 用文字檔輸入（最穩定）

```bash
ttsrun examples/sample.txt
```

## 4.2 用剪貼簿輸入（macOS）

```bash
ttsrun --clipboard
```

## 4.3 用管道輸入（stdin）

```bash
pbpaste | ttsrun --stdin
```

## 4.4 需要總音檔時才合併

```bash
ttsrun examples/sample.txt --merge
```

- 不加 `--merge`：保留 `0001.mp3`、`0002.mp3` ...
- 加 `--merge`：全部成功後生成 `merged.mp3`，並刪除本次分段檔

## 5. 輸出規則

### 5.1 預設輸出目錄

若未指定 `--output-dir`，會自動生成：

```text
<output_root>/<YYYY-MM-DD>/<YYYYMMDD-HHMMSS>-<label>/
```

其中：
- `output_root` 來自配置（預設 `~/Documents/tts-output`）
- `label` 預設取輸入來源標識（或 `--name`）

### 5.2 固定輸出到指定目錄

```bash
ttsrun examples/sample.txt --output-dir outputs/demo
```

### 5.3 產出文件

每次執行至少會有：

- `manifest.json`：任務摘要、參數、逐段結果
- `errors.jsonl`：僅記錄失敗段
- `0001.mp3` 等分段音檔（未合併）或 `merged.mp3`（合併成功）

## 6. 配置檔

預設配置路徑：

```text
~/.voice-dashboard.json
```

輸出配置範例：

```bash
ttsrun --print-config-example
```

可把輸出內容保存為 `~/.voice-dashboard.json` 後按需調整。例如：

```json
{
  "defaults": {
    "voice_id": "clone_voice_can",
    "speed": 1.2,
    "pitch": 0,
    "language_boost": "Chinese,Yue",
    "model": "speech-2.8-hd",
    "sample_rate": 32000,
    "format": "mp3",
    "output_root": "~/Documents/tts-output",
    "open_after_finish": false
  }
}
```

也可指定自定配置路徑：

```bash
ttsrun examples/sample.txt --config /path/to/config.json
```

## 7. 常用參數速查

- 輸入來源（三選一）：
  - `ttsrun <input_path>`
  - `ttsrun --stdin`
  - `ttsrun --clipboard`
- 輸出控制：
  - `--output-dir <dir>`
  - `--output-root <dir>`
  - `--name <job-name>`
- 語音參數：
  - `--voice-id`
  - `--speed`
  - `--pitch`（整數）
  - `--language-boost`
  - `--model`
  - `--sample-rate`
  - `--format mp3`
- 流程開關：
  - `--merge`
  - `--open`

## 8. 失敗處理與退出碼

- 只要任一段失敗，整體退出碼為非 0，但已成功段會保留。
- `--merge` 模式下：
  - 若 `ffmpeg` 不可用、合併失敗、或清理失敗，退出碼為非 0。
  - 合併失敗時分段檔不刪除，便於排查。

## 9. 每日高頻建議命令

如果你的日常是「複製文案 -> 出音檔」，推薦：

```bash
pbpaste | ttsrun --stdin --merge
```

若希望完成後自動打開輸出資料夾：

```bash
pbpaste | ttsrun --stdin --merge --open
```
