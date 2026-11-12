"""BreezyVoice 候选自动挑选（Voice venv）。2026-10-07 建立，搭配 breezyvoice_batch.py。
每句的所有 seed 候选：
  1. faster-whisper large-v3 听写，必须和台词逐字相同（数字、标点、注音标记不计）才算合格；
  2. 长度要在 edge-tts 台湾国语参考音的 0.5–2.5 倍之间（挡掉拖长、乱音）；
  3. 合格者依 pron_compare（对照 edge-tts 台湾国语参考音的每字音高曲线）分数排序，同分取平均距离小的。
都不合格 → 取听写最接近的，标 needs_review。
输出 <out_dir>/<name>.wav（选中的那支，已去头尾静音：保留开头 80 ms、结尾 150 ms）＋ <out_dir>/picks.json（全部候选分数）。
用法：C:\\AI\\Voice\\venv\\Scripts\\python.exe C:\\AI\\tools\\breezyvoice_pick.py jobs.json
edge-tts 只产生参考音当「答案卷」，不进影片（要连网；微软介面无公开授权）。job 给 "tw_ref"（自备参考音路径）就不呼叫 edge-tts。"""
import difflib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stt import _add_cuda_dll_dirs, MODEL_CACHE  # noqa: E402
_add_cuda_dll_dirs()
import soundfile as sf  # noqa: E402
import opencc  # noqa: E402
from faster_whisper import WhisperModel  # noqa: E402
from pron_compare import compare  # noqa: E402

DIG = "零一二三四五六七八九"


def int_zh(n):
    if n < 10: return DIG[n]
    if n < 100:
        t, o = divmod(n, 10); return ("" if t == 1 else DIG[t]) + "十" + (DIG[o] if o else "")
    if n < 1000:
        h, r = divmod(n, 100)
        return DIG[h] + "百" + ("" if r == 0 else ("零" + DIG[r] if r < 10 else ("一" + int_zh(r) if r < 20 else int_zh(r))))
    return "".join(DIG[int(c)] for c in str(n))


def norm(s):
    s = re.sub(r"\[:[^\]]*\]", "", s)
    s = re.sub(r"\d+", lambda m: int_zh(int(m.group())), s)
    return re.sub(r"[^\u4e00-\u9fffA-Za-z]", "", s).upper()


def dur(p):
    """有声长度（切掉头尾静音；edge-tts 会把删节号念成长停顿，不切会误判长度）"""
    import librosa
    x, sr = sf.read(str(p), dtype="float32"); x = x.mean(axis=1) if x.ndim > 1 else x
    y, _ = librosa.effects.trim(x, top_db=35); return max(len(y), 1) / sr


def py_same(a, b):
    """拼音＋声调相同就算对（ASR 把「阿禾」写成「阿和」、「课」写成「客」不算错；声调不同仍算错）"""
    if a == b:
        return True
    if re.search(r"[A-Za-z]", a + b):
        return False
    from pron_check import expected                 # 已套台湾读音（TW_OVERRIDE，例：连假＝jia4，pypinyin 会标成三声）
    f = lambda s: [(x, t) for _, x, t, _ in zip(*expected(s))]
    return f(a) == f(b)


def judge(r, plain, rd, cand_path):
    r["asr_ok"] = py_same(norm(r["asr"]), norm(plain))
    r["sim"] = round(difflib.SequenceMatcher(None, norm(r["asr"]), norm(plain)).ratio(), 3)
    if rd:
        r["len_ratio"] = round(dur(cand_path) / rd, 2)
        r["len_ok"] = 0.5 <= r["len_ratio"] <= 2.5
    else:
        r["len_ratio"] = 1.0
        r["len_ok"] = True
    return r


RERANK = "--rerank" in sys.argv      # 不重跑 ASR，只用 picks.json 里的听写结果重新判定与排序


def main():
    spec_path = Path([a for a in sys.argv[1:] if not a.startswith("--")][0]).resolve()
    spec = json.loads(spec_path.read_text(encoding="utf-8-sig"))
    out = (spec_path.parent / spec.get("out_dir", "bv")).resolve()
    refdir = out / "edge_ref"; refdir.mkdir(exist_ok=True)
    asr = WhisperModel("large-v3", device="cuda", compute_type="float16", download_root=str(MODEL_CACHE))
    s2t = opencc.OpenCC("s2twp")
    picks_path = out / "picks.json"
    picks = json.loads(picks_path.read_text(encoding="utf-8")) if picks_path.exists() else {}
    for j in spec["jobs"]:
        name, plain = j["name"], re.sub(r"\[:[^\]]*\]", "", j["text"])
        cands = sorted((out / "cand").glob(f"{name}_s*.wav"), key=lambda p: int(p.stem.rsplit("_s", 1)[1]))
        if not cands:
            print("[miss]", name); continue
        if name in picks and len(picks[name]["cands"]) == len(cands) and (out / f"{name}.wav").exists():
            if not RERANK:
                continue
            rows = [judge(r, plain, dur(refdir / f"{name}.mp3"), out / "cand" / r["file"]) for r in picks[name]["cands"]]
            choose(out, picks, picks_path, name, j, rows); continue
        ref = refdir / f"{name}.mp3"
        if j.get("tw_ref"):                              # 自备的台湾国语参考音（例如没网路时用 Breeze 产生）
            tw = Path(j["tw_ref"]); tw = tw if tw.is_absolute() else spec_path.parent / tw
            if not ref.exists() or ref.stat().st_mtime < tw.stat().st_mtime:
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tw), str(ref)], check=True)
        elif not ref.exists() or ref.stat().st_size == 0:
            try:
                subprocess.run(["edge-tts", "--voice", j.get("edge_voice", "zh-TW-YunJheNeural"), "--text", plain, "--write-media", str(ref)], check=True)
            except Exception as e:
                print(f"[warn] edge-tts error: {e}, continuing without edge reference", flush=True)
                if ref.exists() and ref.stat().st_size == 0:
                    ref.unlink(missing_ok=True)
        has_ref = ref.exists() and ref.stat().st_size > 0
        rd = dur(ref) if has_ref else None
        rows = []
        for c in cands:
            heard = s2t.convert("".join(s.text for s in asr.transcribe(str(c), language="zh", beam_size=5)[0]))
            r = judge({"file": c.name, "asr": heard}, plain, rd, c)
            if has_ref:
                try:
                    cp = compare(str(c), str(ref), plain); r.update(tw_score=cp["score"], tw_dist=cp["mean_dist"], tw_bad=cp["bad"])
                except Exception as e:                       # 单字句等对不齐时不计腔调分
                    r.update(tw_score=0.5, tw_dist=9.0, tw_err=str(e)[:80])
            else:
                r.update(tw_score=1.0, tw_dist=0.0)
            rows.append(r)
        choose(out, picks, picks_path, name, j, rows)


def write_trimmed(src, dst, head=0.08, tail=0.15):
    """选中的那支去掉头尾静音（保留开头 80 ms、结尾 150 ms），台词放到时间轴上才会准时开口、字幕对得上。
    BreezyVoice 候选头尾常有 0.3–1.0 秒静音（2026-10-07 全新安装测试发现）。回传 [裁掉的开头秒数, 保留的长度秒数]。"""
    import librosa
    x, sr = sf.read(str(src), dtype="float32")
    mono = x.mean(axis=1) if x.ndim > 1 else x
    _, (a, b) = librosa.effects.trim(mono, top_db=40)
    a = max(0, a - int(head * sr)); b = min(len(x), b + int(tail * sr))
    sf.write(str(dst), x[a:b], sr, subtype="PCM_16")
    return [round(float(a) / sr, 3), round(float(b - a) / sr, 3)]


def choose(out, picks, picks_path, name, j, rows):
    good = [r for r in rows if r["asr_ok"] and r["len_ok"]]
    pool = good or [r for r in rows if r["len_ok"]] or rows
    best = max(pool, key=lambda r: (r["asr_ok"], r["sim"], r["tw_score"], -(r["tw_dist"] or 9)) if not good else (r["tw_score"], -(r["tw_dist"] or 9)))
    trim = write_trimmed(out / "cand" / best["file"], out / f"{name}.wav")
    picks[name] = {"text": j["text"], "pick": best["file"], "n_ok": len(good), "needs_review": not good, "trim_s": trim, "cands": rows}
    picks_path.write_text(json.dumps(picks, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[pick] {name} {best['file']} ok={len(good)}/{len(rows)} tw={best['tw_score']} {'NEEDS_REVIEW ' + best['asr'] if not good else ''}", flush=True)


if __name__ == "__main__":
    main()
