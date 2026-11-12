"""逐镜查「镜头内整体颜色漂移」（第 9 集：H3 偶尔在第 1–2 秒把布幕／天空的饱和度拉高，同一场前后镜接不起来）。
用法：python colordrift.py <集资料夹> [镜号...] [--th 10]
做法：每 0.5 秒取一格、缩成 64×36，算平均 RGB 与首帧的最大距离；超过门槛（预设 10，0–255 尺度）就列出。
只看整体颜色，人物走动不太影响；出现距离大但画面其实是切镜或打灯的，要人看过再决定。"""
import argparse
import subprocess
from pathlib import Path

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("ep"); ap.add_argument("ids", nargs="*"); ap.add_argument("--th", type=float, default=10)
a = ap.parse_args()
EP = Path(a.ep).resolve()
ids = a.ids or sorted(p.name for p in (EP / "h3").iterdir() if (p / "clip.mp4").exists())
W, H = 64, 36
bad = 0
for k in ids:
    v = EP / "h3" / k / "clip.mp4"
    if not v.exists():
        continue
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(v), "-vf", f"fps=2,scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True).stdout
    x = np.frombuffer(raw, np.uint8)
    n = len(x) // (W * H * 3)
    if n < 2:
        continue
    m = x[:n * W * H * 3].reshape(n, H, W, 3).astype(np.float32).mean(axis=(1, 2))
    d = np.abs(m - m[0]).max(axis=1)
    i = int(d.argmax())
    if d[i] >= a.th:
        bad += 1
        print(f"{k} 漂移 {d[i]:.1f} @ {i / 2:.1f}s  首帧 RGB {m[0].round().astype(int).tolist()} → {m[i].round().astype(int).tolist()}")
print(f"共 {len(ids)} 镜，{bad} 镜超过 {a.th}")
