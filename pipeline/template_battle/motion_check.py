"""每镜动作量（使用者 2026-11-03「人物没有动」）：实际用到的那段，扣掉嘴巴区，全身平均逐格差。
out/review/motion.json；印最低的镜。尾帧＝首帧常把人锁死，低于门槛的镜要看。用法：python motion_check.py [门槛，预设 1.2]"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

import make_battle as mb

W, H = 240, 136
TH = float(sys.argv[1]) if len(sys.argv) > 1 else 1.2
shots, _ = mb.resolve_shots()
rows = []
for s in shots:
    c = mb.OUT / "h3" / s["id"] / "clip.mp4"
    if s.get("still") or not c.exists():
        continue
    a, b = mb.used_range(s)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", str(c), "-vf", f"scale={W}:{H},fps=12", "-pix_fmt", "gray",
                          "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    F = np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.float32)
    d = np.abs(np.diff(F, axis=0))
    if len(d) == 0:
        continue
    # 只看变化最大的 15% 区域：背景不动时才不会被平均掉
    m = d.mean(axis=0)
    top = np.sort(m.ravel())[-int(m.size * 0.15):].mean()
    rows.append((s["id"], s["kind"], round(float(top), 2), bool(s.get("last_first")), round(s["end"] - s["start"], 1)))
rows.sort(key=lambda r: r[2])
Path(mb.OUT / "review" / "motion.json").write_text(json.dumps(rows, ensure_ascii=False, indent=0), encoding="utf-8")
print("动作量最低（镜、种类、量、尾帧锁、秒）：")
for r in rows[:30]:
    print(" ", r, "← 太低" if r[2] < TH else "")
