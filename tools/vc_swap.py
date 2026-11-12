"""台词换字（不重拍影片）：把念错／不好的字换成 Ming 用角色声音念的正确字，接回原位置，再整句换声统一音色。2026-11-07 建立。
作者实测：云端影片（Gemini Omni）一句台词换掉「上」一字，试听自然；一次换两字（含同音字写法）也可。
整句长度、每个字的时间都不变 → 嘴型照样对。

用法（Voice venv）：
  C:\\AI\\Voice\\venv\\Scripts\\python.exe tools\\vc_swap.py job.json
job.json（相对路径以 job.json 所在资料夹为准）：
  {"src": "clip.mp4",                  # 影片（自动分人声／背景，做完重混换回影片）或干净人声 .wav
   "line": "第一点。我站在桌上。他看著我说，由，先下来。",   # 来源「实际念的」字（含标点；念错的字照正确字写，用来对齐）
   "ref": "characters/<角色>/voice_ref.wav",  # 角色参考音（Ming 克隆＋cosy_vc 换声提示）
   "ref_text": "...",                   # 可省：参考音逐字稿，预设读 ref 同资料夹的 voice_profile.json 的 reference_text
   "swaps": [{"at": "桌上", "char": "上",   # 用 line 里的片段定位（片段要唯一；char 预设＝片段最后一字）
              "tts": "我站在桌上。",          # 可省：Ming 要念的句子，预设＝line 里含这个字的那一小句
              "tts_at": "桌上", "tts_char": "上"}],   # 可省：同音字技巧时（tts 写「交学」）指定 tts 里要切的字
   "vc": "cosy",                        # cosy（预设，整句换声）| none（只接字、不换声）
   "out": "clip_fixed.mp4",             # .mp4（影片）或 .wav（人声）
   "work": "可省，预设 <out 档名>_vcswap/"}

流程：
  1. 影片 → BS-RoFormer 分出人声／背景。
  2. 找字的位置：MMS 强制对齐（pron_check.align）逐字找起讫 → 用音量修边界
     （起点＝MMS 起点前 80 毫秒内最安静的地方；后面接停顿时，终点延到音量比该字最大声低 25 dB 为止）。
  3. Ming（make_ming.py，角色参考音克隆、4 seed、自动挑）念 tts → 同样方法找到要切的字。
  4. 切下 Ming 的字 → 照前后字的音高比例移调（Ming 角色声音音域常跟来源不同，不移会突然拔高，作者实测 +10 半音）
     → 拉成原本那格的长度 → 音量对齐 → 12 毫秒交叉淡化接进来源人声。
  5. 整句 cosy_vc 换声（音色、接缝一起抹平）→ 跟背景重混 → 换回影片。
  6. 报告 <work>/report.json：每个换的字的位置、拉长倍率、声调判定前后（pron_check）、整句听写前后、像角色前后、长度是否不变。
限制：
  - 只修「声音」。换成嘴型差很多的字（号→日）要看画面；声调、破音字、腔调这类嘴型几乎一样的最适合。
  - 拉长倍率超出 0.7–1.4 会警告（太快或太慢会不自然），可改 tts 写法（加减停顿、换短句）重跑。
  - cosy_vc 会保留来源其他字的声调；要一次修很多字，干脆整句改 Ming 固定音轨。
  - 结果一定要人听接缝。"""
import glob
import json
import os
import re
import subprocess
import sys
from pathlib import Path

for _d in glob.glob(os.path.join(sys.prefix, "Lib", "site-packages", "nvidia", "*", "bin")):   # faster-whisper 要的 cublas／cudnn
    os.add_dll_directory(_d); os.environ["PATH"] = _d + os.pathsep + os.environ["PATH"]
import numpy as np
import soundfile as sf

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.environ["PYTHONIOENCODING"] = "utf-8"   # make_ming 会印简体字，子程式输出被导向时 cp950 会当掉
TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import pron_check as pc  # noqa: E402

AI = Path(os.environ.get("AI_ROOT", r"C:\AI"))
_EXE = "Scripts/python.exe" if os.name == "nt" else "bin/python"
VOICE_PY = os.environ.get("PY_VOICE", str(AI / "Voice" / "venv" / _EXE))
BV = AI / "BreezyVoice"
BV_PY = os.environ.get("PY_BREEZYVOICE", str(BV / "venv" / _EXE))
SEPARATOR = os.environ.get("AUDIO_SEPARATOR", str(AI / "Voice" / "venv" / ("Scripts/audio-separator.exe" if os.name == "nt" else "bin/audio-separator")))
SEP_ARGS = ["--model_filename", "model_bs_roformer_ep_317_sdr_12.9755.ckpt", "--model_file_dir", str(AI / "Voice" / "models" / "separator"),
            "--output_format", "WAV"]
CAMPPLUS = BV / "model" / "campplus.onnx"
XF = 0.012          # 交叉淡化（秒）
PUNCT = "。，！？、；：…,.!?;:「」『』（）()—～~ "


def run(*a, **k):
    subprocess.run([str(x) for x in a], check=True, **k)


def hanzi(text):
    """line 里的汉字（跟 pron_check.expected 的 chars 一一对应）＋每个汉字后面是不是标点（停顿）。"""
    chars, pause = [], []
    for c in text:
        if "\u4e00" <= c <= "\u9fff" or c.isdigit():
            chars.append(c); pause.append(False)
        elif chars and c in PUNCT:
            pause[-1] = True
    return chars, pause


def locate(chars, at, ch):
    s = "".join(chars)
    i = s.find(at)
    if i < 0 or s.find(at, i + 1) >= 0:
        raise SystemExit(f"[vc_swap] 「{at}」在「{s}」里找不到或不只一处，请把 at 写长一点")
    j = at.find(ch) if ch else len(at) - 1
    if j < 0:
        raise SystemExit(f"[vc_swap] 「{ch}」不在「{at}」里")
    return i + j


def intensity(x, sr):
    """10 毫秒一格的音量（dB）。"""
    hop = int(sr * 0.01)
    n = len(x) // hop
    fr = x[:n * hop].reshape(n, hop)
    return 20 * np.log10(np.sqrt((fr ** 2).mean(1)) + 1e-6)


def spans(wav, text):
    """逐字（起, 终）秒；MMS 对齐后用音量修边界，让起点落在子音前的低点、停顿前的字包含整个收尾。"""
    import librosa
    x, sr = sf.read(str(wav), dtype="float32", always_2d=True)
    x = x.mean(1)
    chars, base, _, _ = pc.expected(text)
    hz, pause = hanzi(text)
    assert len(hz) == len(chars), (hz, chars)
    sp = pc.align(librosa.resample(x, orig_sr=sr, target_sr=16000), base)
    db = intensity(x, sr)
    out = []
    for k, (a, b) in enumerate(sp):
        prev_end = out[-1][1] if out else 0.0
        lo = max(prev_end, a - 0.08)
        f0, f1 = int(lo * 100), max(int(lo * 100) + 1, int(a * 100) + 1)
        a2 = (f0 + int(np.argmin(db[f0:f1]))) / 100 if f1 > f0 else a
        nxt = sp[k + 1][0] if k + 1 < len(sp) else len(x) / sr
        if pause[k] or k == len(sp) - 1:                 # 后面停顿：延到音量掉 25 dB
            peak = db[int(a * 100):max(int(a * 100) + 1, int(b * 100))].max()
            e = int(b * 100)
            while e < min(len(db) - 1, int(nxt * 100) - 2, int((b + 0.35) * 100)) and db[e] > peak - 25:
                e += 1
            b2 = e / 100
        else:                                            # 后面紧接下一字：切在两字之间最安静的地方
            g0, g1 = int(b * 100), max(int(b * 100) + 1, int(nxt * 100))
            b2 = (g0 + int(np.argmin(db[g0:g1]))) / 100
        out.append((round(a2, 3), round(max(b2, a2 + 0.05), 3)))
    return chars, out


def local_f0(wav, a, b, win=0.6):
    """[a, b] 前后各 win 秒（不含本字）的浊音 F0 中位数＝这个字周围的说话音域。"""
    import parselmouth
    p = parselmouth.Sound(str(wav)).to_pitch_ac(time_step=0.01, pitch_floor=65, pitch_ceiling=500)
    t, f = p.xs(), p.selected_array["frequency"]
    sel = (f > 0) & (((t >= a - win) & (t < a)) | ((t > b) & (t <= b + win)))
    return float(np.median(f[sel])) if sel.sum() >= 5 else None


def clause_of(line, idx):
    """line 里含第 idx 个汉字的那一小句（标点切开，保留句尾标点）。"""
    parts = re.findall(r"[^。，！？；：…,!?;:]+[。，！？；：…,!?;:]?", line)
    n = 0
    for p in parts:
        c = len(hanzi(p)[0])
        if n <= idx < n + c:
            return p.strip().rstrip("，,") + ("" if p.strip()[-1:] in "。！？" else "。")
        n += c
    return line


def separate(src, work):
    voc, bg = work / "src_vocal.wav", work / "src_bg.wav"
    if voc.exists() and bg.exists():
        return voc, bg
    wav = work / "src.wav"
    run("ffmpeg", "-y", "-v", "error", "-i", src, "-vn", "-ac", "2", "-ar", "44100", wav)
    run(SEPARATOR, wav, "--output_dir", work, *SEP_ARGS, capture_output=True)
    next(work.glob("src_(Vocals)*.wav")).replace(voc)
    next(work.glob("src_(Instrumental)*.wav")).replace(bg)
    return voc, bg


def ming(work, items, ref, ref_text):
    jobs = {"out_dir": str(work / "ming"), "seeds": 4, "extra_seeds": 4,
            "jobs": [{"name": n, "text": t, "ref_audio": str(ref), "ref_text": ref_text} for n, t in items]}
    jp = work / "ming_jobs.json"
    jp.write_text(json.dumps(jobs, ensure_ascii=False, indent=1), encoding="utf-8")
    run(VOICE_PY, TOOLS / "make_ming.py", jp)
    return {n: work / "ming" / f"{n}.wav" for n, _ in items}


def cosy(src, ref, out):
    jp = out.with_suffix(".jobs.json")
    jp.write_text(json.dumps([{"src": str(src), "ref": str(ref), "out": str(out)}], ensure_ascii=False), encoding="utf-8")
    env = dict(os.environ, PYTHONPATH=os.pathsep.join(str(BV / p) for p in ("winstub", "code", "code/third_party/Matcha-TTS")))
    run(BV_PY, TOOLS / "cosy_vc.py", jp, env=env)


def measure(wavs, ref, line, idxs):
    """整句听写、像角色（CAM++）、换的字的声调判定。"""
    import onnxruntime as ort
    import torch
    import torchaudio
    from faster_whisper import WhisperModel
    cam = ort.InferenceSession(str(CAMPPLUS), providers=["CPUExecutionProvider"])

    def emb(p):
        a, sr = sf.read(str(p), dtype="float32", always_2d=True)
        x = torchaudio.functional.resample(torch.from_numpy(a.mean(1))[None], sr, 16000)
        f = torchaudio.compliance.kaldi.fbank(x, num_mel_bins=80, dither=0, sample_frequency=16000)
        e = cam.run(None, {"input": (f - f.mean(0, keepdim=True))[None].numpy()})[0][0]
        return e / np.linalg.norm(e)
    asr = WhisperModel("large-v3", device="cuda", compute_type="float16")
    r_emb = emb(ref)
    res = {}
    for name, p in wavs.items():
        segs, _ = asr.transcribe(str(p), language="zh", initial_prompt="以下是台湾国语的对话。")
        pr = pc.check(p, line)
        res[name] = {"asr": "".join(s.text for s in segs).strip(), "sim": round(float(emb(p) @ r_emb), 3),
                     "sec": round(sf.info(str(p)).duration, 3),
                     "chars": [{k: pr["chars"][i][k] for k in ("char", "pinyin", "tone", "verdict", "desc")} for i in idxs]}
    return res


def main():
    jp = Path(sys.argv[1]).resolve()
    job = json.loads(jp.read_text(encoding="utf-8"))
    P = lambda v: Path(v) if Path(v).is_absolute() else (jp.parent / v).resolve()  # noqa: E731
    src, ref, out = P(job["src"]), P(job["ref"]), P(job["out"])
    work = P(job["work"]) if job.get("work") else out.with_name(out.stem + "_vcswap")
    work.mkdir(parents=True, exist_ok=True)
    ref_text = job.get("ref_text") or json.loads((ref.parent / "voice_profile.json").read_text(encoding="utf-8"))["reference_text"]
    line, vc = job["line"], job.get("vc", "cosy")
    is_video = src.suffix.lower() in (".mp4", ".mov", ".mkv", ".webm")

    voc, bg = separate(src, work) if is_video else (src, None)
    chars, sp = spans(voc, line)
    print("[vc_swap] 来源逐字：" + " ".join(f"{c}{a:.2f}-{b:.2f}" for c, (a, b) in zip(chars, sp)))

    plan = []
    for k, s in enumerate(job["swaps"]):
        i = locate(chars, s["at"], s.get("char"))
        tts = s.get("tts") or clause_of(line, i)
        plan.append(dict(name=f"swap{k + 1}", idx=i, char=chars[i], tts=tts, tts_at=s.get("tts_at") or s["at"],
                         tts_char=s.get("tts_char") or s.get("char") or s["at"][-1]))
    wavs = ming(work, [(p["name"], p["tts"]) for p in plan], ref, ref_text)

    x, sr = sf.read(str(voc), dtype="float32", always_2d=True)
    y = x.copy()
    rms = lambda v: float(np.sqrt(np.mean(v ** 2)) + 1e-9)  # noqa: E731
    for p in plan:
        tchars, tsp = spans(wavs[p["name"]], p["tts"])
        ts = "".join(tchars)
        j0 = ts.find(p["tts_at"])
        j = (j0 + p["tts_at"].find(p["tts_char"])) if j0 >= 0 and p["tts_char"] in p["tts_at"] else ts.find(p["tts_char"])
        if j < 0:
            raise SystemExit(f"[vc_swap] tts「{p['tts']}」里找不到「{p['tts_char']}」")
        (a, b), (c, d) = sp[p["idx"]], tsp[j]
        seg, fit = work / f"{p['name']}_cut.wav", work / f"{p['name']}_fit.wav"
        run("ffmpeg", "-y", "-v", "error", "-i", wavs[p["name"]], "-ss", max(0, c - XF), "-to", d + XF, "-ac", x.shape[1], "-ar", sr, seg)
        tempo = (d - c) / (b - a)
        # 音域对齐：Ming 的角色声音可能比来源高或低（作者实测来源 106 Hz vs Ming 144 Hz）→ 照前后字的音高比例移调，避免换的字突然拔高
        f_src, f_tts = local_f0(voc, a, b), local_f0(wavs[p["name"]], c, d)
        pitch = min(1.5, max(0.67, f_src / f_tts)) if f_src and f_tts else 1.0
        af = f"asetrate={int(sr * pitch)},aresample={sr},atempo={tempo / pitch:.4f}"
        run("ffmpeg", "-y", "-v", "error", "-i", seg, "-af", af, "-ar", sr, "-ac", x.shape[1], fit)
        p["pitch_shift_semitones"] = round(12 * np.log2(pitch), 1)
        new, _ = sf.read(str(fit), dtype="float32", always_2d=True)
        n0, n1 = int((a - XF) * sr), int((b + XF) * sr)
        new = np.pad(new, ((0, max(0, (n1 - n0) - len(new))), (0, 0)))[:n1 - n0]
        new *= rms(x[n0:n1]) / rms(new)
        m = int(XF * sr); ramp = np.linspace(0, 1, m)[:, None]
        new[:m] = y[n0:n0 + m] * (1 - ramp) + new[:m] * ramp
        new[-m:] = new[-m:] * (1 - ramp) + y[n1 - m:n1] * ramp
        y[n0:n1] = new
        p.update(src_span=[a, b], tts_span=[c, d], stretch=round(1 / tempo, 3))
        warn = "  ⚠ 倍率超出 0.7–1.4，可能不自然" if not 0.7 <= 1 / tempo <= 1.4 else ""
        print(f"[vc_swap] {p['char']}：来源 {a:.2f}-{b:.2f}  ←  Ming「{p['tts']}」{c:.2f}-{d:.2f}  拉长 ×{1 / tempo:.2f}"
              f"  移调 {p['pitch_shift_semitones']:+} 半音{warn}")
    spliced = work / "vocal_spliced.wav"
    sf.write(str(spliced), y, sr)

    final = spliced
    if vc == "cosy":
        final = work / "vocal_vc.wav"
        cosy(spliced, ref, final)

    if out.suffix.lower() == ".wav":
        run("ffmpeg", "-y", "-v", "error", "-i", final, out)
    elif is_video:
        flt = ("[1:a]aresample=48000,aformat=channel_layouts=stereo,loudnorm=I=-18:TP=-2[v];"
               "[2:a]aresample=48000,aformat=channel_layouts=stereo[b];"
               "[v][b]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-16:TP=-1.5[a]")
        run("ffmpeg", "-y", "-v", "error", "-i", src, "-i", final, "-i", bg, "-filter_complex", flt,
            "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", out)
    else:
        raise SystemExit("[vc_swap] 来源是 wav 时 out 也要是 .wav")

    rep = {"src": str(src), "out": str(out), "line": line, "vc": vc, "swaps": plan,
           "measure": measure({"before": voc, "after": final}, ref, line, [p["idx"] for p in plan])}
    rep["length_same"] = abs(rep["measure"]["before"]["sec"] - rep["measure"]["after"]["sec"]) < 0.05
    (work / "report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    for k in ("before", "after"):
        mm = rep["measure"][k]
        print(f"[vc_swap] {k}: 听写「{mm['asr']}」 像角色 {mm['sim']}  长度 {mm['sec']}s  " +
              " ".join(f"{c['char']}({c['pinyin']}→{c['tone']}声 {c['verdict']} {c['desc']})" for c in mm["chars"]))
    print(f"[vc_swap] 完成 {out}（长度不变 {rep['length_same']}）；报告 {work / 'report.json'}；接缝一定要人听")


if __name__ == "__main__":
    main()
