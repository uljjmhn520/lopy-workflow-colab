"""选用：用 Kie.ai 的 Suno V6 API 生两位饶舌手的歌（没有 Kie 的话，把 out/songtext/ 的文字贴到 Suno 网页的 Custom 模式也一样）。
金钥：环境变数 KIE_API_KEY（或 KIE_KEY_FILE＝存金钥的文字档）。每次送件生 2 版，约 12 点（2026-10 价格）。
用法（先跑 make_battle.py songtext）：
  python kie_suno.py submit A [标签]   → out/suno/tasks_<标签>.json（标签预设 a1）
  python kie_suno.py poll <标签>       → out/suno/<歌名>_<标签>_v1.mp3、_v2.mp3
两人各生一首（同一首歌分两人＝同一个声音），挑好的复制到 song/A.mp3、song/B.mp3。
⚠ 歌词要跟 battle.json 一字不差（songs 阶段靠它对齐）；改了歌词就重跑 songtext 再送。"""
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
CFG = json.loads((HERE / "battle.json").read_text(encoding="utf-8"))
OUT = HERE / "out" / "suno"; OUT.mkdir(parents=True, exist_ok=True)
KEY = os.environ.get("KIE_API_KEY") or (Path(os.environ["KIE_KEY_FILE"]).read_text(encoding="utf-8").strip() if os.environ.get("KIE_KEY_FILE") else "")
API = "https://api.kie.ai/api/v1"


def req(path, data=None, params=""):
    if not KEY:
        sys.exit("设定环境变数 KIE_API_KEY（或 KIE_KEY_FILE）")
    r = urllib.request.Request(API + path + params, data=json.dumps(data).encode() if data is not None else None,
                               headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(r, timeout=60) as f:
        return json.loads(f.read().decode())


def submit(who, tag="a1"):
    r = CFG["rappers"][who]
    lyr = (HERE / "out" / "songtext" / f"suno_{who}_lyrics.txt").read_text(encoding="utf-8")
    style = os.environ.get("SUNO_STYLE") or r["suno_style"]     # 换人声时用环境变数覆盖风格
    if len(style) > 1000:
        sys.exit(f"风格 {len(style)} 字元，超过 Suno 上限 1000")
    inp = {"custom_mode": True, "instrumental": False, "model": "V6", "title": r.get("suno_title", f"{CFG['title']}_{r['name']}"),
           "lyrics": lyr, "style": style, "negative_tags": os.environ.get("SUNO_NEG") or r.get("suno_negative", ""), "vocal_gender": r.get("vocal_gender", "m"),
           "duration": int(r.get("suno_duration", 120))}
    res = req("/jobs/createTask", {"model": "ai-music-api/generate", "input": inp})
    print(res)
    if res.get("code") != 200:
        sys.exit(res)
    (OUT / f"tasks_{tag}.json").write_text(json.dumps({"taskId": res["data"]["taskId"], "who": who, "input": inp, "submitted": time.time()},
                                                      ensure_ascii=False, indent=1), encoding="utf-8")


def poll(tag):
    t = json.loads((OUT / f"tasks_{tag}.json").read_text(encoding="utf-8"))
    while True:
        d = req("/jobs/recordInfo", params=f"?taskId={t['taskId']}").get("data") or {}
        print(tag, d.get("state"), d.get("failMsg") or "", flush=True)
        if d.get("state") in ("success", "fail"):
            break
        time.sleep(20)
    t.update(state=d.get("state"), raw=d, files=[])
    if d.get("state") == "success":
        for i, x in enumerate(json.loads(d["resultJson"])["data"], 1):
            out = OUT / f"{t['input']['title']}_{tag}_v{i}{Path(x['audio_url']).suffix or '.mp3'}"
            r = urllib.request.Request(x["audio_url"], headers={"User-Agent": "Mozilla/5.0"})
            out.write_bytes(urllib.request.urlopen(r, timeout=300).read()); t["files"].append(out.name); print("saved", out, flush=True)
    (OUT / f"tasks_{tag}.json").write_text(json.dumps(t, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    {"submit": submit, "poll": poll}[sys.argv[1]](*sys.argv[2:])
