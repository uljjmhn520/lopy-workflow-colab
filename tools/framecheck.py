"""每秒一格审片：把成片每秒截一张，拼成一张 12 格（4×3、每格 480 宽）的总表，每格标「秒数｜镜号＋镜内秒数」。
一张一张看：背景突然冒人、脸或手糊掉、道具不连戏、墙上冒出旗子标语，都要修，没修的镜头不能用。
格子比一般缩图大，看得出背景的人。

用法：
  python tools/framecheck.py <成片.mp4> [--tl timeline.json] [--out 资料夹] [--cols 4] [--rows 3] [--w 480] [--fps 1]
  python tools/framecheck.py h3/K05/clip.mp4 --fps 2      → 单一镜半秒一格
输出 <out>/fc_01.jpg、fc_02.jpg…（预设 out＝影片旁边的 fc_<档名>/）。
timeline.json 格式：{"shots": {"镜号": {"start": 秒, "dur": 秒}, ...}}；没给就只标秒数。
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fonts import font  # noqa: E402

ap = argparse.ArgumentParser(description="每秒一格审片总表")
ap.add_argument("video"); ap.add_argument("--tl"); ap.add_argument("--out")
ap.add_argument("--cols", type=int, default=4); ap.add_argument("--rows", type=int, default=3)
ap.add_argument("--w", type=int, default=480); ap.add_argument("--fps", type=float, default=1.0)
a = ap.parse_args()
v = Path(a.video)
out = Path(a.out) if a.out else v.parent / f"fc_{v.stem}"
out.mkdir(parents=True, exist_ok=True)
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(v)],
                           capture_output=True, text=True).stdout)
shots = json.loads(Path(a.tl).read_text(encoding="utf-8"))["shots"] if a.tl else {}


def which(t):
    for k, s in shots.items():
        if s["start"] <= t < s["start"] + s["dur"]:
            return f"{k} +{t - s['start']:.1f}"
    return ""


tmp = out / "_f"
tmp.mkdir(exist_ok=True)
for f in tmp.glob("*.jpg"):
    f.unlink()
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(v), "-vf", f"fps={a.fps}:round=up,scale={a.w}:-2", "-q:v", "3",
                str(tmp / "%04d.jpg")], check=True)
frames = sorted(tmp.glob("*.jpg"))
fnt = ImageFont.truetype(font("jhbd"), 20)
per = a.cols * a.rows
for p in range(0, len(frames), per):
    group = frames[p:p + per]
    fw, fh = Image.open(group[0]).size
    sheet = Image.new("RGB", (a.cols * fw, a.rows * fh), "black")
    d = ImageDraw.Draw(sheet)
    for i, f in enumerate(group):
        x, y = i % a.cols * fw, i // a.cols * fh
        sheet.paste(Image.open(f), (x, y))
        t = (p + i) / a.fps
        d.rectangle([x, y, x + 200, y + 26], fill="black")
        d.text((x + 4, y + 2), f"{t:5.1f}s {which(t)}", fill="yellow", font=fnt)
    sheet.save(out / f"fc_{p // per + 1:02d}.jpg", quality=85)
print(len(frames), "frames →", out, f"({(len(frames) + per - 1) // per} sheets, {dur:.1f}s)")
