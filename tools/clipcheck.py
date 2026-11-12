"""逐镜抓「H3 自己切镜／构图漂走」：每 0.5 秒取一格算跟首帧的相关系数，最低值 < 0.7 就标 CHECK，要人看。
H3 常在 1–2.4 秒自己切到别的构图（原专案常切到墙上挂旗子、贴红色标语的教室），没台词的短反应镜最常发生。
抓到的镜：限制句加「never cuts to another shot」「no flags, banners or national emblems」，尾帧锁首帧重抽；
台词讲完才切的，剪掉切镜之后的部分就好。走位多的镜会误报，用总表看。

用法：python tools/clipcheck.py <资料夹> [镜号...]
  资料夹里有 h3/<镜号>/clip.mp4 就查那些；没有就查资料夹里所有 .mp4（镜号＝档名）。
输出 <资料夹>/review/clipcheck.jpg（每镜 0%、50%、100% 三格）与 clipcheck.json（每镜的相关系数序列）。
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fonts import font  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
    print(__doc__)
    sys.exit(0)
EP = Path(sys.argv[1]).resolve()
if (EP / "h3").is_dir():
    found = {p.name: p / "clip.mp4" for p in sorted((EP / "h3").iterdir()) if (p / "clip.mp4").exists()}
else:
    found = {p.stem: p for p in sorted(EP.glob("*.mp4"))}
clips = {k: found[k] for k in sys.argv[2:]} if sys.argv[2:] else found
R = EP / "review"
R.mkdir(exist_ok=True)


def frames(p, fps=2, w=320, h=180):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-vf", f"fps={fps},scale={w}:{h}", "-f", "rawvideo", "-pix_fmt",
                          "rgb24", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)


def corr(a, b):
    a = a.astype(np.float32).mean(2).ravel(); b = b.astype(np.float32).mean(2).ravel()
    a -= a.mean(); b -= b.mean()
    return float((a * b).sum() / (np.sqrt((a * a).sum() * (b * b).sum()) + 1e-9))


out, rows = {}, []
fnt = ImageFont.truetype(font("jh"), 18)
for k, path in clips.items():
    f = frames(path)
    cs = [round(corr(f[0], x), 2) for x in f]
    out[k] = dict(min_corr=min(cs), at=cs.index(min(cs)) / 2, series=cs)
    row = Image.new("RGB", (960, 180))
    for i, x in enumerate([f[0], f[len(f) // 2], f[-1]]):
        row.paste(Image.fromarray(x), (i * 320, 0))
    d = ImageDraw.Draw(row)
    flag = " CHECK" if min(cs) < 0.7 else ""
    d.rectangle([0, 0, 230, 24], fill="black")
    d.text((4, 2), f"{k} min {min(cs):.2f}{flag}", fill="red" if flag else "yellow", font=fnt)
    rows.append(row)
    print(k, f"min corr {min(cs):.2f} @ {cs.index(min(cs)) / 2:.1f}s{flag}", flush=True)
cols = 2
n = (len(rows) + cols - 1) // cols
sheet = Image.new("RGB", (960 * cols, 180 * max(n, 1)), "white")
for i, r in enumerate(rows):
    sheet.paste(r, ((i // n) * 960, (i % n) * 180))
sheet.save(R / "clipcheck.jpg", quality=85)
(R / "clipcheck.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
