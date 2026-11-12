"""只用 Colab 跑 H3（本机 ComfyUI 被别的 session 占著时用，完全不碰本机伫列）。
开跑前先用 cloud/colab_plan.py 算要开几台，告诉使用者、等使用者同意（2026-11-06 起）；同一帐号开两台＝COLAB_HOMES 写两次同一个家目录。
每个帐号开一台 G4（各 2 个 ComfyUI）→ 大家从同一个伫列一批一批拿 → 下载回 out/h3/<镜>/ → 立刻关机并确认。
失败的镜放回伫列，最多重试一轮；还是失败就列出来。
用法：python colab_only.py [镜号…]    （不给镜号＝全部还没有 clip.mp4、或 spec 比 clip 新的镜）
环境变数：COLAB_HOMES（用 ; 分隔的家目录，default＝目前帐号；预设只用目前帐号）、COLAB_NAMES（对应的 session 名，用 ; 分隔；预设 h3、h3_2…）、
COLAB_CHUNK（每批几支，预设 8）、COLAB_REUSE=1（确定开著的那台是自己开的才设）。
⚠ 2026-11-06 踩坑：开工时发现同名 session 已经开著＝很可能是别的 session 的 VM。colab_h3.py start 会直接沿用、做完的 stop 还会把它关掉 →
这里预设跳过那个帐号（只在 COLAB_REUSE=1 才沿用）。开机前查过 status 也不够，隔几分钟就可能被别的 session 开走。"""
import collections
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CFG = json.loads((HERE / "battle.json").read_text(encoding="utf-8"))
REPO = (HERE / CFG.get("repo_dir", "../..")).resolve()
TOOL = REPO / "cloud" / "colab_h3.py"
H3 = HERE / "out" / "h3"
only = sys.argv[1:]
CHUNK = int(os.environ.get("COLAB_CHUNK", "8"))
homes = [None if h.strip() in ("", "default") else h.strip() for h in os.environ.get("COLAB_HOMES", "default").split(";")]


def log(*a):
    print(time.strftime("[%H:%M:%S]"), *a, flush=True)


names = [n.strip() for n in os.environ.get("COLAB_NAMES", "").split(";") if n.strip()] or ["h3" if k == 0 else f"h3_{k + 1}" for k in range(len(homes))]


def need(d):
    sp, cl = d / "spec.json", d / "clip.mp4"
    if not sp.exists() or (only and d.name not in only):
        return False
    return not cl.exists() or cl.stat().st_mtime < sp.stat().st_mtime


def colab(k, *args):
    cmd = [sys.executable, str(TOOL), "--name", names[k], *map(str, args)]
    env = dict(os.environ, USERPROFILE=homes[k], HOME=homes[k]) if homes[k] else dict(os.environ)
    return subprocess.run(cmd, env=env)


q = collections.deque(sorted((d for d in H3.iterdir() if d.is_dir() and need(d)), key=lambda d: d.name))
n0 = len(q)
tries = collections.Counter()
lock = threading.Lock()
t0 = time.time()
log(f"{n0} 镜，{len(homes)} 台 Colab")


def taken(k):
    """同名 session 已经开著？（别的 session 的 VM 不能沿用、更不能关）"""
    env = dict(os.environ, USERPROFILE=homes[k], HOME=homes[k]) if homes[k] else dict(os.environ)
    code = f"import sys; sys.path.insert(0, {str(TOOL.parent)!r}); sys.argv = ['x']; import colab_h3; print('ALIVE' if colab_h3.alive({names[k]!r}) else 'FREE')"
    return "ALIVE" in subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout


def worker(k):
    tag = f"云端{k + 1}"
    if os.environ.get("COLAB_REUSE") != "1" and taken(k):
        log(tag, f"{names[k]} 已经开著（可能是别的 session 的）→ 不用这个帐号")
        return
    log(tag, "开机（只装 H3，约 4 分钟）")
    for attempt in range(int(os.environ.get("COLAB_START_TRIES", "8"))):   # G4 常回 503 Service Unavailable（Google 没机器）：隔 2 分钟再要
        if colab(k, "start", "--h3-only").returncode == 0:
            break
        log(tag, f"第 {attempt + 1} 次开不起来，2 分钟后再试")
        time.sleep(120)
    else:
        log(tag, "一直开不起来，放弃（镜头留给另一台）")
        colab(k, "stop")
        return
    try:
        while True:
            with lock:
                batch = [q.popleft() for _ in range(min(CHUNK, len(q)))]
            if not batch:
                return
            stamp = time.time(); log(tag, "拿", len(batch), "支：", " ".join(d.name for d in batch))
            colab(k, "batch", *[d / "spec.json" for d in batch])
            bad = [d for d in batch if not ((d / "clip.mp4").exists() and (d / "clip.mp4").stat().st_mtime >= stamp)]
            with lock:
                for d in bad:
                    tries[d.name] += 1
                    if tries[d.name] < 2:
                        q.append(d)
            log(tag, f"这批 {len(batch) - len(bad)}/{len(batch)} 支，{time.time() - stamp:.0f} 秒，总进度剩 {len(q)} 支待拿")
    finally:
        log(tag, "关机"); colab(k, "stop")


th = [threading.Thread(target=worker, args=(k,)) for k in range(len(homes))]
for i, t in enumerate(th):
    t.start()
for t in th:
    t.join()
miss = [d.name for d in sorted(H3.iterdir()) if d.is_dir() and need(d)]
log(f"完成 {time.time() - t0:.0f} 秒；没做出来：", miss)
for k in range(len(homes)):
    colab(k, "status")
