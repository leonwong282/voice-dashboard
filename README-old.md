# voice-dashboard

日常可用的 MiniMax 批量 TTS 命令列工具，主入口為 `ttsrun`。

## 核心能力

- 純文本空行分段，逐段生成 mp3
- 三種輸入來源（三選一）：
  - 檔案：`ttsrun <file.txt>`
  - 標準輸入：`ttsrun --stdin`
  - 剪貼簿（macOS）：`ttsrun --clipboard`
- 可選合併：僅加 `--merge` 時才合併為 `merged.mp3`
- 產出 `manifest.json` 與 `errors.jsonl`，便於追蹤結果

## 快速開始

### 1) 設定 API Key

```bash
export MINIMAX_API_KEY="你的新key"
```

### 2) 安裝（開發模式）

```bash
python3 -m pip install -e .
```

### 3) 執行

```bash
# 檔案輸入
ttsrun examples/sample.txt

# stdin 輸入
pbpaste | ttsrun --stdin

# 需要總音檔才加 --merge
pbpaste | ttsrun --stdin --merge
```

## 常用參數

- `--output-dir <dir>`：輸出到固定目錄
- `--output-root <dir>`：設定預設輸出根目錄
- `--name <label>`：自訂任務資料夾名稱尾碼
- `--merge`：全部成功後合併並刪除分段檔
- `--open`：完成後嘗試打開輸出目錄
- `--config <path>`：使用指定設定檔
- `--print-config-example`：輸出設定檔範例

## 文檔

完整使用說明請見：

- [USAGE.md](./USAGE.md)

