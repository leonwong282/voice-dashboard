# Batch TTS MVP

## 功能
- 支援 `CSV / JSON / TXT` 批次輸入
- 批次呼叫 MiniMax TTS API
- 失敗重試（含退避）
- `--resume` 斷點續跑（依 `manifests/latest_manifest.json`）
- `logs/` 輸出執行報表

## 環境變數
優先讀取：
- `MINIMAX_API_KEY`
- 備援：`api_key`

## 快速開始
```bash
python voice.py --input examples/sample.csv --outdir outputs --dry-run
```

實際呼叫 API：
```bash
python voice.py --input examples/sample.csv --outdir outputs
```

## 常用參數
- `--resume`：從上次進度續跑
- `--overwrite`：覆蓋已存在檔案
- `--max-retries 3`：最大重試次數
- `--retry-backoff 2`：退避基數秒數

## CSV 欄位
必要欄位：
- `text`

可選欄位：
- `id`
- `filename`
- `model`
- `voice_id`
- `speed`
- `pitch`
- `language_boost`
- `format`
- `sample_rate`
