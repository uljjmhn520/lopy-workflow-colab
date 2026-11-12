"""挑歌（YuE2／ACE-Step 唱词歌）：量每首拍速，只留目标 BPM（YuE2 约一半会掉到 89 或跳 152），
再用 BS-RoFormer 分人声 → 歌词强制对齐 → 逐句听写，依字对到的比例排序（整首直接听写会幻觉，不要用）。
rap 的听写天生偏低（人工确认全对的 Suno 歌也只量到 0.63–0.70），最后一定要人听。
用法：<Voice venv>/python pick_song.py <输出资料夹> <歌词.txt> [--bpm 143.6]（歌词可含 [Verse] 等段落标签）→ <资料夹>/pick.json
需要：Voice venv 的 faster-whisper、stable-ts、opencc、librosa、audio-separator（模型 model_bs_roformer_ep_317_sdr_12.9755.ckpt）。"""
import re, os, sys, difflib, json
from pathlib import Path
import numpy as np, soundfile as sf, librosa, subprocess
AI = Path(os.environ.get("AI_ROOT", r"C:\AI"))  # AI_ROOT = install root (default C:\AI)
sys.path.insert(0, str(Path(__file__).resolve().parent)); import stt; stt._add_cuda_dll_dirs()
import stable_whisper, opencc
d, lyr = Path(sys.argv[1]), Path(sys.argv[2])
TARGET = float(sys.argv[sys.argv.index("--bpm") + 1]) if "--bpm" in sys.argv else 143.6
lines = [l.strip() for l in lyr.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("[")]
cc = opencc.OpenCC("s2twp"); norm = lambda s: re.sub(r"[^\u4e00-\u9fff]", "", cc.convert(s))
m = stable_whisper.load_faster_whisper("large-v3", device="cuda", compute_type="float16", download_root=str(AI / "Voice" / "models" / "whisper"))
sep = d / "sep"; sep.mkdir(exist_ok=True); rep = {}
for f in sorted(d.glob("*.flac")):
    y, sr = librosa.load(str(f), sr=22050, mono=True)
    bpm = float(np.atleast_1d(librosa.beat.beat_track(y=y, sr=sr)[0])[0])
    if abs(bpm - TARGET) > 1:
        print(f.name, "BPM", round(bpm, 1), "→ 不要"); continue
    voc = next(sep.glob(f"{f.stem}_(Vocals)*"), None)
    if voc is None:
        subprocess.run([str(Path(sys.executable).parent / ("audio-separator.exe" if os.name == "nt" else "audio-separator")), str(f), "--model_filename", "model_bs_roformer_ep_317_sdr_12.9755.ckpt",
                        "--model_file_dir", str(AI / "Voice" / "models" / "separator"), "--output_dir", str(sep), "--output_format", "FLAC"], check=True, capture_output=True)
        voc = next(sep.glob(f"{f.stem}_(Vocals)*"))
    a, vsr = sf.read(str(voc), dtype="float32", always_2d=True); a = a.mean(1)
    res = m.align(str(voc), "\n".join(lines), language="zh", original_split=True); oks = []
    for l, s in zip(lines, res.segments):
        sf.write(d / "_tmp.wav", a[max(0, int((s.start - .3) * vsr)):int((s.end + .3) * vsr)], vsr)
        t = cc.convert("".join(x.text for x in m.transcribe(str(d / "_tmp.wav"), language="zh", vad=False, condition_on_previous_text=False, verbose=None).segments))
        oks.append(sum(b.size for b in difflib.SequenceMatcher(None, norm(l), norm(t), autojunk=False).get_matching_blocks()) / max(1, len(norm(l))))
    rep[f.name] = {"bpm": round(bpm, 1), "char_ok": round(float(np.mean(oks)), 2), "lines_ok": int(sum(o >= .7 for o in oks)), "lines": len(oks)}
    print(f.name, rep[f.name], flush=True)
(d / "_tmp.wav").unlink(missing_ok=True)
(d / "pick.json").write_text(json.dumps(dict(sorted(rep.items(), key=lambda kv: -kv[1]["char_ok"])), ensure_ascii=False, indent=1), encoding="utf-8")
print("排序结果写在", d / "pick.json")
