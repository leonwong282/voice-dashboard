"""
MiniMax 異步 TTS 完整版
真正流程：file_id → retrieve → download_url → 下載 .tar → 解壓 → 轉 SRT
"""

import requests
import json
import os
import time
import tarfile
import io
from datetime import timedelta

API_KEY = os.environ.get("MINIMAX_API_KEY")
BASE_URL = "https://api.minimaxi.com"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "content-type": "application/json",
}


# ── Step 2：建任務 ──────────────────────────────
def create_t2a_async_task(text: str) -> int:
    url = f"{BASE_URL}/v1/t2a_async_v2"
    payload = {
        "model": "speech-2.8-hd",
        "text": text,
        "language_boost": "auto",
        "voice_setting": {
            "voice_id": "male-qn-qingse",
            "speed": 1,
            "vol": 10,
            "pitch": 1,
        },
        "audio_setting": {
            "audio_sample_rate": 32000,
            "bitrate": 128000,
            "format": "mp3",
            "channel": 2,
        },
    }
    resp = requests.post(url, headers=HEADERS, data=json.dumps(payload))
    resp.raise_for_status()
    data = resp.json()
    print("建任務完成:", json.dumps(data, ensure_ascii=False, indent=2))
    return data["task_id"]


# ── Step 3：輪詢直到 Success ────────────────────
def wait_for_task(task_id: int, poll_interval: int = 5) -> int:
    url = f"{BASE_URL}/v1/query/t2a_async_query_v2?task_id={task_id}"
    while True:
        resp = requests.get(url, headers=HEADERS)
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status")
        print(f"  狀態: {status}")
        if status == "Success":
            return data["file_id"]
        elif status in ("Failed", "Expired"):
            raise RuntimeError(f"任務失敗: {data}")
        time.sleep(poll_interval)


# ── Step 4：取得 download_url ───────────────────
def get_download_url(file_id: int) -> str:
    url = f"{BASE_URL}/v1/files/retrieve?file_id={file_id}"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    data = resp.json()
    download_url = data["file"]["download_url"]
    print(f"download_url 取得成功")
    return download_url


# ── Step 5：下載 .tar 並解壓 ────────────────────
def download_and_extract_tar(download_url: str, output_dir: str = "."):
    """
    下載 .tar，解壓後回傳各文件 bytes
    tar 包內通常包含：
      - *.mp3         → 音訊
      - *subtitle*    → 字幕 JSON
      - *extra_info*  → 額外資訊 JSON
    """
    os.makedirs(output_dir, exist_ok=True)
    print("下載 .tar 中...")

    # 直接用 download_url 下載，不需要帶 Authorization（OSS 預簽名 URL）
    resp = requests.get(download_url)
    resp.raise_for_status()

    tar_bytes = io.BytesIO(resp.content)
    extracted = {}

    with tarfile.open(fileobj=tar_bytes, mode="r:*") as tar:
        for member in tar.getmembers():
            print(f"  解壓: {member.name}")
            content = tar.extractfile(member)
            if content is None:
                continue
            data = content.read()
            # 寫到 output_dir
            out_path = os.path.join(output_dir, os.path.basename(member.name))
            with open(out_path, "wb") as f:
                f.write(data)
            extracted[member.name] = out_path

    return extracted


# ── Step 6：字幕 JSON → SRT ─────────────────────
def ms_to_srt_time(ms: float) -> str:
    seconds = ms / 1000.0
    total = int(seconds)
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    millis = int((seconds - total) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{millis:03d}"


def subtitle_json_to_srt(subtitle_path: str, srt_path: str):
    with open(subtitle_path, "r", encoding="utf-8") as f:
        items = json.load(f)

    # 若頂層是 dict，往下找 list
    if isinstance(items, dict):
        for key in ("subtitles", "sentences", "data", "items"):
            if key in items and isinstance(items[key], list):
                items = items[key]
                break

    lines = []
    for idx, seg in enumerate(items, start=1):
        # ✅ 實際欄位是 time_begin / time_end（毫秒）
        start = ms_to_srt_time(seg["time_begin"])
        end   = ms_to_srt_time(seg["time_end"])
        text  = seg["text"].strip()
        lines.append(f"{idx}\n{start} --> {end}\n{text}\n")

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"SRT 已寫入 {srt_path}，共 {len(items)} 句")


# ── 主流程 ──────────────────────────────────────
if __name__ == "__main__":
    SCRIPT = "今天我們來介紹 MiniMax 異步語音合成的使用方式。這個接口支援最多十萬字符的長文本輸入，非常適合影片腳本或有聲書的生成。"
    OUTPUT_DIR = "./tts_output"

    # Step 2
    task_id = create_t2a_async_task(SCRIPT)

    # Step 3
    print("輪詢任務狀態...")
    file_id = wait_for_task(task_id)
    print(f"完成！file_id = {file_id}")

    # Step 4
    download_url = get_download_url(file_id)

    # Step 5：下載 .tar 並解壓到 OUTPUT_DIR
    extracted = download_and_extract_tar(download_url, output_dir=OUTPUT_DIR)
    print("\n解壓完成，文件清單：")
    for name, path in extracted.items():
        print(f"  {name} → {path}")

    # Step 6：找到字幕文件並轉 SRT
    subtitle_path = None
    for name, path in extracted.items():
        if "titles" in name.lower() or name.endswith(".json"):
            subtitle_path = path
            break

    if subtitle_path:
        subtitle_json_to_srt(subtitle_path, os.path.join(OUTPUT_DIR, "subtitle.srt"))
    else:
        print("⚠️ 找不到字幕文件，請手動查看 OUTPUT_DIR 裡的文件")