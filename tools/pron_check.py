"""中文配音发音审核（声调）— 2026-10-04 建立。使用者要求：发音由 agent 先审过，不要每次靠使用者听。
只比对 ASR 文字会漏掉「字对但声调错／腔调怪」；这支工具逐字检查声调走向。

用法（Voice venv）：
  C:\\AI\\Voice\\venv\\Scripts\\python.exe C:\\AI\\tools\\pron_check.py <wav> "台词" [--json out.json] [--plot out.png]
  也可 import：from pron_check import check; r = check(wav, text)  → dict(score, bad, unsure, chars=[...])

流程：
  1. 预期声调：pypinyin（词组判断破音字）＋台湾读音覆写＋变调（三三连读、一、不）。
  2. 逐字对齐：torchaudio MMS_FA 强制对齐（拼音去声调当罗马字）。
  3. 音高：Praat（parselmouth）F0 → 以「前后 3 字的区域中位数」换算半音（抵消整句下倾与说话者音域）。
  4. 逐字判断走向：一声高平、二声上扬、三声低（台湾三声常为低降／低平，不要求曲折）、四声高降；轻声不检查。
     判定 ok／bad／unsure（浊音太少、太短）。score＝ok/(ok+bad)。
限制：规则式判断，适合「挑候选」与「抓明显错」；最后仍以 bad 字列表人工对照。腔调（港腔、陆腔）没有可靠的自动量法，
源头改用台湾口音引擎（Breeze TTS 2）＋本工具声调把关。"""
import json, re, sys
from pathlib import Path
import numpy as np

_FA = None
TW_OVERRIDE = {"垃圾": ["le4", "se4"], "企": ["qi4"], "期": ["qi2"], "危": ["wei2"], "研": ["yan2"], "发": ["fa4"], "微": ["wei2"],
               "暴露": ["pu4", "lu4"], "液": ["yi4"], "和": None, "头套": ["tou2", "tao4"], "什么": ["shen2", "me5"], "东西": ["dong1", "xi5"],
               "时候": ["shi2", "hou4"], "为什么": ["wei4", "shen2", "me5"], "这里": ["zhe4", "li3"], "那里": ["na4", "li3"], "哪里": ["na3", "li3"],
               "老师": ["lao3", "shi1"], "大叔": ["da4", "shu2"], "叔": ["shu2"], "连假": ["lian2", "jia4"], "放假": ["fang4", "jia4"], "请假": ["qing3", "jia4"], "暑假": ["shu3", "jia4"], "寒假": ["han2", "jia4"], "假期": ["jia4", "qi2"], "假日": ["jia4", "ri4"],
               "台风假": ["tai2", "feng1", "jia4"], "防灾假": ["fang2", "zai1", "jia4"], "台": ["tai2"]}   # 2026-10-23：pypinyin 把台风假的假当三声
DIGIT = dict(zip("0123456789", "零一二三四五六七八九"))


def expected(text):
    from pypinyin import pinyin, Style
    t = "".join(DIGIT.get(c, c) for c in text)
    chars, brk = [], set()                              # brk\uff1a\u8a72\u5b57\u5f8c\u9762\u6709\u6a19\u9ede\uff08\u505c\u9813\uff09\u2192 \u8b8a\u8abf\u4e0d\u8de8\u904e\u53bb
    for c in t:
        if "\u4e00" <= c <= "\u9fff": chars.append(c)
        elif chars: brk.add(len(chars) - 1)
    s = "".join(chars)
    py = [p[0] for p in pinyin(s, style=Style.TONE3, neutral_tone_with_five=True, heteronym=False)]
    for k, v in TW_OVERRIDE.items():                    # 台湾读音（长的词先套）
        if not v: continue
        i = s.find(k)
        while i >= 0:
            py[i:i + len(k)] = v; i = s.find(k, i + 1)
    tones = [int(p[-1]) if p[-1].isdigit() else 5 for p in py]
    base = [re.sub(r"\d", "", p).replace("ü", "v") for p in py]
    sur = tones[:]
    for i in range(len(sur) - 2, -1, -1):              # 三三连读：前字变二声（不跨标点）
        if tones[i] == 3 and sur[i + 1] == 3 and i not in brk: sur[i] = 2
    for i, c in enumerate(chars):                       # 一、不 变调
        nxt = tones[i + 1] if i + 1 < len(tones) and i not in brk else None
        if c == "一" and nxt is not None and not (i > 0 and chars[i - 1] in "第") and chars[i + 1:i + 2] != ["次"] or (c == "一" and nxt == 4):
            if nxt is not None: sur[i] = 2 if nxt == 4 else 4
        if c == "不" and nxt == 4: sur[i] = 2
    return chars, base, tones, sur


def _fa():
    global _FA
    if _FA is None:
        import torch, torchaudio
        b = torchaudio.pipelines.MMS_FA
        dev = "cuda" if torch.cuda.is_available() else "cpu"
        _FA = (b, b.get_model(with_star=False).to(dev), b.get_tokenizer(), b.get_aligner(), dev)
    return _FA


def align(wav16, base):
    import torch
    b, model, tok, aligner, dev = _fa()
    with torch.inference_mode():
        em, _ = model(torch.from_numpy(wav16)[None].to(dev))
        spans = aligner(em[0], tok(base))
    ratio = len(wav16) / em.shape[1] / 16000
    return [(sp[0].start * ratio, sp[-1].end * ratio) for sp in spans]


def f0_track(path):
    import parselmouth
    snd = parselmouth.Sound(str(path))
    p = snd.to_pitch_ac(time_step=0.01, pitch_floor=65, pitch_ceiling=500)
    f = p.selected_array["frequency"]; t = p.xs()
    return t, f


def judge(st, tone, dur):
    """st：该字浊音段的半音序列（相对区域中位数）。回传 (verdict, 描述)。"""
    if tone == 5: return "skip", ""
    if len(st) < 3 or dur < 0.05: return "unsure", "浊音太少"
    n = len(st); q = max(1, n // 4)
    a, z, m = float(np.mean(st[:q])), float(np.mean(st[-q:])), float(np.mean(st))
    rise, lo = z - a, float(np.min(st))
    desc = f"起{a:+.1f} 末{z:+.1f} 均{m:+.1f}"
    if tone == 1:
        ok = m > -2.5 and abs(rise) < 4.0
        bad = m < -4.5 or abs(rise) > 5.5
    elif tone == 2:
        ok = rise > 0.3 or (lo < a - 0.5 and z > lo + 1.0)
        bad = rise < -3.0
    elif tone == 3:
        ok = m < 1.0 or (lo < min(a, z) - 1.0)
        bad = m > 3.5 and lo > a - 0.5
    else:  # 4
        ok = rise < -0.8
        bad = rise > 2.5 or (m < -4.5 and abs(rise) < 1.0)
    return ("ok" if ok and not bad else ("bad" if bad else "unsure")), desc


def check(path, text, plot=None):
    import soundfile as sf, librosa
    chars, base, tones, sur = expected(text)
    x, sr = sf.read(str(path), dtype="float32"); x = x.mean(axis=1) if x.ndim > 1 else x
    x16 = librosa.resample(x, orig_sr=sr, target_sr=16000) if sr != 16000 else x
    spans = align(x16, base)
    t, f = f0_track(path)
    voiced = f > 0
    st_all = np.full_like(f, np.nan); st_all[voiced] = 12 * np.log2(f[voiced] / np.median(f[voiced]))
    cen = []
    for s0, s1 in spans:
        sel = (t >= s0) & (t <= s1) & voiced
        cen.append(np.nanmedian(st_all[sel]) if sel.sum() else np.nan)
    out = []
    for i, (c, b, tn, ts, (s0, s1)) in enumerate(zip(chars, base, tones, sur, spans)):
        lo, hi = max(0, i - 3), min(len(spans), i + 4)
        ref = np.nanmedian([v for v in cen[lo:hi] if not np.isnan(v)] or [0])
        pad = (s1 - s0) * 0.08
        sel = (t >= s0 + pad) & (t <= s1 - pad) & voiced
        if sel.sum() < 3: sel = (t >= s0) & (t <= s1) & voiced          # 短字不要被跳过
        st = st_all[sel] - ref
        v, d = judge(st, ts, s1 - s0)
        out.append(dict(char=c, pinyin=f"{b}{tn}", tone=ts, start=round(s0, 3), end=round(s1, 3), verdict=v, desc=d))
    ok = sum(o["verdict"] == "ok" for o in out); bad = [o for o in out if o["verdict"] == "bad"]
    res = dict(text=text, score=round(ok / max(1, ok + len(bad)), 3), n=len(out), ok=ok,
               bad=[f"{o['char']}({o['pinyin']}→应{o['tone']}声 {o['desc']})" for o in bad],
               unsure=[o["char"] for o in out if o["verdict"] == "unsure"], chars=out)
    if plot:
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
        plt.figure(figsize=(max(6, len(out) * 0.6), 3)); plt.plot(t, st_all, ".", ms=2)
        for o in out:
            col = {"ok": "g", "bad": "r", "unsure": "y", "skip": "0.7"}[o["verdict"]]
            plt.axvspan(o["start"], o["end"], color=col, alpha=0.15); plt.text((o["start"] + o["end"]) / 2, 8, f"{o['pinyin']}", ha="center", fontsize=7)
        plt.ylim(-12, 10); plt.tight_layout(); plt.savefig(plot, dpi=110); plt.close()
    return res


if __name__ == "__main__":
    a = sys.argv[1:]
    r = check(a[0], a[1], plot=a[a.index("--plot") + 1] if "--plot" in a else None)
    if "--json" in a: Path(a[a.index("--json") + 1]).write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"score {r['score']}  ok {r['ok']}/{r['n']}  bad {r['bad']}  unsure {r['unsure']}")
