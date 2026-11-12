"""生成前试映（二）：把读本台词照镜表排成时间轴，配 16 宫格草图做成试映影片，量出实际片长。
2026-10-23 由原频道各片的 preview/assemble_read.py 改成通用版。读 preview/shots.json（格式见 make_storyboard.py 开头）：
  每镜 lines＝[{"text": "台词原文（念的字，不含说话者）", "caption": "字幕"}]；
  或旧做法 [{"wav": "台词音档（相对 shots.json）", "caption": "字幕"}]；两者都没有的只显示字幕（群众声、音效、字卡说明）。
⭐ 2026-10-23 起预设「文字读本」：台词由 H3 拿角色参考音自己念，读本不用先做 TTS。有 text 没 wav 的句子用字数估长度：
  试映画面停留＝字数 ÷ READ_CPS＋0.3 秒（照一般语速，给人看节奏）；
  建议 H3 镜长 h3_sec＝max(3, 该镜台词字数 ÷ H3_CPS＋H3_PAD)（每秒 3 字＋2 秒：H3 有时晚 1.5–2.1 秒才开口，再留反应尾巴；
  原频道 7 句实测全部在这个长度内念完，最紧的 13 字句算出 6.3 秒、实际念到 6.16 秒）。多出来的空白剪接时裁掉。
  字数＝中文字＋英数字，不含标点。
每镜长度＝max(镜表秒数 sec, 台词总长＋前 0.25＋每句后 0.3 秒)。草图格子用 storyboard_<k>_label.png（每 16 镜一张，依镜在
shots 里的顺序对应；改剧本删镜后要沿用旧格子，可在镜上写 "panel_index": 旧序号，从 0 起算）。
输出（同资料夹）：读本.wav（文字读本时是静音）、读本_timeline.json（每镜 dur、h3_sec）、读本试映.mp4（720×1280）、_frames/。
用法：python tools/assemble_read.py <片资料夹>/preview/shots.json"""
import json
import re
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fonts import font  # noqa: E402

SR = 24000
W, H = 720, 1280
PER_SHEET = 16
READ_CPS = 4.0                  # 文字读本：试映画面的一般语速（字／秒）
H3_CPS, H3_PAD, H3_MIN = 3.0, 2.0, 3.0   # 建议 H3 镜长＝字数 ÷ 3＋2 秒，最短 3 秒


def nchars(t):
    return len(re.findall(r"[一-鿿A-Za-z0-9]", t or ""))


def load(p):
    if not p.exists():
        return None
    a = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                       capture_output=True, check=True).stdout
    return np.frombuffer(a, np.int16).astype(np.float32) / 32768


def panel(here, i, n_total):
    k, j = i // PER_SHEET + 1, i % PER_SHEET
    lab = here / f"storyboard_{k}_label.png"
    if not lab.exists():
        return None
    nrows = (min(PER_SHEET, n_total - (k - 1) * PER_SHEET) + 3) // 4
    im = Image.open(lab).convert("RGB"); w, h = im.size
    raw = here / f"storyboard_{k}.png"
    g = np.asarray(Image.open(raw if raw.exists() else lab).convert("L")) > 235    # 用白色格线切（列高不一定等分）

    def cuts(frac, n):
        runs = []
        for x in (x for x, v in enumerate(frac) if v > 0.9):
            if runs and x == runs[-1][1] + 1:
                runs[-1][1] = x
            else:
                runs.append([x, x])
        edges = [0] + [x for a, b in runs for x in (a, b + 1)] + [n]
        return [(edges[t], edges[t + 1]) for t in range(0, len(edges), 2) if edges[t + 1] - edges[t] > 20]
    rows, cols = cuts(g.mean(1), h), cuts(g.mean(0), w)
    if len(rows) != nrows or len(cols) != 4:
        rows = [(int(h * t / nrows), int(h * (t + 1) / nrows)) for t in range(nrows)]
        cols = [(int(w * t / 4), int(w * (t + 1) / 4)) for t in range(4)]
    (y0, y1), (x0, x1) = rows[j // 4], cols[j % 4]
    return im.crop((x0, y0, x1, y1))


def frame(here, idx, n_total, sid, caps, end_card):
    bg = Image.new("RGB", (W, H), (12, 12, 16)); d = ImageDraw.Draw(bg)
    pn = panel(here, idx, n_total) if sid != "END" else None
    if pn:
        r = min((W - 40) / pn.width, 980 / pn.height); pn = pn.resize((int(pn.width * r), int(pn.height * r)), Image.LANCZOS)
        bg.paste(pn, ((W - pn.width) // 2, 60))
    elif sid == "END":
        d.text((W // 2, 520), end_card or "", font=ImageFont.truetype(font("jhbd"), 50), fill=(255, 214, 120), anchor="mm")
    d.text((24, 1070), sid, font=ImageFont.truetype(font("jhbd"), 36), fill=(120, 230, 255))
    y, f = 1120, ImageFont.truetype(font("jhbd"), 28)
    for c in caps:
        while c:
            seg, c = c[:23], c[23:]
            d.text((24, y), seg, font=f, fill=(240, 240, 240)); y += 38
    return bg


def main():
    sp = Path(sys.argv[1]).resolve(); here = sp.parent
    spec = json.loads(sp.read_text(encoding="utf-8"))
    shots = list(spec["shots"])
    if spec.get("end_card"):
        shots.append({"id": "END", "sec": 2, "lines": [{"caption": f"〔片尾〕{spec['end_card']}"}]})
    n_total = len(shots)
    vid = here / "_frames"; vid.mkdir(exist_ok=True)
    audio, tl, concat, t = [], [], [], 0.0
    for i, s in enumerate(shots):
        lines = s.get("lines", [])
        has_vo = any(x.get("wav") or x.get("text") for x in lines)
        seg = [np.zeros(int(0.25 * SR), np.float32)] if has_vo else []
        caps, missing = [], []
        spoken = sum(nchars(x.get("text")) for x in lines if x.get("text"))
        for x in lines:
            caps.append(x.get("caption", ""))
            if not x.get("wav"):
                if x.get("text"):          # 文字读本：照字数留时间（静音）
                    seg += [np.zeros(int((nchars(x["text"]) / READ_CPS + 0.3) * SR), np.float32)]
                continue
            a = load(here / x["wav"])
            if a is None:
                missing.append(x["wav"]); a = np.zeros(int(0.22 * SR * len(x.get("caption", ""))), np.float32)
            seg += [a, np.zeros(int(0.3 * SR), np.float32)]
        seg = np.concatenate(seg) if seg else np.zeros(0, np.float32)
        dur = max(float(s.get("sec", 2)), len(seg) / SR + 0.05)
        seg = np.concatenate([seg, np.zeros(int(dur * SR) - len(seg), np.float32)])
        audio.append(seg)
        h3_sec = max(H3_MIN, float(s.get("sec", 0)), spoken / H3_CPS + H3_PAD) if spoken else float(s.get("sec", 2))
        tl.append(dict(shot=s["id"], start=round(t, 2), dur=round(dur, 2), table_sec=s.get("sec"), chars=spoken,
                       h3_sec=round(h3_sec * 2 + 0.499) / 2, missing=missing))
        fp = vid / f"{s['id']}.png"
        frame(here, s.get("panel_index", i), n_total, s["id"], caps, spec.get("end_card")).save(fp)
        concat += [f"file '{fp.as_posix()}'", f"duration {dur:.3f}"]
        t += dur
    concat.append(f"file '{(vid / (shots[-1]['id'] + '.png')).as_posix()}'")
    y = np.concatenate(audio)
    with wave.open(str(here / "读本.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes())
    (here / "读本_timeline.json").write_text(json.dumps(dict(total=round(t, 2), shots=tl), ensure_ascii=False, indent=1), encoding="utf-8")
    (vid / "list.txt").write_text("\n".join(concat), encoding="utf-8")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(vid / "list.txt"), "-i", str(here / "读本.wav"),
                    "-vf", "fps=24,format=yuv420p", "-c:v", "libx264", "-crf", "23", "-c:a", "aac", "-b:a", "128k", "-shortest",
                    str(here / "读本试映.mp4")], check=True)
    longest = sorted(tl, key=lambda x: -x["dur"])[:3]
    print(f"总长 {t:.1f} 秒；缺音 {sum(len(x['missing']) for x in tl)} 句")
    print("最长三镜：", [(x["shot"], x["dur"]) for x in longest])
    print("超出镜表秒数：", [(x["shot"], x["table_sec"], x["dur"]) for x in tl if x["table_sec"] and x["dur"] > x["table_sec"] + 0.1])
    print("超过 12 秒（要拆）：", [x["shot"] for x in tl if x["dur"] > 12 or x["h3_sec"] > 12])
    print("建议 H3 镜长（台词字数 ÷ 3＋2 秒）：", [(x["shot"], x["h3_sec"]) for x in tl if x["chars"]])


if __name__ == "__main__":
    main()
