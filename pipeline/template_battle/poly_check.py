"""破音字检查：歌词与 DJ 口白里「一个字有两种以上念法」的字，逐字上网查教育部《重编国语辞典修订本》，用前后文找出这里该念哪个音。
有 DJ 录音时，再用强制对齐比「各种念法」哪个最像，抓出 TTS 念错音的字（例：〈Bravo 之战〉「乐长」被念成 lè zhǎng）。

用法（Voice venv，在对决的 battle/ 资料夹）：
  python poly_check.py                 # 只查文字 → out/review/poly_check.md
  python poly_check.py --audio         # 另外比对 DJ 录音（out/voice/ming/dj_<key>.wav＋dj_align.json，先跑 dj_align.py）

判读：
  - 「词典有这个词」→ 用词条的音当答案；歌词有用同音字（sing／dj.tts 和字幕不同）时，检查同音字的音是否等于答案。
  - 「要人看上下文」→ 词典没有刚好的词（多半是句子用法，如「我一毛没收」的「没」＝ㄇㄟˊ，不是「没收 ㄇㄛˋ ㄕㄡ」），要自己判断，
    必要时查 https://dict.revised.moe.edu.tw/ 例句。工具只列出来，不替你决定。
  - 唱的部分声调被旋律盖掉，机器量不准 → 只在报告标「要听」；DJ 口白（说话）才做录音比对。
查询结果快取在 out/review/moe_cache.json（重跑不再上网）。查询只送词语，不送其他资料。"""
import argparse, json, re, sys, time, html
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
URL = "https://dict.revised.moe.edu.tw/search.jsp"
UA = {"User-Agent": "Mozilla/5.0 (poly-check script)"}
LIGHT = set("的了著得地一不个们吗呢吧啊")          # 虚字、变调字：念法跟著句子走，预设不列（--all 才列）
CJK = re.compile(r"[一-鿿]")

_cache = None
CACHE = OUT / "review" / "moe_cache.json"
SITES = {"concised": "https://dict.concised.moe.edu.tw/search.jsp",   # 简编本：只收常用音，判断「是不是破音字」用这本
         "revised": "https://dict.revised.moe.edu.tw/search.jsp"}     # 修订本：词条多，找前后文的词用这本补


def moe(word, site="revised"):
    """回传 [(词条, [每字注音…]), …]；查无资料回传 []。"""
    global _cache
    if _cache is None:
        _cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    key = word if site == "revised" else f"{site}:{word}"
    if key in _cache:
        return _cache[key]
    import requests
    for k in range(3):
        try:
            r = requests.get(SITES[site], params=dict(md=1, word=word, qMd=0, qCol=1), headers=UA, timeout=30)
            break
        except Exception:
            time.sleep(2 + 3 * k)
    else:
        raise SystemExit(f"教育部辞典连不上（查「{word}」）")
    t = r.text
    res = []
    def syl(block):
        return [html.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in re.findall(r"<(?:code|phon)>(.*?)</(?:code|phon)>", block)]
    if "id=searchL" in t:
        for row in re.findall(r"<tr data-link=.*?</tr>", t, flags=re.S):
            tds = re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.S)
            if len(tds) < 3: continue
            ent = re.sub(r"<sub>.*?</sub>", "", tds[1], flags=re.S)
            ent = re.sub(r"<[^>]+>", "", ent).strip()
            youyin = "又音" in row
            res.append([ent + ("（又音）" if youyin else ""), syl(tds[2])])
    else:
        m = re.search(r"<h3>(.*?)</h3>", t, flags=re.S)
        if m and re.search(r"<(code|phon)>", m.group(1)):
            ent = re.sub(r"<[^>]+>", "", m.group(1).split(":")[0]).strip()
            res.append([ent, syl(m.group(1))])
    _cache[key] = res
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(_cache, ensure_ascii=False, indent=0), encoding="utf-8")
    time.sleep(0.25)
    return res


def char_readings(c, site="concised"):
    """这个字的常用念法（简编本；简编本没收就用修订本）。"""
    seen = []
    for ent, ph in moe(c, site):
        if ent.replace("（又音）", "") == c and ph and ph[0] not in seen:
            seen.append(ph[0] + ("（又音）" if "又音" in ent else ""))
    if not seen and site == "concised":
        return char_readings(c, "revised")
    return seen


def word_hits(phrase, i):
    """phrase 里第 i 个字：找词典里刚好等于「含这个字的 2–4 字片段」的词条 → [(词, 这个字的注音)]，长的在前。"""
    hits = []
    for n in (4, 3, 2):
        for a in range(max(0, i - n + 1), min(i, len(phrase) - n) + 1):
            w = phrase[a:a + n]
            if not all(CJK.match(x) for x in w): continue
            for ent, ph in moe(w, "concised") + moe(w):
                e = ent.replace("（又音）", "")
                if e == w and len(ph) == len(w):
                    hits.append((w + ("（又音）" if "又音" in ent else ""), ph[i - a]))
    out = []
    for h in hits:
        if h not in out: out.append(h)
    return out


def phrases(text):
    return [p for p in re.split(r"[^一-鿿]+", text) if p]


def collect(B):
    """[(来源, 字幕文字, 送去生成的文字)]"""
    rows = []
    for k, r in B["rappers"].items():
        for sec in r["lyrics"]:
            for ln in sec["lines"]:
                rows.append((f"{r['short']}歌词", ln["show"].replace("　", " "), ln["sing"]))
    dj = B["dj"]
    for k, t in dj["lines"].items():
        rows.append((f"DJ {k}", t, dj.get("tts", {}).get(k, t)))
    return rows


def align_sub(show, sing):
    """字幕与生成文字逐字对应（只比汉字；数字写法不同的段落跳过，只对等长的替换段）。"""
    from difflib import SequenceMatcher
    a, b = "".join(CJK.findall(show)), "".join(CJK.findall(sing))
    m = {}
    for op, i1, i2, j1, j2 in SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op == "equal" or (op == "replace" and i2 - i1 == j2 - j1):
            m.update({i1 + k: b[j1 + k] for k in range(i2 - i1)})
    return m


def guess(text):
    """pypinyin 依词组猜的念法（大陆预设，TTS 前端多半照这个念）→ 注音，给人对照。"""
    from pypinyin import pinyin, Style
    cs = CJK.findall(text)
    return [p[0] for p in pinyin("".join(cs), style=Style.BOPOMOFO)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=str(ROOT / "battle.json"))
    ap.add_argument("--audio", action="store_true", help="DJ 录音比对各种念法")
    ap.add_argument("--all", action="store_true", help="连「的了著得地一不」也列")
    a = ap.parse_args()
    B = json.loads(Path(a.json).read_text(encoding="utf-8"))
    md = ["# 破音字检查（教育部《重编国语辞典修订本》）", "",
          "| 来源 | 字 | 前后文 | 这个字的念法 | 词典里的词 → 这里的音 | pypinyin 猜 | 生成文字 | 判断 |", "|:--|:--|:--|:--|:--|:--|:--|:--|"]
    bad, ok_dict, ctxq, dj_expect = [], [], [], []
    for src, show, sing in collect(B):
        sub = align_sub(show, sing); gs = guess(show); pos = 0
        for ph in phrases(show):
            for i, c in enumerate(ph):
                gi = pos + i
                if c in LIGHT and not a.all: continue
                rd = char_readings(c)
                if len(rd) < 2: continue
                hits = word_hits(ph, i)
                ans = sorted({h[1] for h in hits if "又音" not in h[0]})
                sc = sub.get(gi) if sub else None
                gen = ""
                verdict = "要人看上下文" if len(ans) != 1 else "照词典"
                if sc and sc != c:
                    srd = [x.replace("（又音）", "") for x in char_readings(sc)] or ["?"]
                    gen = f"写成「{sc}」（{'／'.join(srd)}）"
                    if len(ans) == 1:
                        verdict = "同音字对" if ans[0] in srd else "⚠ 同音字的音跟词典不同"
                elif src.startswith("DJ"):
                    dj_expect.append((src[3:], gi, c, ans[0] if len(ans) == 1 else None, rd))
                g = gs[gi] if gi < len(gs) else ""
                if verdict == "照词典" and g and ans[0].replace("˙", "") != g.replace("˙", ""):
                    verdict = "照词典 ★和大陆预设不同，确认意思"          # 例：记载 ㄗㄞˋ（陆 zǎi）、一毛没收（词条＝充公）
                ctx = ph[max(0, i - 3):i] + f"【{c}】" + ph[i + 1:i + 4]
                hs = "、".join(f"{w} {p}" for w, p in hits[:4]) or "—"
                line = f"| {src} | {c} | {ctx} | {'／'.join(rd)} | {hs} | {g} | {gen} | {verdict} |"
                md.append(line)
                (bad if verdict.startswith("⚠") else ok_dict if verdict.startswith(("照词典", "同音字对")) else ctxq).append(line)
            pos += len(ph)
    H = [md[2], md[3]]
    md += ["", f"共 {len(md) - 4} 个破音字。", "",
           f"## ⚠ 同音字的音跟词典不同（{len(bad)}）", "", *H, *(bad or ["（无）"]), "",
           f"## 词典词条定的音（{len(ok_dict)}）— 要确认词条的意思跟句子一样（「一毛没收」≠ 词条「没收＝充公 ㄇㄛˋ」）", "", *H, *(ok_dict or ["（无）"]), "",
           f"## 词典没有刚好的词（{len(ctxq)}）— 看前后文自己定（pypinyin 猜的是大陆预设，TTS 多半照它念）", "", *H, *(ctxq or ["（无）"])]
    flags = bad
    if a.audio:
        md += ["", "## DJ 录音比对（强制对齐分数：越接近 0 越像）", ""] + audio_check(B, dj_expect)
    rep = OUT / "review" / "poly_check.md"
    rep.parent.mkdir(parents=True, exist_ok=True)
    rep.write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(flags) or "没有要处理的破音字"); print("→", rep)


# ------------------------------------------------------------------ DJ 录音：各种念法的强制对齐分数
BOPO = None


def bopo2py(c, bp):
    """这个字的注音 → 去声调拼音（用 pypinyin 同一字的多音清单对照）。"""
    from pypinyin import pinyin, Style
    nb = pinyin(c, style=Style.BOPOMOFO, heteronym=True)[0]
    nn = pinyin(c, style=Style.NORMAL, heteronym=True)[0]
    tb = pinyin(c, style=Style.TONE3, heteronym=True)[0]
    strip = lambda s: re.sub(r"[ˊˇˋ˙]", "", s.replace("（又音）", ""))
    for b, n in zip(nb, nn):
        if strip(b) == strip(bp): return n
    return None


def audio_check(B, expect):
    import torch, torchaudio, soundfile as sf
    from pypinyin import lazy_pinyin
    alp = OUT / "voice" / "ming" / "dj_align.json"
    if not alp.exists(): return ["（没有 dj_align.json，先跑 dj_align.py）"]
    AL = json.loads(alp.read_text(encoding="utf-8"))
    FA = torchaudio.pipelines.MMS_FA; model = FA.get_model().cuda().eval(); D = FA.get_dict()
    out = []
    for key, gi, c, ans, rd in expect:
        wav = OUT / "voice" / "ming" / f"dj_{key}.wav"
        if key not in AL or not wav.exists(): continue
        chars = []
        for w, s, e in AL[key]:
            t = w.strip(); n = max(1, len(t))
            chars += [(x, s + j * (e - s) / n, s + (j + 1) * (e - s) / n) for j, x in enumerate(t) if CJK.match(x)]
        if gi >= len(chars) or chars[gi][0] != c: continue
        a0, a1 = max(0, gi - 2), min(len(chars), gi + 2)
        py = lazy_pinyin("".join(x for x, _, _ in chars[a0:a1]))
        alts = {}
        for r in rd:
            p = bopo2py(c, r)
            if p and p not in alts.values(): alts[r] = p
        exp_p = bopo2py(c, ans) if ans else None
        if len(set(alts.values())) < 2: continue                    # 只差声调：对齐分数分不出，略
        x, sr = sf.read(str(wav), always_2d=True); x = x.mean(1)
        seg = x[int(max(0, chars[a0][1] - .1) * sr):int((chars[a1 - 1][2] + .1) * sr)]
        w = torchaudio.functional.resample(torch.tensor(seg, dtype=torch.float32)[None], sr, FA.sample_rate).cuda()
        with torch.inference_mode():
            em = torch.log_softmax(model(w)[0], -1)
        sc = {}
        for p in set(alts.values()):
            q = py[:]; q[gi - a0] = p
            toks = [D[ch] for ch in "*".join(q) if ch in D]
            _, s = torchaudio.functional.forced_align(em, torch.tensor([toks], device="cuda"), blank=0)
            sc[p] = float(s.mean())
        best = max(sc, key=sc.get)
        ctx = "".join(x for x, _, _ in chars[max(0, gi - 3):gi + 3])
        scs = "、".join(f"{p}={v:.2f}" for p, v in sorted(sc.items(), key=lambda kv: -kv[1]))
        if exp_p:
            ok = best == exp_p or sc[exp_p] >= sc[best] - 0.03
            out.append(f"- {'✅' if ok else '⚠ 可能念错'} DJ {key}「{ctx}」的「{c}」：该念 {ans}（{exp_p}），录音最像 {best}；{scs}")
        else:
            out.append(f"- ❓ DJ {key}「{ctx}」的「{c}」：词典没有刚好的词，录音最像 **{best}** → 自己对前后文判断对不对；{scs}")
    return out or ["（没有只靠声母韵母就分得出的破音字）"]


if __name__ == "__main__":
    main()
