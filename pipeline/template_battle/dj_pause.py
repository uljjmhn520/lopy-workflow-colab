"""DJ 口白加停顿：Ming 念得一口气到底，重点句（「这题，我不答」）后面要留白才有重量。
在指定字后面插静音，并把 out/voice/ming/dj_align.json 的时间一起往后推。原档留 dj_<key>_orig.wav（之后重跑都从原档算）。
用法（Voice venv）：python dj_pause.py verdict 下毒=0.3 是谁=0.55 你赢=1.2
⚠ 切点一律用 dj_tail_check.tail_end（句尾真正结束的地方）：〈Bravo 之战〉v5 以前照对齐器的字尾切，字尾报早 0.1–0.3 秒，
每句最后一个字被砍、尾巴被推到停顿后面，使用者听出「DJ 讲话的尾句都断掉」（2026-11-08）。插完会自动跑句尾检查。
注意：插停顿会改变后面每个字的时间，DJ 有对嘴的镜要在生成影片之前插。"""
import json
import sys
import shutil
from pathlib import Path

import numpy as np
import soundfile as sf

from dj_tail_check import hard_cuts, tail_end

M = Path(__file__).resolve().parent / "out" / "voice" / "ming"
if len(sys.argv) < 3:
    sys.exit(__doc__)
KEY = sys.argv[1]
AFTER = {a.split("=")[0]: float(a.split("=")[1]) for a in sys.argv[2:]}
src, orig = M / f"dj_{KEY}.wav", M / f"dj_{KEY}_orig.wav"
if not orig.exists():
    shutil.copy(src, orig)
al_p, al_o = M / "dj_align.json", M / "dj_align_orig.json"
if not al_o.exists():
    shutil.copy(al_p, al_o)
x, sr = sf.read(str(orig), dtype="float32", always_2d=True)
al = json.loads(al_o.read_text(encoding="utf-8"))
words = [w for w in al[KEY] if w[0].strip()]
txt = "".join(w[0] for w in words)
cuts = []
for phrase, sec in AFTER.items():
    pos = txt.index(phrase) + len(phrase)
    n = 0
    for w in words:
        n += len(w[0])
        if n >= pos:
            cuts.append((w[2], sec, w[0])); break
cuts.sort()
parts, last, new, shift = [], 0, [], 0.0
for t, sec, w in cuts:
    # 切在句尾真正结束的地方（v6 修：对齐器的字尾常早 0.1–0.3 秒，照它切会砍掉最后一个字、尾巴被推到停顿后面）
    c = int(tail_end(x, sr, t, limit=min(.5, sec - .08)) * sr)
    parts += [x[last:c], np.zeros((int(sec * sr), x.shape[1]), "float32")]; last = c
    print(w, round(t, 2), "+", sec)
parts.append(x[last:])
sf.write(str(src), np.concatenate(parts), sr, subtype="PCM_16")
for w in al[KEY]:
    add = sum(sec for t, sec, _ in cuts if w[1] >= t - .02)
    new.append([w[0], round(w[1] + add, 2), round(w[2] + add, 2)])
al[KEY] = new
al_p.write_text(json.dumps(al, ensure_ascii=False, indent=0), encoding="utf-8")
print("长度", round(len(x) / sr, 2), "→", round(sum(len(p) for p in parts) / sr, 2))
r = hard_cuts(np.concatenate(parts).mean(1), sr)
print("句尾检查：", "OK" if not r else r)
