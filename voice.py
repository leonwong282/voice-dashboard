import argparse
import csv
import json
import os
import random
import re
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib import error, request

API_URL = "https://api.minimaxi.com/v1/t2a_v2"
DEFAULT_MODEL = "speech-2.8-hd"
DEFAULT_LANGUAGE_BOOST = "Chinese,Yue"
DEFAULT_VOICE_ID = "clone_voice_can"
DEFAULT_SPEED = 1.2
DEFAULT_PITCH = 0
DEFAULT_FORMAT = "mp3"
DEFAULT_SAMPLE_RATE = 32000


@dataclass
class TTSItem:
    item_id: str
    text: str
    filename: Optional[str] = None
    model: Optional[str] = None
    voice_id: Optional[str] = None
    speed: Optional[float] = None
    pitch: Optional[float] = None
    language_boost: Optional[str] = None
    audio_format: Optional[str] = None
    sample_rate: Optional[int] = None


class BatchTTSRunner:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.api_key = os.getenv("MINIMAX_API_KEY") or os.getenv("api_key")
        if not args.dry_run and not self.api_key:
            raise ValueError("找不到 API 金鑰。請設定 MINIMAX_API_KEY（或舊的 api_key）環境變數。")

        self.outdir = Path(args.outdir)
        self.outdir.mkdir(parents=True, exist_ok=True)
        self.manifest_dir = Path(args.manifest_dir)
        self.manifest_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir = Path(args.log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self.run_id = ts
        self.manifest_path = self.manifest_dir / f"manifest_{self.run_id}.json"
        self.latest_manifest_path = self.manifest_dir / "latest_manifest.json"
        self.log_path = self.log_dir / f"run_{self.run_id}.json"

        self.manifest: Dict[str, Any] = self._init_manifest()
        if self.args.resume:
            self._load_latest_manifest_if_exists()

    def _init_manifest(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "input_file": self.args.input,
            "outdir": str(self.outdir),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "settings": {
                "default_model": self.args.default_model,
                "default_voice_id": self.args.default_voice_id,
                "default_speed": self.args.default_speed,
                "default_pitch": self.args.default_pitch,
                "default_language_boost": self.args.default_language_boost,
                "default_format": self.args.default_format,
                "default_sample_rate": self.args.default_sample_rate,
                "max_retries": self.args.max_retries,
                "retry_backoff": self.args.retry_backoff,
                "dry_run": self.args.dry_run,
            },
            "items": {},
        }

    def _load_latest_manifest_if_exists(self) -> None:
        if not self.latest_manifest_path.exists():
            print("ℹ️ --resume 啟用，但找不到 latest_manifest.json，將從頭開始。")
            return
        try:
            old_manifest = json.loads(self.latest_manifest_path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"⚠️ 無法讀取既有 manifest，將從頭開始：{exc}")
            return

        if old_manifest.get("input_file") != self.args.input:
            print("ℹ️ latest_manifest 的 input 與本次不同，將從頭開始。")
            return

        self.manifest["items"] = old_manifest.get("items", {})
        print(f"ℹ️ 已載入既有進度，共 {len(self.manifest['items'])} 筆。")

    def run(self) -> int:
        items = self._load_items(self.args.input)
        if not items:
            print("沒有可處理的文字內容。")
            return 1

        total = len(items)
        stats = {"total": total, "success": 0, "failed": 0, "skipped": 0}
        started = time.time()

        for idx, item in enumerate(items, 1):
            normalized = self._normalize_item(item, idx)
            existing = self.manifest["items"].get(normalized.item_id)
            if self.args.resume and existing and existing.get("status") == "success":
                print(f"[{idx}/{total}] ⏭️ skip {normalized.item_id} (已成功)")
                stats["skipped"] += 1
                continue

            output_filename = self._resolve_output_filename(normalized, idx)
            output_path = self.outdir / output_filename
            if output_path.exists() and not self.args.overwrite:
                print(f"[{idx}/{total}] ⏭️ skip {normalized.item_id} ({output_filename} 已存在)")
                self._record_item(normalized.item_id, "skipped", output_filename, "file_exists")
                stats["skipped"] += 1
                continue

            ok, err = self._process_single_item(normalized, output_path)
            if ok:
                stats["success"] += 1
            else:
                stats["failed"] += 1
                print(f"[{idx}/{total}] ❌ failed {normalized.item_id}: {err}")

            self._persist_manifest()

        duration = round(time.time() - started, 2)
        summary = {**stats, "duration_seconds": duration}
        print("\n=== Batch Summary ===")
        print(json.dumps(summary, ensure_ascii=False, indent=2))

        run_log = {
            "run_id": self.run_id,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "summary": summary,
            "manifest_path": str(self.manifest_path),
            "items": self.manifest["items"],
        }
        self.log_path.write_text(json.dumps(run_log, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"📝 log: {self.log_path}")
        return 0 if stats["failed"] == 0 else 2

    def _load_items(self, input_path: str) -> List[TTSItem]:
        path = Path(input_path)
        if not path.exists():
            raise FileNotFoundError(f"找不到輸入檔：{path}")

        ext = path.suffix.lower()
        if ext == ".csv":
            return self._load_csv(path)
        if ext == ".json":
            return self._load_json(path)
        if ext == ".txt":
            return self._load_txt(path)
        raise ValueError(f"不支援的輸入格式：{ext}，請使用 .csv / .json / .txt")

    def _load_csv(self, path: Path) -> List[TTSItem]:
        rows: List[TTSItem] = []
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader, 1):
                text = (row.get("text") or "").strip()
                if not text:
                    continue
                rows.append(
                    TTSItem(
                        item_id=(row.get("id") or f"row_{i}").strip(),
                        text=text,
                        filename=(row.get("filename") or "").strip() or None,
                        model=(row.get("model") or "").strip() or None,
                        voice_id=(row.get("voice_id") or "").strip() or None,
                        speed=self._to_float(row.get("speed")),
                        pitch=self._to_float(row.get("pitch")),
                        language_boost=(row.get("language_boost") or "").strip() or None,
                        audio_format=(row.get("format") or "").strip() or None,
                        sample_rate=self._to_int(row.get("sample_rate")),
                    )
                )
        return rows

    def _load_json(self, path: Path) -> List[TTSItem]:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("JSON 內容必須是陣列。")
        rows: List[TTSItem] = []
        for i, row in enumerate(data, 1):
            if not isinstance(row, dict):
                continue
            text = str(row.get("text", "")).strip()
            if not text:
                continue
            rows.append(
                TTSItem(
                    item_id=str(row.get("id") or f"row_{i}"),
                    text=text,
                    filename=(str(row.get("filename", "")).strip() or None),
                    model=(str(row.get("model", "")).strip() or None),
                    voice_id=(str(row.get("voice_id", "")).strip() or None),
                    speed=self._to_float(row.get("speed")),
                    pitch=self._to_float(row.get("pitch")),
                    language_boost=(str(row.get("language_boost", "")).strip() or None),
                    audio_format=(str(row.get("format", "")).strip() or None),
                    sample_rate=self._to_int(row.get("sample_rate")),
                )
            )
        return rows

    def _load_txt(self, path: Path) -> List[TTSItem]:
        items: List[TTSItem] = []
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            text = line.strip()
            if not text:
                continue
            items.append(TTSItem(item_id=f"line_{i}", text=text))
        return items

    def _normalize_item(self, item: TTSItem, index: int) -> TTSItem:
        item.item_id = self._sanitize_id(item.item_id or f"item_{index}")
        item.model = item.model or self.args.default_model
        item.voice_id = item.voice_id or self.args.default_voice_id
        item.speed = item.speed if item.speed is not None else self.args.default_speed
        item.pitch = item.pitch if item.pitch is not None else self.args.default_pitch
        item.language_boost = item.language_boost or self.args.default_language_boost
        item.audio_format = (item.audio_format or self.args.default_format).lower()
        item.sample_rate = item.sample_rate or self.args.default_sample_rate
        return item

    def _process_single_item(self, item: TTSItem, output_path: Path) -> Tuple[bool, Optional[str]]:
        if self.args.dry_run:
            print(f"[DRY-RUN] {item.item_id} -> {output_path.name}")
            self._record_item(item.item_id, "success", output_path.name, None, payload=asdict(item))
            return True, None

        payload: Dict[str, Any] = {
            "model": item.model,
            "text": item.text,
            "language_boost": item.language_boost,
            "voice_setting": {"voice_id": item.voice_id, "speed": item.speed, "pitch": item.pitch},
            "audio_setting": {"format": item.audio_format, "sample_rate": item.sample_rate},
        }

        for attempt in range(self.args.max_retries + 1):
            try:
                status, body = self._http_post_json(API_URL, payload)
                if status >= 400:
                    if self._is_retryable_status(status):
                        raise RuntimeError(f"HTTP {status}: {body[:500]}")
                    self._record_item(item.item_id, "failed", output_path.name, f"HTTP {status}: {body[:500]}", payload)
                    return False, f"HTTP {status}"

                data = json.loads(body)
                audio_hex = data.get("data", {}).get("audio")
                if not audio_hex:
                    raise RuntimeError("回應缺少 data.audio")

                tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
                tmp_path.write_bytes(bytes.fromhex(audio_hex))
                tmp_path.replace(output_path)
                print(f"✅ {item.item_id} -> {output_path.name}")
                self._record_item(item.item_id, "success", output_path.name, None, payload)
                return True, None
            except Exception as exc:
                if attempt >= self.args.max_retries:
                    self._record_item(item.item_id, "failed", output_path.name, str(exc), payload)
                    return False, str(exc)
                sleep_secs = self.args.retry_backoff * (2**attempt) + random.uniform(0, 0.5)
                print(f"⚠️ {item.item_id} 第 {attempt + 1} 次失敗：{exc}，{sleep_secs:.1f}s 後重試")
                time.sleep(sleep_secs)

        self._record_item(item.item_id, "failed", output_path.name, "unknown_error", payload)
        return False, "unknown_error"

    def _http_post_json(self, url: str, payload: Dict[str, Any]) -> Tuple[int, str]:
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            url,
            data=data,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with request.urlopen(req, timeout=self.args.timeout) as resp:
                return resp.getcode(), resp.read().decode("utf-8", errors="replace")
        except error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8", errors="replace")

    def _persist_manifest(self) -> None:
        text = json.dumps(self.manifest, ensure_ascii=False, indent=2)
        self.manifest_path.write_text(text, encoding="utf-8")
        self.latest_manifest_path.write_text(text, encoding="utf-8")

    def _record_item(
        self,
        item_id: str,
        status: str,
        output_file: str,
        error_msg: Optional[str],
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.manifest["items"][item_id] = {
            "status": status,
            "output": output_file,
            "error": error_msg,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }

    @staticmethod
    def _is_retryable_status(code: int) -> bool:
        return code == 429 or 500 <= code < 600

    @staticmethod
    def _to_float(value: Any) -> Optional[float]:
        if value in (None, ""):
            return None
        return float(value)

    @staticmethod
    def _to_int(value: Any) -> Optional[int]:
        if value in (None, ""):
            return None
        return int(value)

    def _resolve_output_filename(self, item: TTSItem, index: int) -> str:
        base = item.filename or f"{index:04d}_{item.item_id}"
        base = self._sanitize_id(base)
        ext = item.audio_format or self.args.default_format
        return base if base.lower().endswith(f".{ext}") else f"{base}.{ext}"

    @staticmethod
    def _sanitize_id(value: str) -> str:
        value = re.sub(r"[\\/:*?\"<>|\s]+", "_", value.strip())
        value = value.strip("._")
        return value or "item"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="批次 TTS 轉換工具（支援 CSV/TXT/JSON）")
    parser.add_argument("--input", required=True, help="輸入檔路徑（.csv/.json/.txt）")
    parser.add_argument("--outdir", default="outputs", help="輸出資料夾")
    parser.add_argument("--manifest-dir", default="manifests", help="manifest 輸出資料夾")
    parser.add_argument("--log-dir", default="logs", help="log 輸出資料夾")

    parser.add_argument("--default-model", default=DEFAULT_MODEL)
    parser.add_argument("--default-voice-id", default=DEFAULT_VOICE_ID)
    parser.add_argument("--default-speed", type=float, default=DEFAULT_SPEED)
    parser.add_argument("--default-pitch", type=float, default=DEFAULT_PITCH)
    parser.add_argument("--default-language-boost", default=DEFAULT_LANGUAGE_BOOST)
    parser.add_argument("--default-format", default=DEFAULT_FORMAT)
    parser.add_argument("--default-sample-rate", type=int, default=DEFAULT_SAMPLE_RATE)

    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--retry-backoff", type=float, default=2.0)
    parser.add_argument("--timeout", type=int, default=60)

    parser.add_argument("--resume", action="store_true", help="從 latest_manifest.json 續跑")
    parser.add_argument("--overwrite", action="store_true", help="覆蓋已存在音檔")
    parser.add_argument("--dry-run", action="store_true", help="只驗證流程，不呼叫 API")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    runner = BatchTTSRunner(args)
    return runner.run()


if __name__ == "__main__":
    raise SystemExit(main())
