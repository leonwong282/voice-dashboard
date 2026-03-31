# Batch TTS MVP

本工具將 MiniMax TTS API 包裝成批次命令列流程，讓你可直接餵入腳本檔，一次生成多段音檔。

## 功能
- 支援 `CSV / JSON / TXT` 批次輸入
- 批次呼叫 MiniMax TTS API
- 失敗重試（含退避）
- `--resume` 斷點續跑（依 `manifests/latest_manifest.json`）
- `logs/` 輸出執行報表

---

## 環境變數
優先讀取：
- `MINIMAX_API_KEY`
- 備援：`api_key`

建議只使用 `MINIMAX_API_KEY`，便於團隊一致管理。

---

## 快速開始
```bash
python voice.py --input examples/sample.csv --outdir outputs --dry-run
```

實際呼叫 API：
```bash
python voice.py --input examples/sample.csv --outdir outputs
```

---

## 命令列參數
### 必填參數
- `--input`：輸入檔路徑，僅支援 `.csv/.json/.txt`

### 常用參數
- `--outdir`：音檔輸出資料夾（預設 `outputs`）
- `--manifest-dir`：進度檔輸出資料夾（預設 `manifests`）
- `--log-dir`：執行紀錄輸出資料夾（預設 `logs`）
- `--resume`：從 `manifests/latest_manifest.json` 續跑
- `--overwrite`：覆蓋既有音檔
- `--dry-run`：只驗證流程，不呼叫 API

### TTS 預設參數（可被單筆覆蓋）
- `--default-model`（預設 `speech-2.8-hd`）
- `--default-voice-id`（預設 `clone_voice_can`）
- `--default-speed`（預設 `1.2`）
- `--default-pitch`（預設 `0`）
- `--default-language-boost`（預設 `Chinese,Yue`）
- `--default-format`（預設 `mp3`）
- `--default-sample-rate`（預設 `32000`）

### 穩定性參數
- `--max-retries`：最大重試次數（預設 `3`）
- `--retry-backoff`：重試退避基數秒數（預設 `2.0`）
- `--timeout`：每次 API 呼叫 timeout 秒數（預設 `60`）

---

## 批次輸入格式與要求（重點）

> 三種格式都會被轉成統一的「一筆一段文字」資料模型，再依序轉語音。

### 1) CSV（推薦）

#### 編碼與格式要求
- 檔案編碼：`UTF-8`（含 UTF-8 BOM 也支援）
- 第一列必須是欄位名稱（header）
- 欄位分隔符為逗號 `,`
- 多行文字請使用 CSV 引號規則（以 `"..."` 包裹）

#### 欄位定義
- 必填欄位
  - `text`：要轉語音的內容（空字串會被跳過）
- 可選欄位
  - `id`：此筆唯一識別（未提供時自動用 `row_N`）
  - `filename`：輸出檔名（不含副檔名亦可）
  - `model`
  - `voice_id`
  - `speed`（可轉成 float）
  - `pitch`（可轉成 float）
  - `language_boost`
  - `format`（例如 `mp3`）
  - `sample_rate`（可轉成 int）

#### 範例
```csv
id,text,filename,voice_id,speed,format
intro,大家好，歡迎來到今天的節目,intro,clone_voice_can,1.1,mp3
part1,第一段內容示範,,clone_voice_can,1.2,mp3
```

---

### 2) JSON（彈性最高）

#### 格式要求
- 頂層必須是陣列 `[]`
- 每個元素必須是物件 `{}`
- 物件至少要有 `text`（空字串會被跳過）

#### 支援欄位
與 CSV 相同：`id`, `text`, `filename`, `model`, `voice_id`, `speed`, `pitch`, `language_boost`, `format`, `sample_rate`

#### 範例
```json
[
  {
    "id": "intro",
    "text": "大家好，歡迎來到今天的節目",
    "filename": "intro",
    "voice_id": "clone_voice_can",
    "speed": 1.1,
    "format": "mp3"
  },
  {
    "id": "part1",
    "text": "第一段內容示範"
  }
]
```

---

### 3) TXT（最簡單）

#### 格式要求
- 純文字檔，建議 `UTF-8`
- 每一行代表一段文字
- 空行會忽略

#### 規則
- `id` 會自動生成為 `line_N`
- `filename` 會自動生成為 `0001_line_1.mp3` 這類形式
- 聲音參數一律取 CLI 預設值（因 TXT 無欄位可覆蓋）

#### 範例
```txt
大家好，這是第一段。

這是第二段，空行會自動忽略。
```

---

## 共同規則（CSV/JSON/TXT 都適用）

### 1) 跳過規則
- `text` 空白或空字串：跳過不處理
- `--resume` 啟用且該 `id` 在 manifest 中為 `success`：跳過
- 輸出檔已存在且未指定 `--overwrite`：跳過

### 2) 檔名處理
- 會清理檔名中的非法字元（如 `\\ / : * ? " < > |` 與空白）
- 若未帶副檔名，會自動補上 `.<format>`

### 3) 失敗重試
- `429` 或 `5xx` 視為可重試錯誤
- 採用指數退避（`retry_backoff * 2^attempt`）與隨機抖動

### 4) 輸出工件
- 音檔：`outdir/*.mp3`（或你指定格式）
- Manifest：`manifests/manifest_<timestamp>.json` + `manifests/latest_manifest.json`
- Run log：`logs/run_<timestamp>.json`

---

## 建議批次作業流程
1. 先用 `--dry-run` 驗證輸入格式與檔名規則
2. 正式執行批次轉換
3. 若中斷，使用 `--resume` 續跑
4. 查看 `logs/run_*.json` 與 manifest 追蹤失敗項目
