"""全本地多镜短片范本：读 film.json，从角色定妆照一路做到成片＋自审。做新片只改 film.json，这支程式不用改。
H3 venv 执行（ComfyUI 要先开：同一个 cmd 视窗 call configs\\profile.cmd → C:\\AI\\tools\\start_comfy.cmd）：
  C:\\AI\\H3\\venv\\Scripts\\python.exe make_film.py [stage ...] [--film 别的设定.json]
stage（不给＝全部依序）：chars masters frames voices h3 amb edl music ending cut review
每一步的输出都在 out/，已存在的档案会跳过，所以可以中断后续跑、或删掉某个档重做：
  - 重生某一镜首帧：删 out/first/<镜>.png，在 film.json 的 seeds 加 "frame_<镜>": 新 seed，再跑 frames
  - 重拍某一镜 H3：删 out/h3/<镜>/clip.mp4（或加 "h3_<镜>": 新 seed），再跑 h3（环境变数 ONLY="S2 S5" 只跑指定镜）
  - 改了台词：voice_mode h3_ref（预设）删 out/h3/<镜>/clip.mp4 再跑 h3；fixed 删 out/voice/bv 里那句的档（或整个 out/voice/bv），再跑 voices
台词声音（2026-10-23 起预设 voice_mode "h3_ref"）：Breeze 设计角色参考音 → H3 拿参考音自己念台词（嘴型与声音一起生成）→ h3 阶段结尾
分离人声＋听写比对原文。"fixed"＝旧做法（BreezyVoice 配音当固定音轨）。film.json 全片设 voice_mode，单句可在 line 里设 "voice_mode" 覆写。
2026-10-24 本范本从头实测（RTX 5090，〈被狗吃掉的作业〉7 镜、action 照官方结构写）：6 句台词 H3 全部念对、自审五遍通过、影音同为 39.000 秒、全程约 27 分钟。
  - 改了剪接（cut_in、tail…）：跑 edl cut review 即可
人工关卡：frames 之后看 out/first/_sheet.jpg；h3 之后看 out/review/clips_*.jpg；review 之后一定要看成片。
2026-10-07 由「一个没看过本专案的 agent 照 repo 做出〈被狗吃掉的作业〉」时写的 film.py／post.py 整理而成。"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
import wave
from pathlib import Path

for _s in (sys.stdout, sys.stderr):                 # 中文输出在非 UTF-8 主控台不变乱码
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
ARGS = [a for a in sys.argv[1:]]
FILM = HERE / (ARGS[ARGS.index("--film") + 1] if "--film" in ARGS else "film.json")
CFG = json.loads(FILM.read_text(encoding="utf-8"))
OUT = HERE / "out"; OUT.mkdir(exist_ok=True)
REPO = (HERE / CFG.get("repo_dir", "../..")).resolve()
T = Path(os.environ.get("AI_TOOLS", r"C:\AI\tools"))
PYH3 = os.environ.get("PY_H3", r"C:\AI\H3\venv\Scripts\python.exe")
PYV = os.environ.get("PY_VOICE", r"C:\AI\Voice\venv\Scripts\python.exe")
PYB = os.environ.get("PY_BREEZE", r"C:\AI\BreezeTTS\venv\Scripts\python.exe")
PYBV = os.environ.get("PY_BREEZYVOICE", r"C:\AI\BreezyVoice\venv\Scripts\python.exe")
SEP = str(Path(PYV).parent / ("audio-separator.exe" if os.name == "nt" else "audio-separator"))
HOST = os.environ.get("COMFY_HOST", "http://127.0.0.1:8188")
SR, FPS = 48000, 24
sys.path.insert(0, str(REPO / "tools"))
from fonts import font, SUB_FONT_NAME  # noqa: E402  (Windows 字型／Linux 用 Noto CJK)
UPSCALE = os.environ.get("UPSCALE", "rtxvsr" if os.name == "nt" else "lanczos")   # rtxvsr（只有 Windows）｜flashvsr｜lanczos


def local_h3_ok():
    """本机能不能跑 H3：NVIDIA 显卡 ≥15GB 且记忆体 ≥30GB（三份硬体版 repo 的最低配置）。"""
    try:
        vram = int(subprocess.run(["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
                                  capture_output=True, text=True, timeout=20).stdout.split()[0]) / 1024
    except Exception:
        return False
    try:
        if os.name == "nt":
            import ctypes
            class M(ctypes.Structure):
                _fields_ = [("l", ctypes.c_ulong), ("load", ctypes.c_ulong), ("total", ctypes.c_ulonglong)] + [(f"x{i}", ctypes.c_ulonglong) for i in range(6)]
            m = M(); m.l = ctypes.sizeof(M); ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)); ram = m.total / 2**30
        else:
            ram = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2**30
    except Exception:
        ram = 0
    return vram >= 15 and ram >= 30


# H3 在哪跑：local＝本机 ComfyUI；colab＝整批送到 Google Colab G4（cloud/colab_h3.py）；
# both＝本机＋Colab 一起跑（共用伫列，cloud/hybrid_h3.py，⚠ 尚未实测）。不设就自动判断（local／colab）。
H3_BACKEND = os.environ.get("H3_BACKEND") or ("local" if local_h3_ok() else "colab")


def render_h3(dirs):
    """dirs 里每个资料夹都有 spec.json；成品写回同一个资料夹（clip.mp4、meta.json…）。"""
    if not dirs:
        return
    if H3_BACKEND == "both":
        sys.path.insert(0, str(REPO / "cloud")); from hybrid_h3 import run_hybrid   # noqa: E402
        miss = run_hybrid(dirs, PYH3, T)
        if miss:
            sys.exit(f"[h3] 这些镜头没做出来：{' '.join(d.name for d in miss)}")
    elif H3_BACKEND == "colab":
        print(f"[h3] {len(dirs)} 镜送到 Colab（cloud/colab_h3.py batch）", flush=True)
        run([sys.executable, REPO / "cloud" / "colab_h3.py", "batch"] + [d / "spec.json" for d in dirs])
    elif os.environ.get("H3_PARALLEL") == "2":           # 全云端模式（colab_h3.py film 设定）：H3 这一步改用 2 个 ComfyUI 错开跑
        run([PYH3, REPO / "cloud" / "vm" / "parallel_h3.py"] + dirs)
    else:
        for d in dirs:
            run([PYH3, T / "h3_shot.py", d / "spec.json", "--out", d])
CHARS, SHOTS = CFG["chars"], CFG["shots"]
LINES = [(s["id"], s["line"]) for s in SHOTS if s.get("line")]      # (镜, {who, text, tts?, at, voice_mode?})
VOICE_MODE = CFG.get("voice_mode", "h3_ref")                        # h3_ref＝H3＋角色参考音自己念（预设）｜fixed＝BreezyVoice 固定音轨


def h3_says(ln):
    """这句台词是不是让 H3 自己念（h3_ref）。"""
    return ln.get("voice_mode", VOICE_MODE) == "h3_ref"


def est_line_secs(ln):
    """H3 自己念时事先估台词秒数（约每秒 4 字，至少 1.2 秒）；实际起讫在 h3 阶段结尾听写抓。"""
    return max(1.2, len(re.findall(r"[一-鿿A-Za-z0-9]", ln["text"])) / 4.0)
MIX = CFG.get("mix", {})
TIMING = OUT / "timing.json"
timing = json.loads(TIMING.read_text(encoding="utf-8")) if TIMING.exists() else {}


def seed(key, default):
    return int(CFG.get("seeds", {}).get(key, default))


def comfy_ok():
    try:
        urllib.request.urlopen(HOST + "/system_stats", timeout=5); return True
    except Exception:
        return False


def free_comfy():
    try:
        r = urllib.request.Request(HOST + "/free", data=json.dumps({"unload_models": True, "free_memory": True}).encode(),
                                   headers={"Content-Type": "application/json"})
        urllib.request.urlopen(r, timeout=30)
    except Exception:
        pass
    time.sleep(5)


def run(cmd, cwd=OUT, check=True, **kw):
    print("$", " ".join(map(str, cmd))[:200], flush=True)
    env = {**os.environ, **kw.pop("env", {}), "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    r = subprocess.run([str(c) for c in cmd], cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=env, stdin=subprocess.DEVNULL, **kw)
    if check and r.returncode != 0:
        raise SystemExit(f"FAILED: {' '.join(map(str, cmd))[:200]}\n{(r.stdout + r.stderr)[-2500:]}")
    return r


def newest(d, ext=".png"):
    fs = sorted(Path(d).glob(f"*{ext}"), key=lambda f: f.stat().st_mtime)
    return fs[-1] if fs else None


def dur(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    return float(r.stdout)


def frames_for(d):
    n = 0
    while 17 * n + 5 < d * FPS:
        n += 1
    return 17 * n + 5


def stage(name):
    def deco(fn):
        def wrap():
            t0 = time.time(); a = time.strftime("%H:%M:%S"); fn()
            timing[name] = dict(sec=round(time.time() - t0, 1), start=a, end=time.strftime("%H:%M:%S"))
            TIMING.write_text(json.dumps(timing, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"[stage] {name} {timing[name]['sec']}s", flush=True)
        return wrap
    return deco


def line_index(sid):
    return next(i for i, (s, _) in enumerate(LINES) if s == sid)


# ------------------------------------------------------------------------------------------------ 图
@stage("chars")
def chars():
    """角色定妆照：单张、灰底、正面半身（docs/07 §1）。不满意就在 seeds 加 char_<角色> 换 seed、删档重跑。"""
    for k, c in CHARS.items():
        dst = OUT / "chars" / f"{k}.png"
        if dst.exists():
            continue
        p = ("Studio character reference photo, single person only, one image (not a collage), medium close-up bust portrait facing the camera, "
             "plain light grey seamless background, soft even studio light, sharp focus, realistic photograph. " + c["look"] + ", gentle natural expression. "
             "No text, no watermark.")
        run([PYH3, T / "gen_image.py", "--prompt", p, "--width", "1024", "--height", "1024", "--seed", seed("char_" + k, 11),
             "--prefix", f"film/char_{k}", "--out", "chars"])
        newest(OUT / "chars").rename(dst)


@stage("masters")
def masters():
    """场景母版（空景 2K），再依每镜的 scene 框裁成该镜景别，当首帧的场景参考（docs/07 §4）。"""
    from PIL import Image
    for k, p in CFG.get("masters", {}).items():
        dst = OUT / "masters" / f"{k}.png"
        if not dst.exists():
            run([PYH3, T / "gen_image.py", "--prompt", p, "--seed", seed("master_" + k, 21), "--prefix", f"film/master_{k}", "--out", "masters"])
            newest(OUT / "masters").rename(dst)
    for s in SHOTS:
        if not s.get("scene"):
            continue
        m, box = s["scene"]; im = Image.open(OUT / "masters" / f"{m}.png").convert("RGB"); W, H = im.size
        crop = im.crop((int(box[0] * W), int(box[1] * H), int(box[2] * W), int(box[3] * H)))
        crop.thumbnail((1344, 1344)); crop.save(OUT / "masters" / f"crop_{s['id']}.png")


@stage("frames")
def frames():
    """首帧：Qwen-Image-Edit 附「角色定妆照（<image1>…）＋场景裁切（最后一张）」。每镜都照抄角色完整外观描述，否则会掉眼镜、换发型。"""
    for s in SHOTS:
        dst = OUT / "first" / f"{s['id']}.png"
        if dst.exists():
            continue
        keep = " ".join(f"Keep exactly the same person as <image{i}>: same face, hairstyle and clothes ({CHARS[k]['look']})."
                        for i, k in enumerate(s["refs"], 1))
        set_s = (" " + CFG["set_sentence"].format(n=len(s["refs"]) + 1)) if s.get("scene") else ""
        p = keep + set_s + " New photo: " + CFG["cine"] + s["frame"] + CFG.get("frame_suffix", " No text, no watermark, no captions.")
        cmd = [PYH3, T / "gen_image.py", "--model", "qwen-edit", "--width", "1344", "--height", "768", "--prompt", p,
               "--seed", seed("frame_" + s["id"], 5101), "--prefix", f"film/{s['id']}", "--out", "first"]
        for k in s["refs"]:
            cmd += ["--ref", OUT / "chars" / f"{k}.png"]
        if s.get("scene"):
            cmd += ["--ref", OUT / "masters" / f"crop_{s['id']}.png"]
        run(cmd)
        newest(OUT / "first").rename(dst)
    sheet([OUT / "first" / f"{s['id']}.png" for s in SHOTS], OUT / "first" / "_sheet.jpg")
    print("→ 人工检查 out/first/_sheet.jpg：脸、服装、多手多脚、背景有没有字、窗户方向", flush=True)


def sheet(files, dst, cols=3):
    from PIL import Image, ImageDraw, ImageFont
    fs = [p for p in files if Path(p).exists()]
    if not fs:
        return
    W, H = 672, 384; rows = (len(fs) + cols - 1) // cols
    im = Image.new("RGB", (W * cols, H * rows)); f = ImageFont.truetype(font("jhbd"), 28)
    for i, p in enumerate(fs):
        t = Image.open(p).convert("RGB").resize((W, H)); ImageDraw.Draw(t).text((8, 6), Path(p).stem, font=f, fill=(255, 255, 0), stroke_width=3, stroke_fill=0)
        im.paste(t, ((i % cols) * W, (i // cols) * H))
    Path(dst).parent.mkdir(parents=True, exist_ok=True); im.save(dst, quality=85)


# ------------------------------------------------------------------------------------------------ 声音
def load_picks():
    """out/voice_picks.json：每句台词实际用的声音档（BreezyVoice 挑的，或 H3 成片分离出的人声）。"""
    p = OUT / "voice_picks.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


@stage("voices")
def voices():
    """Breeze 设计角色声音（一次，h3_ref 拿它当 H3 的参考音）。fixed 的句子再做：edge-tts 台湾国语答案卷 → BreezyVoice 每句 8 候选 →
    自动挑（听写拼音声调全对＋腔调分数，已去头尾静音）。"""
    free_comfy()
    vd = OUT / "voice"; vd.mkdir(exist_ok=True)
    jobs = [dict(name=f"ref_{k}", text=c["voice_sample"], instruction=c["voice_design"], seed=seed("voice_" + k, 7)) for k, c in CHARS.items()]
    fixed = [(i, sid, ln) for i, (sid, ln) in enumerate(LINES) if not h3_says(ln)]
    if not fixed:                                    # 全部 h3_ref：只要角色参考音
        (OUT / "breeze.json").write_text(json.dumps(dict(out_dir="voice", jobs=jobs), ensure_ascii=False, indent=1), encoding="utf-8")
        run([PYB, T / "breeze_batch.py", "breeze.json"])
        print("[voices] voice_mode h3_ref：角色参考音在 out/voice/ref_<角色>.wav，台词由 H3 在 h3 阶段自己念", flush=True)
        return
    for i, sid, ln in fixed:                         # 答案卷：只拿来比腔调，不进成片
        w = vd / f"tw_{i}.wav"
        if w.exists():
            continue
        mp3 = vd / f"tw_{i}.mp3"
        r = run([PYV, T / "gen_voice.py", "--engine", "edge", "--text", ln["text"], "--voice", CHARS[ln["who"]].get("edge_voice", "zh-TW-YunJheNeural"),
                 "--out", mp3], check=False)
        if r.returncode == 0 and mp3.exists():
            run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp3, "-ar", "48000", "-ac", "1", w])
        else:                                        # 没网路：改用 Breeze 产生答案卷（可靠度较低）
            jobs.append(dict(name=f"tw_{i}", text=ln["text"], instruction="A clear, neutral standard Taiwanese Mandarin news-reading voice, calm, precise tones.", seed=11))
    (OUT / "breeze.json").write_text(json.dumps(dict(out_dir="voice", jobs=jobs), ensure_ascii=False, indent=1), encoding="utf-8")
    run([PYB, T / "breeze_batch.py", "breeze.json"])
    bv = [dict(name=f"line{i}", text=ln.get("tts", ln["text"]), ref_audio=f"voice/ref_{ln['who']}.wav", ref_text=CHARS[ln["who"]]["voice_sample"],
               tw_ref=f"voice/tw_{i}.wav", seeds=8) for i, sid, ln in fixed]
    (OUT / "bv.json").write_text(json.dumps(dict(out_dir="voice/bv", jobs=bv), ensure_ascii=False, indent=1), encoding="utf-8")
    run([PYBV, T / "breezyvoice_batch.py", "bv.json"])
    run([PYV, T / "breezyvoice_pick.py", "bv.json"])
    bp = json.loads((vd / "bv" / "picks.json").read_text(encoding="utf-8"))
    picks, bad = load_picks(), []
    for i, sid, ln in fixed:
        p = bp[f"line{i}"]; best = next(c for c in p["cands"] if c["file"] == p["pick"])
        if p["needs_review"]:
            bad.append(f"{sid}「{ln['text']}」听成「{best['asr']}」")
        picks[str(i)] = dict(shot=sid, who=ln["who"], text=ln["text"], file=str(vd / "bv" / f"line{i}.wav"), heard=best["asr"],
                             tw_score=best.get("tw_score"), needs_review=p["needs_review"], source="breezyvoice")
        print("pick", sid, ln["text"], "→", p["pick"], best["asr"], best.get("tw_score"), flush=True)
    (OUT / "voice_picks.json").write_text(json.dumps(picks, ensure_ascii=False, indent=1), encoding="utf-8")
    if bad and os.environ.get("ALLOW_REVIEW") != "1":
        raise SystemExit("这几句 8 个候选听写都不对：" + "；".join(bad) +
                         "\n请在 film.json 该句加 \"tts\"（念不准的字标注音，例：假[:ㄐㄧㄚ4]）或换说法，删掉 out/voice/bv 再跑 voices；"
                         "确定只是 ASR 听错（例如单字喊叫）就用 ALLOW_REVIEW=1 继续。")


# ------------------------------------------------------------------------------------------------ H3
def shot_secs(s, picks):
    d = s["dur"]
    if s.get("line"):
        ln = s["line"]
        if h3_says(ln):                              # H3 自己念：用估计秒数＋1.2 秒余裕（H3 偶尔晚开口）
            d = max(d, ln["at"] + est_line_secs(ln) + 1.2)
        else:
            d = max(d, ln["at"] + dur(picks[str(line_index(s["id"]))]["file"]) + 0.8)
    return frames_for(d) / FPS


def h3_spec(s, secs, dialogue):
    h = CFG["h3"]
    return dict(duration=round(secs - 0.02, 3), size=[1344, 768], seed=seed("h3_" + s["id"], h.get("default_seed", 20261007)), steps=14, draft=True,
                style=h["style"], setting=h["setting"], first_frame=str(OUT / "first" / f"{s['id']}.png"),
                subjects=[dict(key=k, desc=CHARS[k]["look"], voice=CHARS[k]["h3_voice"]) for k in s["refs"]],
                shots=[dict(camera=s.get("camera", h.get("camera", "The camera holds a static shot on a tripod.")), action=s["action"], dialogue=dialogue)],
                constraints=h.get("constraints", []) + s.get("extra_constraints", []), soundscape=h["soundscape"], music="N/A")


@stage("h3")
def h3():
    """每镜 H3（DMAD 4 步、只给首帧）。有台词：h3_ref＝给角色参考音、H3 自己念；fixed＝放 BreezyVoice 配音当固定音轨。
    没台词的镜头一律给静音固定音轨（否则角色会自己嘟囔）。h3_ref 的镜头跑完后 harvest_lines() 抓出台词。"""
    picks = load_picks()
    only = os.environ.get("ONLY", "").split(); todo = []
    for s in SHOTS:
        if only and s["id"] not in only:
            continue
        od = OUT / "h3" / s["id"]
        if (od / "clip.mp4").exists():
            continue
        od.mkdir(parents=True, exist_ok=True)
        secs = shot_secs(s, picks); buf = bytearray(int(secs * SR) * 2); dlg = []
        if s.get("line") and h3_says(s["line"]):
            ln = s["line"]
            dlg = [dict(subject=ln["who"], line=ln["text"], lang="Chinese", after="Right after the line the speaker's lips close and stay closed.")]
            spec = h3_spec(s, secs, dlg)
            spec["audio"] = {"voice_ref": {"subject": ln["who"], "file": str(OUT / "voice" / f"ref_{ln['who']}.wav")}}
            (od / "spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
            todo.append(od)
            continue
        if s.get("line"):
            ln = s["line"]; f = picks[str(line_index(s["id"]))]["file"]
            pcm = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", f, "-ar", str(SR), "-ac", "1", "-f", "s16le", "-"], capture_output=True).stdout
            st = int(ln["at"] * SR) * 2; seg = pcm[: len(buf) - st]; buf[st:st + len(seg)] = seg
            dlg = [dict(subject=ln["who"], line=ln["text"], lang="Chinese", after="Right after the line the speaker's lips close and stay closed.")]
        with wave.open(str(od / "guide.wav"), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(bytes(buf))
        spec = h3_spec(s, secs, dlg); spec["audio"] = {"fixed": {"file": str(od / "guide.wav")}}
        (od / "spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
        todo.append(od)
    render_h3(todo)
    harvest_lines()
    sheet_clips()


def harvest_lines():
    """h3_ref 的台词：H3 成片音轨 → BS-RoFormer 取人声 → 听写（找起讫、比对原文）→ 存 out/voice/h3/line<i>.wav，写进 voice_picks.json。
    H3 会改用词（例：二十四号→二十四日）、偶尔晚开口；听写和原文差太多就停下来，换 seed（seeds 加 h3_<镜>）重拍。"""
    import difflib
    picks, bad = load_picks(), []
    hd = OUT / "voice" / "h3"; hd.mkdir(parents=True, exist_ok=True)
    norm = lambda t: "".join(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]", t)).lower()
    for i, (sid, ln) in enumerate(LINES):
        clip = OUT / "h3" / sid / "clip.mp4"
        if not h3_says(ln) or not clip.exists():
            continue
        dst = hd / f"line{i}.wav"; p = picks.get(str(i), {})
        if dst.exists() and p.get("source") == "h3" and dst.stat().st_mtime >= clip.stat().st_mtime:
            continue                                 # 已抓过、而且镜头没重拍
        wav = hd / f"{sid}_mix.wav"
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", clip, "-vn", "-ac", "2", "-ar", "44100", wav])
        for f in hd.glob(f"{sid}_mix_(*"):
            f.unlink()
        run([SEP, wav, "--model_filename", "model_bs_roformer_ep_317_sdr_12.9755.ckpt", "--model_file_dir",
             Path(os.environ.get("AI_ROOT", r"C:\AI")) / "Voice" / "models" / "separator", "--output_dir", hd, "--output_format", "WAV"])
        voc = next(hd.glob(f"{sid}_mix_(Vocals)*.wav"))
        run([PYV, T / "stt.py", "--audio", voc, "--outdir", hd / f"{sid}_stt"], check=False)
        tj = hd / f"{sid}_stt" / "transcript.json"
        segs = json.loads(tj.read_text(encoding="utf-8"))["segments"] if tj.exists() else []
        heard = "".join(x["text"] for x in segs)
        a = max(0.0, segs[0]["start"] - 0.05) if segs else float(ln["at"]); b = segs[-1]["end"] + 0.15 if segs else a + est_line_secs(ln)
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", voc, "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-ar", str(SR), "-ac", "1", dst])
        score = difflib.SequenceMatcher(None, norm(ln["text"]), norm(heard)).ratio()
        review_ = score < 0.7
        if review_:
            bad.append(f"{sid}「{ln['text']}」听成「{heard}」")
        picks[str(i)] = dict(shot=sid, who=ln["who"], text=ln["text"], file=str(dst), heard=heard, at=round(a, 3),
                             match=round(score, 2), needs_review=review_, source="h3")
        print(f"line {sid}: H3 念「{heard}」（相似 {score:.2f}，{a:.2f}–{b:.2f} 秒）", flush=True)
    (OUT / "voice_picks.json").write_text(json.dumps(picks, ensure_ascii=False, indent=1), encoding="utf-8")
    if bad and os.environ.get("ALLOW_REVIEW") != "1":
        raise SystemExit("H3 念的台词和原文差太多：" + "；".join(bad) +
                         "\n在 film.json 的 seeds 加 \"h3_<镜>\": 新数字、删 out/h3/<镜>/clip.mp4，再跑 ONLY=<镜> h3；抽 2–3 次都不对就在该句 line 加 "
                         "\"voice_mode\": \"fixed\"（改用 BreezyVoice 固定音轨，先跑 voices）。确定只是听写听错（同音字）就用 ALLOW_REVIEW=1 继续。")


def sheet_clips():
    from PIL import Image
    rv = OUT / "review"; rv.mkdir(exist_ok=True)
    for s in SHOTS:
        c = OUT / "h3" / s["id"] / "clip.mp4"
        if not c.exists():
            continue
        d = dur(c); tiles = []
        for q in (0.08, 0.3, 0.5, 0.7, 0.85, 0.97):
            raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", f"{d * q:.2f}", "-i", str(c), "-frames:v", "1", "-vf", "scale=448:256",
                                  "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
            if len(raw) == 448 * 256 * 3:
                tiles.append(Image.frombytes("RGB", (448, 256), raw))
        im = Image.new("RGB", (448 * 6, 256))
        for i, t in enumerate(tiles):
            im.paste(t, (448 * i, 0))
        im.save(rv / f"clips_{s['id']}.jpg", quality=82)
    print("→ 人工检查 out/review/clips_*.jpg：换脸、多出人、多手多脚、镜头漂移、背景同学乱动", flush=True)


@stage("amb")
def amb():
    """有动作音效的镜头（amb: true）：用同一张首帧另拍一支「H3 原生音效」版，听写确认没有人声后，只取它的音轨当环境音。"""
    res = {}; todo = []
    picks = load_picks()
    for s in SHOTS:
        if not s.get("amb"):
            continue
        od = OUT / "h3" / f"{s['id']}_amb"; od.mkdir(parents=True, exist_ok=True)
        if not (od / "clip.mp4").exists():
            spec = h3_spec(s, shot_secs(s, picks), [])
            spec["seed"] = int(s.get("amb_seed", spec["seed"]))      # 不写 audio 栏位＝H3 原生音效
            (od / "spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
            todo.append(od)
    render_h3(todo)
    for s in SHOTS:
        if not s.get("amb"):
            continue
        od = OUT / "h3" / f"{s['id']}_amb"
        run([PYV, T / "stt.py", "--audio", od / "clip.mp4", "--outdir", od / "stt"], check=False)
        heard = (od / "stt" / "transcript.txt").read_text(encoding="utf-8").strip() if (od / "stt" / "transcript.txt").exists() else ""
        speech = len(re.findall(r"[\u4e00-\u9fff]", heard))
        if speech <= 1:
            res[s["id"]] = str(od / "clip.mp4"); print(f"amb {s['id']}: OK（听写没有人声）", flush=True)
        else:
            print(f"amb {s['id']}: 有人声「{heard}」→ 不用；换 amb_seed 再跑 amb，或改用 sfx/ 音效", flush=True)
    (OUT / "post").mkdir(exist_ok=True)
    (OUT / "post" / "amb.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")


# ------------------------------------------------------------------------------------------------ 剪接、配乐、片尾、成片
def ending_secs():
    e = CFG.get("ending")
    return len(e["cards"]) * e.get("card_dur", 3.3) + e.get("title_dur", 7.5) if e else 0.0


@stage("edl")
def edl():
    """时间轴：依配音长度与 cut_in／cut_out／tail 算每镜在成片中的位置，写 out/post/edl.json（cut、review 都读它）。
    cut_in＝裁掉镜头开头几秒（H3 常晚开口）；cut_out＝"full" 用到镜尾，不写＝台词结束＋tail 秒（反应停顿）。
    H3 自己念的台词（source h3）用听写抓到的实际开口时间、不提前（嘴型本来就对齐）；BreezyVoice 的照 line.at 并提前 say_lead 秒。"""
    picks = load_picks()
    amb_files = json.loads((OUT / "post" / "amb.json").read_text(encoding="utf-8")) if (OUT / "post" / "amb.json").exists() else {}
    t, rows = 0.0, []
    for s in SHOTS:
        # 修剪点一律对齐 1/24 秒：cut 阶段每段用 -frames:v 取整数格，没对齐的话每镜多／少零点几格、累积起来画面会落后声音
        cd = dur(OUT / "h3" / s["id"] / "clip.mp4"); a = round(float(s.get("cut_in", 0.0)) * FPS) / FPS; b = s.get("cut_out"); lines = []
        if s.get("line"):
            i = line_index(s["id"]); ln = s["line"]; p = picks[str(i)]; d = dur(p["file"])
            at = float(p.get("at", ln["at"])); lead = 0.0 if p.get("source") == "h3" else MIX.get("say_lead", 0.2)
            lines.append(dict(id=f"line{i}", who=ln["who"], text=ln["text"], file=p["file"],
                              film_start=round(t + at - a - lead, 3), film_end=round(t + at - a - lead + d, 3)))
            if b is None:
                b = at + d + s.get("tail", MIX.get("default_tail", 0.55))
        b = cd if b in (None, "full") else min(float(b), cd)
        b = min(round(b * FPS), int(cd * FPS + 1e-6)) / FPS
        rows.append(dict(id=s["id"], start=round(t, 3), dur=round(b - a, 3), src_in=a, src_out=round(b, 3), lines=lines, amb=amb_files.get(s["id"])))
        t += b - a
    e = dict(shots=rows, story_end=round(t, 3), total=round(t + ending_secs(), 3))
    (OUT / "post").mkdir(exist_ok=True)
    (OUT / "post" / "edl.json").write_text(json.dumps(e, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"本片 {t:.2f} 秒＋片尾 {ending_secs():.1f} 秒＝{e['total']:.2f} 秒", flush=True)


def load(p):
    import numpy as np
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(p), "-ar", str(SR), "-ac", "1", "-f", "f32le", "-"], capture_output=True)
    return np.frombuffer(r.stdout, np.float32).copy()


@stage("music")
def music():
    """配乐：Music 3 纯器乐多 seed → BS-RoFormer 分离 → 挑人声残留最少、长度够的那首的纯器乐轨。"""
    import numpy as np
    e = json.loads((OUT / "post" / "edl.json").read_text(encoding="utf-8")); secs = int(e["total"] + 4)
    m = CFG["music"]; md = OUT / "music"; md.mkdir(exist_ok=True)
    (md / "cap.txt").write_text(m["caption"], encoding="utf-8")
    (md / "lyr.txt").write_text("[Intro]\n" + "[Instrumental]\n" * 14 + "[Outro]\n[Instrumental]\n", encoding="utf-8")   # 少于 14 个会太短；加 Verse 会冒人声
    for sd_ in m.get("seeds", [7, 23, 51]):
        sd = md / f"s{sd_}"; sd.mkdir(exist_ok=True)
        if not list(sd.glob("*.flac")):
            run([PYH3, T / "gen_music3.py", "--caption-file", md / "cap.txt", "--lyrics-file", md / "lyr.txt", "--seconds", secs, "--seed", sd_,
                 "--prefix", f"audio/MM3/film_{sd_}", "--out", sd])
    free_comfy(); best = None
    for sd_ in m.get("seeds", [7, 23, 51]):
        sd = md / f"s{sd_}"; src = next(sd.glob("*.flac"))
        if not list(sd.glob("*Instrumental*.wav")):
            run([SEP, src, "--model_filename", "model_bs_roformer_ep_317_sdr_12.9755.ckpt", "--model_file_dir", Path(os.environ.get("AI_ROOT", r"C:\AI")) / "Voice" / "models" / "separator",
                 "--output_dir", sd, "--output_format", "WAV"])
        voc = load(next(sd.glob("*Vocals*.wav"))); ins = load(next(sd.glob("*Instrumental*.wav")))
        ratio = float(np.sqrt((voc ** 2).mean()) / (np.sqrt((ins ** 2).mean()) + 1e-9)); d = len(ins) / SR
        print(f"music s{sd_}: 人声残留 {ratio:.4f}，{d:.1f} 秒", flush=True)
        if d >= e["total"] and (best is None or ratio < best[0]):
            best = (ratio, next(sd.glob("*Instrumental*.wav")))
    if best is None:
        raise SystemExit("没有一首配乐够长：把 music.seeds 换掉再跑 music")
    (OUT / "post" / "music_pick.json").write_text(json.dumps(dict(file=str(best[1]), vocal_ratio=best[0]), ensure_ascii=False), encoding="utf-8")


@stage("ending")
def ending():
    """片尾：特写静帧＋AI 工具名单＋片名（templates/ending）。MiniMax Music3 授权要求标示、公开内容要标示 AI 生成。"""
    e = CFG.get("ending")
    if not e:
        return
    from PIL import Image
    ed = OUT / "ending"; (ed / "frames").mkdir(parents=True, exist_ok=True)
    cards = []
    up_name = {"flashvsr": "FlashVSR", "lanczos": "lanczos"}.get(UPSCALE)        # 片尾名单照实际做法写（2026-10-10 新 agent 测试指出）
    for i, tools in enumerate(e["cards"]):
        sid = e["closeups"][i % len(e["closeups"])]
        Image.open(OUT / "first" / f"{sid}.png").convert("RGB").save(ed / "frames" / f"close{i + 1}.png")
        if up_name:
            tools = [[t[0].replace("RTX VSR", up_name), t[1]] for t in tools]
        cards.append(dict(image=f"frames/close{i + 1}.png", tools=tools))
    header = e.get("header", "本片使用的 AI 工具")
    if "本机" in header and (os.name != "nt" or H3_BACKEND in ("colab", "both")):
        header = "本片使用的 AI 工具（" + ("在 Google Colab 执行" if os.name != "nt" else
                                       "影片在本机与 Google Colab 生成" if H3_BACKEND == "both" else "影片在 Google Colab 生成") + "）"
    cfg = {"_base": str(ed), "title": e.get("title", CFG["title"]), "header": header, "card_dur": e.get("card_dur", 3.3),
           "title_dur": e.get("title_dur", 7.5), "out": "ending.mp4", "cards": cards}
    (ed / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8")
    run([PYH3, REPO / "templates" / "ending" / "render_ending.py", ed / "config.json"])


def ass_time(t):
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


@stage("cut")
def cut():
    """RTX VSR 放大 → 依 edl 剪接 → 混音（台词提前 say_lead 秒、配乐台词期间压低）→ 响度 → 1080p 烧字幕 → 手机版。"""
    import numpy as np
    e = json.loads((OUT / "post" / "edl.json").read_text(encoding="utf-8")); post = OUT / "post"
    vsr = post / "vsr"; vsr.mkdir(exist_ok=True); seg = post / "seg"; seg.mkdir(exist_ok=True); parts = []
    for r in e["shots"]:
        src = OUT / "h3" / r["id"] / "clip.mp4"; v = vsr / f"{r['id']}.mp4"
        if v.exists() and v.stat().st_mtime < src.stat().st_mtime:
            v.unlink()                               # 重拍过：重新放大（upscale_vsr.py 不覆写旧档）
        if UPSCALE == "lanczos":                     # Linux／Colab 没有 RTX VSR：直接用下面 ffmpeg 的 lanczos 放大
            v = src
        elif UPSCALE == "flashvsr":
            fv = vsr / r["id"]
            if not (fv / "clip.mp4").exists() or (fv / "clip.mp4").stat().st_mtime < src.stat().st_mtime:
                run([PYH3, T / "flashvsr_cli.py", src, fv])
            v = fv / "clip.mp4"
        elif not v.exists():
            run([PYH3, T / "upscale_vsr.py", "--source", src, "--output", v])
        p = seg / f"{r['id']}.mp4"
        run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{r['src_in']:.3f}", "-i", v, "-frames:v", str(round(r["dur"] * FPS)), "-an",
             "-vf", "scale=1920:1080:flags=lanczos,fps=24,format=yuv420p", "-c:v", "libx264", "-crf", "14", "-preset", "medium", p])
        parts.append(p)
    if CFG.get("ending"):
        parts.append(OUT / "ending" / "ending.mp4")
    (post / "list.txt").write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", post / "list.txt", "-c", "copy", post / "video.mp4"])
    vtotal = dur(post / "video.mp4"); n = int(vtotal * SR) + SR
    voice = np.zeros(n, np.float32); amb_ = np.zeros(n, np.float32); duck = np.ones(n, np.float32)
    under = MIX.get("music_under_lines", 0.30)
    for r in e["shots"]:
        for l in r["lines"]:
            a = load(l["file"]); s0 = int(l["film_start"] * SR); voice[s0:s0 + len(a)] += a[: n - s0]
            duck[max(0, int((l["film_start"] - 0.25) * SR)):int((l["film_end"] + 0.35) * SR)] = under
        if r.get("amb"):                             # amb 阶段确认过没有人声的 H3 原生音效
            a = load(r["amb"])[int(r["src_in"] * SR):int(r["src_out"] * SR)]
            fade = np.minimum(1, np.minimum(np.arange(len(a)) / (0.15 * SR), (len(a) - np.arange(len(a))) / (0.15 * SR)))
            s0 = int(r["start"] * SR); amb_[s0:s0 + len(a)] += (a * fade * 0.8)[: n - s0]
    k = int(0.12 * SR); duck = np.convolve(duck, np.ones(k) / k, mode="same")
    mus = load(json.loads((post / "music_pick.json").read_text(encoding="utf-8"))["file"])[:n]; mus = np.pad(mus, (0, n - len(mus)))
    mus = mus / (np.sqrt((mus[: int(e["story_end"] * SR)] ** 2).mean()) + 1e-9) * MIX.get("music_bed_rms", 0.035)
    t = np.arange(n) / SR
    mix = voice + amb_ + mus * duck * np.clip((vtotal - t) / 3.0, 0, 1) * np.clip(t / 0.8, 0, 1)
    raw = post / "mix_raw.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", "-c:a", "pcm_f32le", str(raw)],
                   input=mix[: int(vtotal * SR)].astype(np.float32).tobytes(), check=True)
    # 响度：量 → 固定增益 → 限幅（alimiter 一定要 level=false，预设会把峰值拉到 0 dBFS）→ 再量一次、差太多就补一次
    target = MIX.get("target_lufs", -15.5); gain = 0.0
    for _ in range(3):
        r = subprocess.run(["ffmpeg", "-i", str(raw), "-af", f"volume={gain:.2f}dB,alimiter=limit=0.78:level=false:attack=2:release=80,ebur128",
                            "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace")
        m = re.findall(r"I:\s*(-?[\d.]+) LUFS", r.stderr); got = float(m[-1]) if m else target
        if abs(got - target) <= 0.4:
            break
        gain += target - got
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-af", f"volume={gain:.2f}dB,alimiter=limit=0.78:level=false:attack=2:release=80", "-ar", str(SR),
         post / "mix.wav"])
    # 字幕（ASS，依说话者上色，放大到 1080p 之后才烧）
    hdr = ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n\n[V4+ Styles]\n"
           "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, "
           "Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
    for k, c in CHARS.items():
        hdr += f"Style: {k},{SUB_FONT_NAME},58,{c.get('sub_color', '&H00FFFFFF')},&H000000FF,&H00101010,&H80000000,-1,0,0,0,100,100,1,0,1,4,1,2,60,60,70,1\n"
    ev = "\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    caps = sorted([(l, r) for r in e["shots"] for l in r["lines"]], key=lambda x: x[0]["film_start"])
    for i, (l, r) in enumerate(caps):
        a = l["film_start"] - 0.05; b = l["film_end"] + 0.45
        if i + 1 < len(caps):
            b = min(b, caps[i + 1][0]["film_start"] - 0.1)
        b = min(b, r["start"] + r["dur"] - 0.04)
        ev += f"Dialogue: 0,{ass_time(a)},{ass_time(b)},{l['who']},,0,0,0,,{CHARS[l['who']]['name']}：{l['text']}\n"
    (post / "subs.ass").write_text(hdr + ev, encoding="utf-8")
    (OUT / "cut").mkdir(exist_ok=True)
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", "post/video.mp4", "-i", "post/mix.wav", "-vf", "subtitles=post/subs.ass", "-map", "0:v", "-map", "1:a",
         "-c:v", "libx264", "-crf", "16", "-preset", "slow", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", "-shortest",
         "cut/film_1080p.mp4"])
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", OUT / "cut" / "film_1080p.mp4", "-vf", "scale=1280:720", "-c:v", "libx264", "-crf", "26",
         "-c:a", "aac", "-b:a", "128k", OUT / "cut" / "film_720p_phone.mp4"])
    print(f"成片 out/cut/film_1080p.mp4（{vtotal:.2f} 秒）", flush=True)


@stage("review")
def review():
    """自审五遍（review.py）：1 逐镜抽格、2 成片听写、3 杂讯、4 黑画面／定格／响度、5 切点明暗／台词重叠／台词被镜尾切掉。"""
    c = OUT / "cut" / "film_1080p.mp4"
    env = {"AI_TOOLS": str(REPO / "tools")}                      # review.py 的 fonts.py 跟 film.json 的 repo_dir 走（范本搬到别的资料夹也能跑）
    for r in (run([PYH3, HERE / "review.py", c], check=False, env=env), run([PYV, HERE / "review.py", c, "--asr"], check=False, env=env)):
        print(r.stdout[-3000:], flush=True)
        if r.returncode != 0:                                    # 自审失败不能悄悄略过
            print(f"⚠ review.py 失败（{r.returncode}）：\n{r.stderr[-2000:]}", flush=True)
    print("→ 看 out/review/：film_1080p_pass1.jpg、pass5_cuts.jpg、review.json、asr.json；最后一定要人看成片", flush=True)


STAGES = dict(chars=chars, masters=masters, frames=frames, voices=voices, h3=h3, amb=amb, edl=edl, music=music, ending=ending, cut=cut, review=review)

if __name__ == "__main__":
    names = [a for i, a in enumerate(ARGS) if a in STAGES]
    need = {"chars", "masters", "frames", "music"} | ({"h3", "amb"} if H3_BACKEND in ("local", "both") else set())
    print(f"[make_film] H3_BACKEND={H3_BACKEND}  UPSCALE={UPSCALE}", flush=True)
    if need & set(names or STAGES) and not comfy_ok():
        sys.exit(f"ComfyUI not running at {HOST}: call configs\\profile.cmd, then C:\\AI\\tools\\start_comfy.cmd")
    for name in (names or list(STAGES)):
        STAGES[name]()
    print("timing", json.dumps({k: v["sec"] for k, v in timing.items()}, ensure_ascii=False), flush=True)
