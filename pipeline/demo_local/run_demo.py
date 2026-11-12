"""全本地示范片：从零做出一支约 20 秒、4 镜的小短片，证明安装好的工作流可以完整跑通。不需要任何外部素材。
H3 venv 执行（ComfyUI 要先开：call configs\\profile.cmd → C:\\AI\\tools\\start_comfy.cmd）：
  C:\\AI\\H3\\venv\\Scripts\\python.exe pipeline\\demo_local\\run_demo.py [stage ...]
stage：chars → frames → voices → h3 → music → cut（不给就全部依序跑；已完成的档案会跳过，可续跑）
输出 pipeline/demo_local/out/：角色定妆照、首帧、配音、H3 片段、配乐、cut/demo_1080p.mp4、timing.json

剧情（4 镜）：放学后的教室。学生小芸举手问老师明天考不考，老师说「要考」，小芸愣住，老师笑著补一句「考你会的」。
做法都是本专案实测过的：
- 角色：Qwen-Image 2.1 生「单张半身定妆照」（灰底、正面）。
- 首帧：Qwen-Image-Edit 2511 附定妆照当参考（不训练就能保持长相、又会照剧本演），直接出 1344×768。
- 声音：Breeze TTS 2 用文字描述设计角色声音 → BreezyVoice 以它为参考念台词（每句 8 候选）→ faster-whisper＋声调比对（对照 edge-tts 标准台湾国语）自动挑最好的。
- 影片：H3 DMAD 4 步、只给首帧、台词放进固定音轨（不说话的镜头给静音）。
- 配乐：MiniMax Music 3 纯器乐；放大：RTX VSR。"""
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
OUT = HERE / "out"; OUT.mkdir(exist_ok=True)
T = Path(os.environ.get("AI_TOOLS", r"C:\AI\tools"))
PYH3 = os.environ.get("PY_H3", r"C:\AI\H3\venv\Scripts\python.exe")
PYV = os.environ.get("PY_VOICE", r"C:\AI\Voice\venv\Scripts\python.exe")
PYB = os.environ.get("PY_BREEZE", r"C:\AI\BreezeTTS\venv\Scripts\python.exe")
PYBV = os.environ.get("PY_BREEZYVOICE", r"C:\AI\BreezyVoice\venv\Scripts\python.exe")
SEP = str(Path(PYV).parent / "audio-separator.exe")
HOST = os.environ.get("COMFY_HOST", "http://127.0.0.1:8188")
FONT = "C:/Windows/Fonts/msjhbd.ttc"
TIMING = OUT / "timing.json"
timing = json.loads(TIMING.read_text(encoding="utf-8")) if TIMING.exists() else {}

CHARS = {
    "yun": dict(name="小芸", look="Xiaoyun, a bright 11-year-old Taiwanese schoolgirl with a short black bob haircut and straight bangs, round friendly face, "
                "wearing a plain white short-sleeve school shirt",
                voice_design="A bright, clear 11-year-old Taiwanese girl, curious and lively, natural Taiwanese Mandarin accent.",
                voice_sample="老师，我想问一下，明天的数学课要不要带量角器？我怕又忘记了。", h3_voice="a bright, clear 11-year-old girl's voice"),
    "lin": dict(name="林老师", look="Mr. Lin, a kind Taiwanese male teacher in his early thirties with short neat black hair and thin black-rimmed glasses, "
                "wearing a light blue button-up shirt",
                voice_design="A calm, warm Taiwanese man in his thirties, a gentle teacher, relaxed natural Taiwanese Mandarin accent.",
                voice_sample="好，大家把课本收起来，今天我们先复习上礼拜教的内容，有问题随时举手。", h3_voice="a calm, warm adult male voice"),
}
CINE = ("A cinematic film still from a Taiwanese coming-of-age movie, shot on Kodak Vision3 500T film with an anamorphic 50mm lens at f/2. "
        "Late-afternoon golden-hour sun pours in low through the classroom windows, warm backlight with a glowing rim light, hazy air with visible dusty "
        "light beams, warm amber color grade, shallow depth of field, subtle film grain. ")
ROOM = "an empty Taiwanese elementary school classroom after school, wooden desks, a green chalkboard with nothing written on it"
SHOTS = [
    dict(id="S1", refs=["yun"], dur=4.4, line=("yun", "老师，明天要考试吗？", 0.5),
         frame="Medium shot at eye level: the girl from <image1> sits at her wooden desk in " + ROOM + ", raising one hand and looking toward the front "
               "of the room with a curious, slightly worried face.",
         action="The girl keeps her hand raised and asks her question toward the front of the room, a little worried."),
    dict(id="S2", refs=["lin"], dur=3.6, line=("lin", "要考。", 1.2),   # 单字台词「考。」VoxCPM2 会念成乱音（实测），至少两三个字
         frame="Medium close-up at eye level: the man from <image1> stands at the front of " + ROOM + " next to the green chalkboard, holding a stack of "
               "papers, looking at the camera with a calm, neutral face.",
         action="The teacher pauses for a beat, then answers with one short word, calm and neutral."),
    dict(id="S3", refs=["yun"], dur=3.6, line=None,
         frame="Close-up: the girl from <image1> at her desk in " + ROOM + ", frozen in shock, eyes wide, mouth slightly open, her raised hand still in the air.",
         action="The girl stays frozen in shock; her raised hand slowly droops. She does not speak; her lips stay closed after the first second."),
    dict(id="S4", refs=["lin", "yun"], dur=5.1, line=("lin", "考你会的。", 1.0),
         frame="Medium two-shot: in " + ROOM + ", the man from <image1> stands beside the desk of the girl from <image2>, smiling gently down at her; "
               "she looks up at him, surprised. Only these two people.",
         action="The teacher smiles and says his line gently; the girl's shocked face slowly relaxes into a relieved smile. Only the teacher speaks."),
]


def comfy_ok():
    try:
        urllib.request.urlopen(HOST + "/system_stats", timeout=5); return True
    except Exception:
        return False


def free_comfy():
    try:
        r = urllib.request.Request(HOST + "/free", data=json.dumps({"unload_models": True, "free_memory": True}).encode(), headers={"Content-Type": "application/json"})
        urllib.request.urlopen(r, timeout=30)
    except Exception:
        pass
    time.sleep(5)


def run(cmd, cwd=OUT, check=True):
    r = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"})
    if check and r.returncode != 0:
        raise SystemExit(f"FAILED: {' '.join(map(str, cmd))[:200]}\n{(r.stdout + r.stderr)[-1500:]}")
    return r


def newest(d, ext=".png"):
    fs = sorted(Path(d).glob(f"*{ext}"), key=lambda f: f.stat().st_mtime)
    return fs[-1] if fs else None


def stage(name):
    def deco(fn):
        def wrap():
            t0 = time.time(); fn(); timing[name] = round(time.time() - t0, 1)
            TIMING.write_text(json.dumps(timing, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"[stage] {name} {timing[name]}s", flush=True)
        return wrap
    return deco


@stage("chars")
def chars():
    for k, c in CHARS.items():
        dst = OUT / "chars" / f"{k}.png"
        if dst.exists():
            continue
        p = ("Studio character reference photo, single person only, one image (not a collage), medium close-up bust portrait facing the camera, "
             "plain light grey seamless background, soft even studio light, sharp focus, realistic photograph. " + c["look"] + ", gentle natural expression. "
             "No text, no watermark.")
        run([PYH3, str(T / "gen_image.py"), "--prompt", p, "--width", "1024", "--height", "1024", "--seed", "11", "--prefix", f"demo/char_{k}", "--out", "chars"])
        newest(OUT / "chars").rename(dst)


@stage("frames")
def frames():
    for s in SHOTS:
        dst = OUT / "first" / f"{s['id']}.png"
        if dst.exists():
            continue
        # 参考图之外，每一镜都要照抄完整外观描述（只写「Keep the same person」时，Qwen-Edit 会掉眼镜、换发型；2026-10-07 实测）
        keep = " ".join(f"Keep exactly the same person as <image{i}>: same face, hairstyle and clothes — {CHARS[k]['look']}."
                        for i, k in enumerate(s["refs"], 1))
        p = keep + " New photo: " + CINE + s["frame"] + " No text, no watermark, no captions."
        cmd = [PYH3, str(T / "gen_image.py"), "--model", "qwen-edit", "--width", "1344", "--height", "768", "--prompt", p, "--seed", "5101",
               "--prefix", f"demo/{s['id']}", "--out", "first"]
        for k in s["refs"]:
            cmd += ["--ref", str(OUT / "chars" / f"{k}.png")]
        run(cmd)
        newest(OUT / "first").rename(dst)


@stage("voices")
def voices():
    free_comfy()
    (OUT / "voice").mkdir(exist_ok=True)
    jobs = [dict(name=f"ref_{k}", text=c["voice_sample"], instruction=c["voice_design"], seed=7) for k, c in CHARS.items()]
    lines = [s["line"] for s in SHOTS if s["line"]]
    # 挑音用的「台湾国语答案卷」：预设 edge-tts（原专案验收过的做法；只产生参考音、不进成片，要连网、免费免帐号）。
    # 没网路时改用 Breeze 产生（2026-10-07 实测：跟 edge-tts 挑出的第一名只有 4/19 句相同，可靠度较低）。
    for i, (who, txt, _) in enumerate(lines):
        w = OUT / "voice" / f"tw_{i}.wav"
        if w.exists():
            continue
        mp3 = OUT / "voice" / f"tw_{i}.mp3"
        edge_voice = "zh-TW-HsiaoChenNeural" if who == "yun" else "zh-TW-YunJheNeural"
        r = run([PYV, str(T / "gen_voice.py"), "--engine", "edge", "--text", txt, "--voice", edge_voice, "--out", str(mp3)], check=False)
        if r.returncode == 0 and mp3.exists():
            run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3), "-ar", "48000", "-ac", "1", str(w)])
        else:
            print("edge-tts unavailable, falling back to Breeze reference for line", i, flush=True)
            jobs.append(dict(name=f"tw_{i}", text=txt, instruction="A clear, neutral standard Taiwanese Mandarin news-reading voice, calm, precise tones.", seed=11))
    (OUT / "breeze.json").write_text(json.dumps(dict(out_dir="voice", jobs=jobs), ensure_ascii=False), encoding="utf-8")
    run([PYB, str(T / "breeze_batch.py"), "breeze.json"])
    # 台词：BreezyVoice 用设计好的声音念，每句 8 个 seed → 自动挑（听写的拼音声调要全对，再比台湾国语腔调分数）
    # 念不准的字直接在台词标注音，例如「连假[:ㄐㄧㄚ4]」（字幕用不含标记的原文）。
    bv_jobs = [dict(name=f"line{i}", text=txt, ref_audio=f"voice/ref_{who}.wav", ref_text=CHARS[who]["voice_sample"], tw_ref=f"voice/tw_{i}.wav", seeds=8)
               for i, (who, txt, _) in enumerate(lines)]
    (OUT / "bv.json").write_text(json.dumps(dict(out_dir="voice/bv", jobs=bv_jobs), ensure_ascii=False, indent=1), encoding="utf-8")
    run([PYBV, str(T / "breezyvoice_batch.py"), "bv.json"])
    run([PYV, str(T / "breezyvoice_pick.py"), "bv.json"])
    bp = json.loads((OUT / "voice" / "bv" / "picks.json").read_text(encoding="utf-8"))
    picks = {}
    for i, (who, txt, _) in enumerate(lines):
        p = bp[f"line{i}"]
        if p["needs_review"]:
            best = next(c for c in p["cands"] if c["file"] == p["pick"])
            raise SystemExit(f"台词「{txt}」8 个候选听写都不对（最好的听成「{best['asr']}」）。念错的字请在台词标注音（例：假[:ㄐㄧㄚ4]）或换说法，再删掉 voice/bv 重跑。")
        best = next(c for c in p["cands"] if c["file"] == p["pick"])
        picks[i] = dict(file=str(OUT / "voice" / "bv" / f"line{i}.wav"), heard=best["asr"], tw_score=best.get("tw_score"))
        print("pick", txt, "→", p["pick"], best["asr"], flush=True)
    (OUT / "voice_picks.json").write_text(json.dumps(picks, ensure_ascii=False, indent=1), encoding="utf-8")


def frames_for(d):
    n = 0
    while 17 * n + 5 < d * 24:
        n += 1
    return 17 * n + 5


@stage("h3")
def h3():
    picks = json.loads((OUT / "voice_picks.json").read_text(encoding="utf-8"))
    li = 0
    for s in SHOTS:
        od = OUT / "h3" / s["id"]
        if (od / "clip.mp4").exists():
            li += 1 if s["line"] else 0; continue
        od.mkdir(parents=True, exist_ok=True)
        secs = frames_for(s["dur"]) / 24; sr = 48000; buf = bytearray(int(secs * sr) * 2)
        dlg = []
        if s["line"]:
            who, txt, at = s["line"]
            r = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", picks[str(li)]["file"], "-ar", str(sr), "-ac", "1", "-f", "s16le", "-"], capture_output=True)
            st = int(at * sr) * 2; seg = r.stdout[: len(buf) - st]; buf[st:st + len(seg)] = seg
            dlg = [dict(subject=who, line=txt, lang="Chinese", after="Right after the line the speaker's lips close and stay closed.")]
            li += 1
        with wave.open(str(od / "guide.wav"), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(bytes(buf))   # 不说话的镜头＝整段静音，防止角色自己开口
        subs = [dict(key=k, desc=CHARS[k]["look"], voice=CHARS[k]["h3_voice"]) for k in s["refs"]]
        spec = dict(duration=round(secs - 0.02, 3), size=[1344, 768], seed=20261007, steps=14, draft=True,
                    style="a realistic cinematic live-action Taiwanese film shot on anamorphic lenses, 35mm grain, warm light with drifting dust",
                    setting="a Taiwanese elementary school classroom after school", first_frame=str(OUT / "first" / f"{s['id']}.png"), subjects=subs,
                    audio={"fixed": {"file": str(od / "guide.wav")}},
                    shots=[dict(camera="The camera holds a static shot on a tripod.", action=s["action"], dialogue=dlg)],
                    constraints=["No new people appear that are not already in the first frame; no captions and no readable text.",
                                 "The camera stays locked on the tripod; no zoom, no pan."],
                    soundscape="Quiet empty classroom room tone after school, faint distant playground sounds.", music="N/A")
        (od / "spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
        run([PYH3, str(T / "h3_shot.py"), str(od / "spec.json"), "--out", str(od)])


@stage("music")
def music():
    if newest(OUT / "music", ".flac"):
        return
    (OUT / "cap.txt").write_text("Genre: light playful school comedy underscore, purely instrumental film score. BPM 100, key G major.\nVocal: NONE. "
                                 "No singing, no humming.\nArrangement: pizzicato strings, marimba, glockenspiel, upright bass.", encoding="utf-8")
    (OUT / "lyr.txt").write_text("[Intro]\n" + "[Instrumental]\n" * 14 + "[Outro]\n[Instrumental]\n", encoding="utf-8")
    run([PYH3, str(T / "gen_music3.py"), "--caption-file", "cap.txt", "--lyrics-file", "lyr.txt", "--seconds", "40", "--seed", "7",
         "--prefix", "audio/MM3/demo", "--out", "music"])
    free_comfy()
    run([SEP, str(newest(OUT / "music", ".flac")), "--model_filename", "model_bs_roformer_ep_317_sdr_12.9755.ckpt", "--model_file_dir", r"C:\AI\Voice\models\separator",
         "--output_dir", str(OUT / "music"), "--output_format", "WAV"])


@stage("cut")
def cut():
    (OUT / "cut").mkdir(exist_ok=True); (OUT / "vsr").mkdir(exist_ok=True)
    parts, t, subs = [], 0.0, []
    for s in SHOTS:
        v = OUT / "vsr" / f"{s['id']}.mp4"
        if not v.exists():
            run([PYH3, str(T / "upscale_vsr.py"), "--source", str(OUT / "h3" / s["id"] / "clip.mp4"), "--output", str(v)])
        d = float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(v)]).stdout)
        if s["line"]:
            subs.append((t + s["line"][2], t + s["line"][2] + 1.6, CHARS[s["line"][0]]["name"] + "：" + s["line"][1]))
        parts.append(v); t += d
    (OUT / "cut" / "list.txt").write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", "cut/list.txt", "-c", "copy", "cut/joined.mp4"])
    inst = next((OUT / "music").glob("*Instrumental*.wav"))
    srt = "".join(f"{i}\n{int(a // 3600):02d}:{int(a % 3600 // 60):02d}:{a % 60:06.3f}".replace(".", ",") + " --> " +
                  f"{int(b // 3600):02d}:{int(b % 3600 // 60):02d}:{b % 60:06.3f}".replace(".", ",") + f"\n{txt}\n\n" for i, (a, b, txt) in enumerate(subs, 1))
    (OUT / "cut" / "subs.srt").write_text(srt, encoding="utf-8")
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", "cut/joined.mp4", "-i", str(inst), "-filter_complex",
         f"[1:a]volume=0.18,afade=t=out:st={t - 2:.2f}:d=2[m];[0:a][m]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-16:TP=-1.5[a];"
         f"[0:v]subtitles=cut/subs.srt:force_style='FontName=Microsoft JhengHei,FontSize=22,Outline=2'[v]",
         "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "18", "-c:a", "aac", "-b:a", "192k", "cut/demo_1080p.mp4"])
    print("[done]", OUT / "cut" / "demo_1080p.mp4", f"{t:.1f}s", flush=True)


STAGES = dict(chars=chars, frames=frames, voices=voices, h3=h3, music=music, cut=cut)

if __name__ == "__main__":
    if not comfy_ok():
        sys.exit(f"ComfyUI not running at {HOST}: call configs\\profile.cmd, then C:\\AI\\tools\\start_comfy.cmd")
    for name in (sys.argv[1:] or list(STAGES)):
        STAGES[name]()
    print("timing", json.dumps(timing, ensure_ascii=False))
