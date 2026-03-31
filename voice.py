import requests, json, os

api_key = os.getenv("api_key")
print(api_key)

res = requests.post(
    "https://api.minimaxi.com/v1/t2a_v2",
    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    json={
        "model": "speech-2.8-hd",
        "text": "「門票幾錢？旺季——即係 4 月到 10 月——成人 60 蚊，淡季 40 蚊。珍寶館同鐘錶館各加 10 蚊，買聯票最抵：旺季 80、淡季 60，老人半價，三個館一次睇晒！」",
        "language_boost": "Chinese,Yue",
        "voice_setting": {"voice_id": "clone_voice_can", "speed": 1.2, "pitch": 0},
        "audio_setting": {"format": "mp3", "sample_rate": 32000},
    },
)

data = res.json()
print(data)  # 先看完整 response

# 解碼並存 MP3
audio_hex = data["data"]["audio"]
with open("0.mp3", "wb") as f:
    f.write(bytes.fromhex(audio_hex))

print("✅ output.mp3 已生成")
