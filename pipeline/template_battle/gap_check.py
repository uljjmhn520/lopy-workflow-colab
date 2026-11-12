"""人声破洞检查（〈向日葵之战〉使用者 2026-11-04「3:01 有跳拍」：盖句子时在「没」跟「电」中间留了 0.33 秒空洞，对齐分数、听写都没抓到）。
列出最终人声轨在「句子里」与「相邻两句之间」的无声段，和原唱人声比对：原唱这里也没声音的是换气，原唱有声、成品没有的就是接坏了（⚠）。
用法（Voice venv）：python gap_check.py <A|B> [最短秒数=0.18]"""
import json
import os
import sys
from pathlib import Path

import librosa
import numpy as np

HERE = Path(__file__).resolve().parent
who = sys.argv[1]
MIN = float(sys.argv[2]) if len(sys.argv) > 2 else 0.18
SR, HOP = 22050, 220
CFG = json.loads((HERE / "battle.json").read_text(encoding="utf-8"))
AL = json.loads((HERE / "out" / "song" / f"align_{who}.json").read_text(encoding="utf-8"))
SONG = HERE / CFG["rappers"][who]["song"]
FINAL = Path(os.environ.get("GAP_VOCALS") or SONG.with_name(SONG.stem + "_vocals.wav"))
ORIG = next((HERE / "out" / "song" / "sep").glob(f"{who}_(Vocals)*"))


def voiced(p):
    y = librosa.load(str(p), sr=SR, mono=True)[0]
    db = 20 * np.log10(librosa.feature.rms(y=y, frame_length=HOP * 2, hop_length=HOP)[0] + 1e-6)
    return db > max(db.max() - 42, -48)


fin, org = voiced(FINAL), voiced(ORIG)
t0, t1 = AL["rows"][0]["start"], AL.get("last_word_end", AL["rows"][-1]["end"])
fr = lambda t: int(t * SR / HOP)
bad = []
i = fr(t0)
while i < min(fr(t1), len(fin)):
    if fin[i]:
        i += 1
        continue
    j = i
    while j < len(fin) and not fin[j]:
        j += 1
    sec = (j - i) * HOP / SR
    if sec >= MIN:
        o = float(org[i:min(j, len(org))].mean())
        bad.append((i * HOP / SR, sec, o))
    i = j
for t, sec, o in bad:
    print(f"{'⚠' if o > 0.5 else ' '} 歌曲 {t:7.2f}  无声 {sec:.2f} 秒  原唱此处有声比例 {o:.0%}")
print(f"{FINAL.name}：{len(bad)} 段；⚠ {sum(o > 0.5 for *_, o in bad)} 段（原唱有声、成品没有，要回头听）")
