"""中文配音「对照标准台湾国语」腔调审核 — 2026-10-04 建立。
pron_check.py 只看每字声调的升降方向，抓不到「方向对但高低／力道不像台湾国语」的腔调（使用者听到的港腔）。
这支把候选配音和一段「标准台湾国语参考音」（同一句台词，例如 zh-TW 标准语音念的）逐字对齐后，比对每个字的音高曲线形状：

  1. 两段音档都用 MMS_FA 逐字对齐（pron_check.align）。
  2. 每段各自换算半音（相对前后 3 字的区域中位数，抵消音域与整句下倾），每字取 10 点曲线。
  3. 逐字距离 = 两条曲线的 RMS 差（半音）；另比对字长比例（念太急或拖太长）。
  4. 距离 > 门槛 的字标为「腔调偏」，门槛用「两个台湾口音之间」的自然差距校准（本人真实录音 vs 标准语音）。

用法（Voice venv）：
  python C:\\AI\\tools\\pron_compare.py <候选.wav> <参考.wav> "台词"     → 每字距离、偏掉的字、整句分数
  from pron_compare import compare
参考音不放进影片，只当「答案卷」。"""
import sys
import numpy as np

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from pron_check import expected, align, f0_track  # noqa: E402

THRESH = 3.0      # 半音；校准后更新（见 C:\AI\tools\README.md 发音审核段）


def contours(path, base):
    import soundfile as sf, librosa
    x, sr = sf.read(str(path), dtype="float32"); x = x.mean(axis=1) if x.ndim > 1 else x
    x16 = librosa.resample(x, orig_sr=sr, target_sr=16000) if sr != 16000 else x
    spans = align(x16, base); t, f = f0_track(path); v = f > 0
    st = np.full_like(f, np.nan); st[v] = 12 * np.log2(f[v] / np.median(f[v]))
    cen = [np.nanmedian(st[(t >= a) & (t <= b) & v]) if ((t >= a) & (t <= b) & v).sum() else np.nan for a, b in spans]
    out = []
    for i, (a, b) in enumerate(spans):
        ref = np.nanmedian([c for c in cen[max(0, i - 3):i + 4] if not np.isnan(c)] or [0])
        pad = (b - a) * 0.06; sel = (t >= a + pad) & (t <= b - pad) & v
        if sel.sum() < 3: sel = (t >= a) & (t <= b) & v          # 短字（如「急」）不要因为切头尾而被跳过
        y = st[sel] - ref
        out.append((np.interp(np.linspace(0, 1, 10), np.linspace(0, 1, len(y)), y) if len(y) >= 3 else None, b - a))
    return out


def compare(cand, ref, text, thresh=THRESH):
    chars, base, tones, sur = expected(text)
    C, R = contours(cand, base), contours(ref, base)
    tc = sum(d for _, d in C) or 1; tr = sum(d for _, d in R) or 1
    rows, dists = [], []
    for ch, b, tn, (cc, dc), (rc, dr) in zip(chars, base, sur, C, R):
        if tn == 5 or cc is None or rc is None:
            rows.append(dict(char=ch, tone=tn, dist=None, verdict="skip")); continue
        d = float(np.sqrt(np.mean((cc - rc) ** 2))); ratio = (dc / tc) / max(1e-6, dr / tr)
        bad = d > thresh or ratio < 0.45 or ratio > 2.2
        rows.append(dict(char=ch, tone=tn, dist=round(d, 2), dur_ratio=round(ratio, 2), verdict="bad" if bad else "ok")); dists.append(d)
    bad = [r for r in rows if r["verdict"] == "bad"]
    return dict(text=text, mean_dist=round(float(np.mean(dists)), 2) if dists else None, n=len(dists), bad=[f"{r['char']}({r['dist']}半音, 长度比{r['dur_ratio']})" for r in bad],
                score=round(1 - len(bad) / max(1, len(dists)), 3), chars=rows)


if __name__ == "__main__":
    r = compare(sys.argv[1], sys.argv[2], sys.argv[3])
    print(f"score {r['score']}  mean_dist {r['mean_dist']}  bad {r['bad']}")
