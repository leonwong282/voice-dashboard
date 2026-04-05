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
    payload = { ... }  # 不變

    resp = requests.post(url, headers=HEADERS, data=json.dumps(payload))
    resp.raise_for_status()
    data = resp.json()
    print("建任務完成:", json.dumps(data, ensure_ascii=False, indent=2))

    # ✅ 加這個，失敗立刻 raise 不繼續跑
    if data["base_resp"]["status_code"] != 0:
        raise RuntimeError(f"建任務失敗 [{data['base_resp']['status_code']}]: {data['base_resp']['status_msg']}")

    return data["task_id"]


# ── Step 3：輪詢直到 Success ────────────────────
def wait_for_task(task_id: int, poll_interval: int = 5) -> int:
    url = f"{BASE_URL}/v1/query/t2a_async_query_v2?task_id={task_id}"
    while True:
        resp = requests.get(url, headers=HEADERS)
        resp.raise_for_status()
        data = resp.json()

        # ✅ 加這個，query 本身失敗也要 raise
        if data["base_resp"]["status_code"] != 0:
            raise RuntimeError(f"Query 失敗 [{data['base_resp']['status_code']}]: {data['base_resp']['status_msg']}")

        status = data.get("status", "")
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
    SCRIPT = "北京有個地方，第一任主人係清朝第一大貪官和珅，身家等於國庫十五年收入。呢座六萬平米嘅超級王府，到底收埋咗啲乜？呢度就係恭王府，中國現存最大、保存最完整嘅清代王府，占地六萬平方米。歷經三位主人：先係權臣和珅、後係慶僖親王永璘、最後係主導洋務運動嘅恭親王奕訢。所以先有嗰句：一座恭王府，半部清代史。府邸分東中西三路。中路嘅銀安殿係王府正殿，綠色琉璃瓦頂，只有重大典禮先會開門。西路最誇張，有間錫晉齋，又叫楠木殿。和珅當年膽大包天，仿紫禁城寧壽宮嘅規格嚟起，入面全部用金絲楠木雕成，三面做仙樓——大屋裡面套細屋，呢個可係皇帝先用得嘅規制。結果呢個就變咗佢二十大罪之一。行到最後面，有條長一百五十六米嘅後罩樓，八十八扇什錦窗，每扇都唔同款，一共一百零八間房。傳說和珅用唔同窗戶形狀對應唔同嘅收藏品，簡直係一個超大型密碼保險庫。穿過府邸就到花園——萃錦園。呢度有恭王府最出名嘅三絕一寶。第一絕，西洋門。漢白玉石拱門，仿圓明園大法海建造，門額外刻「靜含太古」、內刻「秀挹恆春」，係恭親王刻意引入西方建築嘅象徵，北京皇家園林入面好罕見。第二絕，大戲樓。全國保存最完好嘅清代室內戲樓之一，可以坐到二百人，頂部有通風換氣設計，到依家都仲有傳統戲曲演出。第三絕同一寶合埋講——滴翠岩。太湖石堆疊嘅假山，山頂有邀月台，而山肚入面，就收埋咗恭王府最大嘅寶貝，就係呢塊——天下第一福！康熙皇帝親筆寫嘅福字碑，收埋喺滴翠岩下面嘅秘云洞入面，藏咗超過二百年。呢個福字有幾特別？佢可以拆解成「多子、多才、多田、多壽、多福」五福合一，右半邊更加係王羲之蘭亭序入面個「壽」字寫法——歷代墨寶入面唯一福壽合一嘅字。碑頂仲蓋咗康熙御璽，所以佢亦都係中國唯一一個唔可以倒掛嘅福字。一九六二年周恩來總理視察恭王府，下令掘開封閉咗二百幾年嘅秘云洞，呢塊碑先至重見天日，親命名為「中華第一福」。去到嗰度記得排隊入洞摸一摸，沾沾福氣！實用信息：門票四十蚊，提前十天網上預約，週一閉館。搭地鐵六號線北海北站，A口出行十分鐘就到。建議遊覽兩到三個鐘。行完仲可以行五分鐘到什剎海，繼續嘆湖畔胡同。恭王府，一座王府半部清史，值得你花半日慢慢行。覺得有用就畀個關注，下期帶你遊北京更多隱藏景點！"
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