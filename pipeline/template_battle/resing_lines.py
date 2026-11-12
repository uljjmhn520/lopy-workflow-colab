"""局部重唱候选逐句比对：窗内每句人声、混音各听写一次（不给提示，拼音比），另外量窗外跟定稿的时间差，和句内有没有多唱（整窗听写）。
用法（Voice venv）：python resing_lines.py <A|B> <窗开始> <窗结束> <候选标签> …   输出 out/song/resing/lines_<标签>.md"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import librosa
import numpy as np
import opencc
from faster_whisper import WhisperModel
from pypinyin import lazy_pinyin

import make_battle as mb

HERE = Path(__file__).resolve().parent
sys.stdout.reconfigure(encoding="utf-8")
cc = opencc.OpenCC("s2twp")
who = sys.argv[1]; w0, w1 = float(sys.argv[2]), float(sys.argv[3]); tags = sys.argv[4:]
D = HERE / "out" / "song" / "resing"; D.mkdir(parents=True, exist_ok=True)
TITLE = {"A": "Bravo_Mozart", "B": "Bravo_Salieri"}[who]
AL = json.loads((HERE / "out" / "song" / f"align_{who}.json").read_text(encoding="utf-8"))
NOTCH = re.compile(r"[^\u4e00-\u9fff0-9]")
m = WhisperModel("large-v3", device="cpu", compute_type="int8", download_root=os.environ.get("AI_ROOT", "C:/AI") + "/Voice/models/whisper")
SR = 16000


def hear(x):
    seg, _ = m.transcribe(x, language="zh", vad_filter=False, condition_on_previous_text=False, temperature=0.0)
    return NOTCH.sub("", cc.convert("".join(s.text for s in seg)))


def miss(want, got):
    a, b = lazy_pinyin(want), lazy_pinyin(got)
    d = np.zeros((len(a) + 1, len(b) + 1), int)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            d[i + 1, j + 1] = d[i, j] + 1 if x == y else max(d[i, j + 1], d[i + 1, j])
    i, j = len(a), len(b); out = []
    while i and j:
        if a[i - 1] == b[j - 1]:
            i -= 1; j -= 1
        elif d[i - 1, j] >= d[i, j - 1]:
            i -= 1; out.append(want[i])
        else:
            j -= 1
    return "".join(out[::-1]) + ""


ref, _ = librosa.load(str(HERE / "song" / f"{who}.mp3"), sr=SR, mono=True)
rows = [r for r in AL["rows"] if r["start"] >= w0 - 0.3 and r["end"] <= w1 + 0.3]
out = [f"# {who} 窗 {w0}–{w1}"]
for t in tags:
    p = HERE / "out" / "suno" / f"{TITLE}_{t}.mp3"
    y, _ = librosa.load(str(p), sr=SR, mono=True)
    a = int((w0 - 12) * SR); b = int((w0 - 2) * SR)
    lag = (int(np.argmax(np.correlate(y[a:b][::8], ref[a:b][::8], "full"))) - (b - a) // 8 + 1) * 8 / SR * 1000
    a2 = int((w1 + 2) * SR); b2 = int((w1 + 12) * SR)
    lag2 = (int(np.argmax(np.correlate(y[a2:b2][::8], ref[a2:b2][::8], "full"))) - (b2 - a2) // 8 + 1) * 8 / SR * 1000
    clip = D / f"{t}_clip.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{w0 - 2}", "-to", f"{w1 + 2}", "-i", str(p), "-ar", "44100", str(clip)], check=True)
    voc, _inst = mb.sep_stems(clip, D / "sep")
    v, _ = librosa.load(str(voc), sr=SR, mono=True)
    out.append(f"\n## {t}  长度 {len(y) / SR:.1f}  窗前差 {lag:.0f} ms  窗后差 {lag2:.0f} ms")
    out.append("整窗人声：" + hear(v))
    out.append("整窗混音：" + hear(y[int((w0 - .2) * SR):int((w1 + .2) * SR)]))
    for r in rows:
        want = NOTCH.sub("", cc.convert(r["text"]))
        s0, s1 = r["start"] - 0.3, r["end"] + 0.35
        hv = hear(v[int((s0 - w0 + 2) * SR):int((s1 - w0 + 2) * SR)]); hm = hear(y[int(s0 * SR):int(s1 * SR)])
        mv, mm = miss(want, hv), miss(want, hm)
        out.append(f"- {r['start']:.1f} {want} ｜人声 {hv} ｜混音 {hm} ｜都缺 {''.join(c for c in mv if c in mm)}")
    print("\n".join(out[-len(rows) - 3:]), flush=True)
(D / f"lines_{tags[0]}.md").write_text("\n".join(out), encoding="utf-8")
