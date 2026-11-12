"""edge-tts 不能用时（2026-10-12 微软回 403）的备用挑选：只用听写。
每句候选（已先跑 breeze_tailfilter.py 去掉句尾截断的）→ faster-whisper 听写 → 拼音（含声调）和台词相同才合格
→ 合格者取长度最接近中位数的（避开太快／拖太长）→ 去头尾静音输出 <out>/<name>.wav，结果写 <out>/asr_picks.json。
用法：C:\\AI\\Voice\\venv\\Scripts\\python.exe asr_pick.py jobs_v7_pick.json"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, r"C:\AI\tools")
import breezyvoice_pick as bp  # noqa: E402  (norm, write_trimmed, 听写模型设定)
from pypinyin import Style, lazy_pinyin  # noqa: E402
import soundfile as sf  # noqa: E402
from faster_whisper import WhisperModel  # noqa: E402

spec = Path(sys.argv[1]); J = json.loads(spec.read_text(encoding="utf-8")); out = spec.parent / J["out_dir"]
m = WhisperModel("large-v3", device="cuda", compute_type="float16")


def f0_range(path):
    import numpy as np, parselmouth
    p = parselmouth.Sound(str(path)).to_pitch(0.01, 75, 600).selected_array["frequency"]; p = p[p > 0]
    return float(12 * np.log2(np.percentile(p, 95) / np.percentile(p, 5))) if len(p) > 10 else 0.0


def py(s):
    s = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", bp.norm(s))
    return lazy_pinyin(s, style=Style.TONE3)


res = {}
for j in J["jobs"]:
    name = j["name"]; want = py(j["text"]); rows = []
    for f in sorted((out / "cand").glob(f"{name}_s*.wav")):
        segs, _ = m.transcribe(str(f), language="zh", initial_prompt="以下是繁体中文。")
        asr = "".join(s.text for s in segs).strip(); d = sf.info(str(f)).duration
        rows.append(dict(file=f.name, asr=asr, ok=py(asr) == want, dur=round(d, 2)))
    if not rows:   # 2026-10-12：候选全被 breeze_tailfilter 判句尾截断 → 不中断整批，标记要多抽 seed
        res[name] = dict(pick=None, n_ok=0, n=0, needs_review=True, cands=[])
        print(f"[pick] {name} 无候选（全部句尾截断，在 cand_trunc/）NEEDS_REVIEW → 加 seeds 重跑", flush=True)
        continue
    good = [r for r in rows if r["ok"]]
    if good:
        med = sorted(r["dur"] for r in good)[len(good) // 2]
        if J.get("pick") == "range":     # 语调起伏最大的（长度在中位数 0.75–1.35 倍内）
            ok2 = [r for r in good if 0.75 * med <= r["dur"] <= 1.35 * med] or good
            for r in ok2: r["range"] = f0_range(out / "cand" / r["file"])
            best = max(ok2, key=lambda r: r["range"])
        else:
            best = min(good, key=lambda r: abs(r["dur"] - med))
    else:
        best = min(rows, key=lambda r: abs(len(r["asr"]) - len(j["text"])))
    bp.write_trimmed(out / "cand" / best["file"], out / f"{name}.wav")
    res[name] = dict(pick=best["file"], n_ok=len(good), n=len(rows), needs_review=not good, cands=rows)
    print(f"[pick] {name} {best['file']} ok={len(good)}/{len(rows)} {'' if good else 'NEEDS_REVIEW ' + best['asr']}", flush=True)
(out / "asr_picks.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
