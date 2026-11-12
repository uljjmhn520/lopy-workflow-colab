"""把 Suno 局部重唱（suno_replace.py）的候选接回定稿：人声连音乐整段换，接点自动找好。
〈Bravo 之战〉v3（2026-11-08）使用者听出 2:51、2:55「音乐跳接」：旧做法固定接点＋固定时间差，接点落在字中间（「张扬」的「扬」切一半），
候选的拍子在窗里慢慢漂（窗头对齐、窗尾差 16 ms）。这支改成：
  1. 每个版本先分人声（BS-RoFormer，存 out/song/sep_takes/，只做一次）；
  2. 接点在原订位置 ±0.35 秒内找「两个版本都没在唱」的空隙（比原位置安静 5 dB 以上才搬）；
  3. 窗头、窗尾各自量拍子差（伴奏＝原曲减人声，起音包络相关，1 ms 精度），窗内照两端线性对齐（FFT 重取样，最多差零点几 %，听不出来）；
  4. 窗头、窗尾各自量伴奏音量，窗内线性补（最多 ±3 dB）；
  5. 相邻两个窗直接互接（不经过定稿），等功率交叉 40 ms；
  6. 报告每个接点：搬到哪、人声音量、两端拍子差；接完再量一次跟定稿的拍子差（要 ≤3 ms）；
     两版同一个字时间不一样（一版接点后才开口、另一版接点前就唱完）会警告「可能少一个字」——〈Bravo 之战〉v4「张扬」的「扬」就是这样被切掉，
     这种要只剪人声（用分好的人声，在同一个母音的长音里剪掉多出来的长度、交叉 30 ms，再叠回原版伴奏），音乐不剪。
用法（Voice venv）：python splice_resing.py plan.json
plan.json：{"base": "out/suno/<歌>_s2_v1.mp3", "out": "song/B.wav",
            "windows": [{"take": "out/suno/<歌>_rb1_v1.mp3", "t0": 28.1, "t1": 38.9, "lag_ms": -22}, …]}
  t0／t1＝歌曲时间（定稿的秒数），lag_ms＝大约的时间差（候选比定稿晚为正；不知道就给 0，会在 ±60 ms 内找）。路径相对于 plan.json。"""
import json
import os
import subprocess
import sys
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf
from scipy.signal import resample

SR = 44100
HOP = 44                     # 起音包络 1 ms 一格
XF = 0.04                    # 接点交叉淡化秒数
SEARCH = 0.35                # 接点往前后找空隙的范围
SEP = os.environ.get("SEP_EXE") or str(Path(sys.executable).parent / ("audio-separator.exe" if os.name == "nt" else "audio-separator"))
SEP_MODEL = "model_bs_roformer_ep_317_sdr_12.9755.ckpt"
SEP_DIR = os.environ.get("SEP_MODEL_DIR") or str(Path(os.environ.get("AI_ROOT", r"C:\AI")) / "Voice" / "models" / "separator")


def load(p):
    y, _ = librosa.load(str(p), sr=SR, mono=False)
    return np.atleast_2d(y).T.astype(np.float32)          # (n, 2)


def vocals(p, d):
    d.mkdir(parents=True, exist_ok=True)
    v = next(d.glob(f"{p.stem}_(Vocals)*"), None)
    if v is None:
        subprocess.run([SEP, str(p), "--model_filename", SEP_MODEL, "--model_file_dir", SEP_DIR, "--output_dir", str(d),
                        "--output_format", "FLAC", "--single_stem", "Vocals"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        v = next(d.glob(f"{p.stem}_(Vocals)*"))
    return load(v)


def fit(a, n):
    return a[:n] if len(a) >= n else np.concatenate([a, np.zeros((n - len(a), a.shape[1]), np.float32)])


class Src:
    def __init__(self, path, d):
        self.mix = load(path); self.voc = fit(vocals(path, d), len(self.mix))
        self.inst = self.mix - self.voc
        self.ons = librosa.onset.onset_strength(y=self.inst.mean(1), sr=SR, hop_length=HOP)
        h = int(0.02 * SR); v = self.voc.mean(1)
        self.venv = 20 * np.log10(np.sqrt(np.convolve(v ** 2, np.ones(3 * h) / (3 * h), "same"))[::h] + 1e-9)   # 人声音量，20 ms 一格

    def vdb(self, t):
        return float(self.venv[min(len(self.venv) - 1, max(0, int(round(t / 0.02))))])


def lag_at(base, take, a, b, hint):
    """[a, b] 这段（歌曲时间）候选比定稿晚几 ms：伴奏起音包络相关最高的位移。"""
    i0, i1 = int(a * SR / HOP), int(b * SR / HOP); x = base.ons[i0:i1]; best = (hint, -1.0)
    for L in range(int(hint) - 60, int(hint) + 61):
        j = i0 + int(round(L * SR / 1000 / HOP)); y = take.ons[j:j + len(x)]
        if j < 0 or len(y) < len(x):
            continue
        r = float(np.corrcoef(x, y)[0, 1])
        if r > best[1]:
            best = (L, r)
    return best


def rms_db(a):
    return 20 * np.log10(np.sqrt(np.mean(a ** 2)) + 1e-9)


def main():
    plan_p = Path(sys.argv[1]).resolve(); root = plan_p.parent; P = json.loads(plan_p.read_text(encoding="utf-8"))
    sep_d = root / "out" / "song" / "sep_takes"
    base_p = root / P["base"]; base = Src(base_p, sep_d); n = len(base.mix)
    W = sorted(P["windows"], key=lambda w: w["t0"]); takes = {}
    for w in W:
        takes.setdefault(w["take"], Src(root / w["take"], sep_d))
    # 1. 两端拍子差、伴奏音量差（窗内靠接点那 2.5 秒）
    for w in W:
        tk = takes[w["take"]]; ln = min(2.5, (w["t1"] - w["t0"]) / 2)
        w["La"], w["ra"] = lag_at(base, tk, w["t0"], w["t0"] + ln, w.get("lag_ms", 0))
        w["Le"], w["re"] = lag_at(base, tk, w["t1"] - ln, w["t1"], w.get("lag_ms", 0))
        for e in ("a", "e"):                                  # 相关太低（人声盖过伴奏、两版编曲不同）量不准 → 用另一端或给的值
            if w["r" + e] < 0.75:
                o = "e" if e == "a" else "a"
                w["L" + e] = w["L" + o] if w["r" + o] >= 0.75 else w.get("lag_ms", 0)
        seg = lambda s, a, b, L: s.inst[int((a + L / 1000) * SR):int((b + L / 1000) * SR)]
        w["ga"] = float(np.clip(rms_db(seg(base, w["t0"], w["t0"] + ln, 0)) - rms_db(seg(tk, w["t0"], w["t0"] + ln, w["La"])), -3, 3))
        w["ge"] = float(np.clip(rms_db(seg(base, w["t1"] - ln, w["t1"], 0)) - rms_db(seg(tk, w["t1"] - ln, w["t1"], w["Le"])), -3, 3))
    # 2. 段落表：定稿／候选交替；相邻窗直接接
    segs = []; cur = 0.0
    for w in W:
        if w["t0"] > cur + 1e-3:
            segs.append(dict(src=base, name="定稿", a=cur, b=w["t0"], w=None))
        segs.append(dict(src=takes[w["take"]], name=Path(w["take"]).stem, a=w["t0"], b=w["t1"], w=w)); cur = w["t1"]
    segs.append(dict(src=base, name="定稿", a=cur, b=n / SR, w=None))

    def lag_of(s, t):                                       # 段落 s 在歌曲时间 t 的时间差（秒）
        w = s["w"]
        if w is None:
            return 0.0
        f = (t - w["t0"]) / max(1e-6, w["t1"] - w["t0"])
        return (w["La"] + (w["Le"] - w["La"]) * f) / 1000

    # 3. 接点搬到两边都没在唱的空隙
    rep = []
    for k in range(len(segs) - 1):
        L, R = segs[k], segs[k + 1]; t = L["b"]
        # 只能往窗外搬（多用候选），不能往窗里搬：窗里的定稿是旧歌词（〈Bravo 之战〉搬进窗里的接点听写变差）；两个窗相接时前后都可以
        lo_t = t - (0.04 if R["w"] is None else SEARCH)      # 定稿→候选：只能提早；候选→定稿：只能延后
        hi_t = t + (0.04 if L["w"] is None else SEARCH)
        grid = np.arange(lo_t, hi_t + 1e-9, 0.02)
        lo, hi = L["a"] + 0.3, R["b"] - 0.3
        score = [max(L["src"].vdb(g + lag_of(L, g)), R["src"].vdb(g + lag_of(R, g))) if lo < g < hi else 99 for g in grid]
        here = max(L["src"].vdb(t + lag_of(L, t)), R["src"].vdb(t + lag_of(R, t)))
        g = float(grid[int(np.argmin(score))]); new = g if min(score) <= here - 5 else t
        L["b"] = R["a"] = new
        # 字的时间两版不一样（〈Bravo 之战〉v4：rb9a 的「扬」在接点后 0.08 秒才开口 → 被切掉）
        # 判断法：接点前后 0.4 秒两版的音高曲线，两版都有声的格子音高差的中位数 > 1.5 半音＝两版这里唱的不是同一个字（或时间错开）
        def pitch(S, seg):
            a = new - 0.4 + lag_of(seg, new); y = S.voc[max(0, int(a * SR)):int((a + 0.8) * SR)].mean(1)
            f0, _, _ = librosa.pyin(librosa.resample(y, orig_sr=SR, target_sr=22050), fmin=70, fmax=800, sr=22050, frame_length=1024, hop_length=441)
            return 12 * np.log2(f0 / 100)
        pa, pb = pitch(L["src"], L), pitch(R["src"], R); m_ = min(len(pa), len(pb)); both = ~np.isnan(pa[:m_]) & ~np.isnan(pb[:m_])
        dp = float(np.median(np.abs(pa[:m_][both] - pb[:m_][both]))) if both.sum() >= 5 else 0.0
        rep.append(dict(seam=f"{L['name']}→{R['name']}", old=round(t, 2), new=round(new, 2), voc_old=round(here), voc_new=round(min(min(score), here)),
                        word_risk=dp > 1.5, pitch_diff=round(dp, 1)))
    # 4. 依段落表重组，等功率交叉
    out = np.zeros((n, 2), np.float32); out_i = np.zeros((n, 2), np.float32); x = int(XF * SR); hx = x // 2
    for k, s in enumerate(segs):
        a, b = int(round(s["a"] * SR)) - (hx if k else 0), min(n, int(round(s["b"] * SR)) + (hx if k < len(segs) - 1 else 0))
        def take(arr):
            if s["w"] is None:
                return arr[a:b].copy()
            ta, tb = a / SR, b / SR; pad = int(0.25 * SR)
            sa, sb = int(round((ta + lag_of(s, ta)) * SR)), int(round((tb + lag_of(s, tb)) * SR))
            src = arr[max(0, sa - pad):sb + pad]
            m = int(round((b - a) * len(src) / (sb - sa)))
            r = resample(src, m, axis=0).astype(np.float32); p0 = int(round((sa - max(0, sa - pad)) * (b - a) / (sb - sa)))
            gdb = np.linspace(s["w"]["ga"], s["w"]["ge"], b - a)
            return fit(r[p0:p0 + (b - a)], b - a) * (10 ** (gdb / 20))[:, None]
        piece, piece_i = take(s["src"].mix), take(s["src"].inst)
        env = np.ones(len(piece), np.float32)
        if k:
            env[:x] = np.sin(np.linspace(0, np.pi / 2, x)) ** 1
        if k < len(segs) - 1:
            env[-x:] = np.cos(np.linspace(0, np.pi / 2, x)) ** 1
        out[a:a + len(piece)] += piece * env[:, None]; out_i[a:a + len(piece)] += piece_i * env[:, None]
    pk = np.abs(out).max()
    if pk > 0.999:
        out *= 0.999 / pk
    dst = root / P["out"]; sf.write(str(dst), out, SR, subtype="PCM_16")
    # 5. 验收：接完的歌跟定稿的拍子差（每个接点前后 2 秒）
    chk = librosa.onset.onset_strength(y=out_i.mean(1), sr=SR, hop_length=HOP)

    class O:
        ons = chk
    print(f"→ {dst}")
    for w in W:
        print(f"  {Path(w['take']).stem}: {w['t0']:.2f}–{w['t1']:.2f}  拍子差 头 {w['La']} ms(r {w['ra']:.2f}) 尾 {w['Le']} ms(r {w['re']:.2f})"
              f"  伴奏补 {w['ga']:+.1f}/{w['ge']:+.1f} dB")
    for r_ in rep:
        t = r_["new"]; lb = lag_at(base, O, t - 2.0, t - 0.05, 0); la = lag_at(base, O, t + 0.05, t + 2.0, 0)
        r_.update(after_lag_ms=[lb[0], la[0]])
        print(f"  接点 {r_['seam']}：{r_['old']:.2f} → {r_['new']:.2f} 秒，人声 {r_['voc_old']} → {r_['voc_new']} dB；接完拍子差 前 {lb[0]} ms／后 {la[0]} ms"
              + ("  ⚠ 拍子没对齐" if max(abs(lb[0]), abs(la[0])) > 3 else "") + ("  ⚠ 接点还在字上，要人听" if r_["voc_new"] > -30 else "")
              + (f"  ⚠ 接点前后两版唱的不一样（音高差 {r_['pitch_diff']} 半音）：可能少一个字或重复一个字，逐字对" if r_["word_risk"] else ""))
    (dst.parent / f"{dst.stem}_splice.json").write_text(json.dumps(dict(windows=[{k: v for k, v in w.items()} for w in W], seams=rep),
                                                                  ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
