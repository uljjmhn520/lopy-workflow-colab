"""本机＋Colab 一起跑 H3（H3_BACKEND=both）。
开跑前先用 cloud/colab_plan.py 算要开几台，告诉使用者、等使用者同意（2026-11-06 起）；同一帐号开两台＝HYBRID_COLAB_HOMES 写两次同一个家目录。

2026-10-11 第一次实战（〈收假图鉴〉直式 34 镜、3370 格、DMAD 4 步，本机 RTX 5090＋Colab G4，HYBRID_CHUNK=8）：
  **17.9 分钟**完成（本机 15 支、云端 19 支、失败 0），推算全部本机 32.6 分钟 → **省 45%**；Colab 花 1.97 单元（含开机、关机）。
  Colab 开机 216 秒（这段时间本机先做了 4 支）；每批 8 支约 304–314 秒，其中上传、解压、轮询、下载约 70 秒。
  依这次踩的坑改了：每批预设 8 支、轮询 15 秒（colab_h3.py）、伫列快空时依两边速度估算云端该拿几支（避免本机做完还在等云端）、
  关机放背景不算进等待、本机工具路径可用 HYBRID_TOOLS 指定。

做法：所有镜头放进同一个伫列，两个工人同时拿：
  - 本机：从伫列「前面」一支一支拿，用本机 ComfyUI（h3_shot.py）跑。开跑不用等。
  - 云端：先开 Colab G4（只装 ComfyUI＋H3，约 3.5 分钟，这段时间本机已经在跑），开好后每次从伫列「后面」拿一批交给
    colab_h3.py batch（上传 → 跑 → 下载回每个镜头的资料夹），做完再拿下一批。
    批次大小：伫列还多时拿 HYBRID_CHUNK 支；快空时用实测速度估算——让「云端这批做完」和「本机做完剩下的」差不多同时，
    算出来少于 2 支就不再派云端（只剩 0–1 支时本机做比较快）。
  - 云端失败的镜头放回伫列给本机重跑；伫列空了就在背景关掉 Colab（HYBRID_KEEP=1 则不关，审片后要重抽可以接著用）。
接力镜头（spec 有 first_clip，要用上一镜的结尾）等两边都做完、上一镜一定已经在了，才由本机照顺序跑。
镜头太少（< HYBRID_MIN，预设 8）不值得等云端开机 → 全部本机跑。

用法：python cloud/hybrid_h3.py out/h3/S01 out/h3/S02 …   （每个资料夹要有 spec.json；成品 clip.mp4 写回同一个资料夹）
      make_film.py 设 H3_BACKEND=both 会自动呼叫 run_hybrid()。
环境变数：HYBRID_CHUNK（云端每批最多几支，预设 8）、HYBRID_MIN（少于几支就不开云端，预设 8）、HYBRID_KEEP=1（做完不关 Colab）、
          HYBRID_TOOLS（本机 h3_shot.py 所在资料夹，预设 repo 的 tools/）、COLAB_NAME（Colab session 名称，预设 h3）、
          HYBRID_COLAB_HOMES（两个以上 Colab 帐号同时跑：每个帐号一个家目录，用 ; 分隔〔Linux／macOS 用 :〕，default＝目前登入的帐号）。
两个帐号同时跑（2026-10-29）：Colab CLI 的登入凭证放在家目录（~/.config/colab-cli/token.json），一个家目录＝一个帐号。
  第二个帐号：建一个空资料夹（例如 C:\\colab_home2），在 cmd 跑 `set USERPROFILE=C:\\colab_home2` `set HOME=C:\\colab_home2` `colab usage`
  → 浏览器登入第二个帐号（只要做一次）。之后 `set HYBRID_COLAB_HOMES=default;C:\\colab_home2`：本机 1 个 ComfyUI＋每台 G4 2 个。
  每台各扣自己帐号的单元；云端预设保留比例照台数算（两台约 4/5 给云端）。
  实测（2026-10-29，38 支 3–4.5 秒短镜、DMAD 4 步，本机 RTX 5090＋两个帐号各一台 G4）：16.5 分钟全部完成（本机 10、云端 10＋18），
  推算全部本机约 37 分 → 快约 55%；两个帐号各扣约 2.0 单元。G4 开机看机房：美国 216 秒、荷兰 8.5 分（下载模型慢），
  开机慢的那台只在后段出力 → 镜头少（< 20 支）时第二台不太划算，越长的片越值得。
中途要停：本机要连 h3_shot.py 子程序与 ComfyUI 伫列一起清（POST /queue {"clear": true} 与 POST /interrupt）；
          停掉这支程式后 Colab 上的批次还在算，要另外 python cloud/colab_h3.py stop。
HYBRID_KEEP=1 做完要手动关：第一台 `colab_h3.py stop`；第二台以后的 session 名称是 h3_2、h3_3…，而且要在那个帐号的家目录下关
（set USERPROFILE=<家目录> 再 `colab_h3.py --name h3_2 stop`），只跑 `colab_h3.py stop` 会回「Session 'h3' not found」、那台照扣。
关完用 `colab_h3.py status` 确认 Active assignments: 0（2026-10-30〈电流之战〉漏关第二台的教训）。"""
import collections
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
AI_ROOT = Path(os.environ.get("AI_ROOT", "C:/AI"))
PYH3_DEFAULT = AI_ROOT / "H3" / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
LOCAL_SEC, CLOUD_SEC, CLOUD_OVERHEAD = 62.0, 30.0, 70.0     # 起始估计（2026-10-11 实测：本机每支约 62 秒；云端 2 个 ComfyUI 平均每支约 30 秒＋每批约 70 秒耗损）


def _log(msg):
    print(time.strftime("[%H:%M:%S] ") + msg, flush=True)


def _relay(d):
    try:
        return "first_clip" in json.loads((Path(d) / "spec.json").read_text(encoding="utf-8"))
    except Exception:
        return False


def cloud_take(rem, chunk, local_sec, cloud_sec, overhead=CLOUD_OVERHEAD):
    """伫列剩 rem 支时云端这批该拿几支：让 max(本机做完剩下的, 云端这批做完) 最小。回传 0／1 代表不值得派云端。"""
    best_n, best_t = 0, rem * local_sec
    for n in range(1, min(chunk, rem) + 1):
        t = max((rem - n) * local_sec, overhead + n * cloud_sec)
        if t < best_t:
            best_n, best_t = n, t
    return best_n


def colab_homes():
    """HYBRID_COLAB_HOMES：每个 Colab 帐号一个家目录（Colab CLI 的登入凭证在 <家目录>/.config/colab-cli/），用 os.pathsep 分隔
    （Windows 是 ;）；写 default 或空字串＝目前登入的帐号。没设＝只用目前帐号一台。每个帐号开一台 G4、各 2 个 ComfyUI。"""
    v = os.environ.get("HYBRID_COLAB_HOMES")
    if not v:
        return [None]
    return [None if h.strip() in ("", "default") else str(Path(h.strip()).expanduser().resolve()) for h in v.split(os.pathsep)]


def run_hybrid(dirs, pyh3=None, tools=None):
    """dirs：镜头资料夹（各有 spec.json）。回传没做出 clip.mp4 的资料夹清单（空＝全部成功）。"""
    pyh3 = str(pyh3 or PYH3_DEFAULT); tools = Path(tools or os.environ.get("HYBRID_TOOLS") or REPO / "tools")
    dirs = [Path(d) for d in dirs]
    chunk = int(os.environ.get("HYBRID_CHUNK", "8")); nmin = int(os.environ.get("HYBRID_MIN", "8"))
    name = os.environ.get("COLAB_NAME", "h3"); keep = os.environ.get("HYBRID_KEEP") == "1"
    homes = colab_homes(); nc = len(homes)
    relay = [d for d in dirs if _relay(d)]                          # 最后才由本机照顺序跑
    shared = collections.deque(d for d in dirs if d not in relay)
    lock = threading.Lock(); stats = {"local": 0, "cloud": 0}; cloud_on = len(shared) >= nmin
    # 2026-10-25（使用者：「Colab 比较快，要分配比较多的片段给他」）：开跑就照速度比例替云端保留一份（预设
    # 本机 62 秒／支 vs 云端 30 秒／支 → 一台云端约 2/3、两台约 4/5），本机不能先拿走；本机自己那份做完才去接云端还没送出的。
    # 之前是共用伫列，云端第一批要载模型（〈毕氏定理 MV〉8 支 8.5 分）期间本机一直拿，结果本机分得比云端多。
    share = float(os.environ.get("HYBRID_CLOUD_SHARE", nc * LOCAL_SEC / (nc * LOCAL_SEC + CLOUD_SEC))) if cloud_on else 0.0
    reserve = collections.deque(shared.pop() for _ in range(int(round(len(shared) * share))))   # 从尾巴拿＝云端照旧做后段
    speed = {"local": [], "cloud": []}                              # 实测秒数，用来估算尾巴该怎么分
    t0 = time.time()
    _log(f"[hybrid] {len(dirs)} 镜（接力镜 {len(relay)} 支只在本机）；" + (f"本机＋{nc} 台 Colab 一起跑：先保留 {len(reserve)} 支给云端、"
         f"{len(shared)} 支给本机（HYBRID_CLOUD_SHARE={share:.2f}）" if cloud_on else f"少于 {nmin} 支，全部本机跑"))

    def avg(k, default):
        v = speed[k]
        return sum(v) / len(v) if v else default

    def local_worker(do_relay=False):
        while True:
            with lock:
                if shared:
                    d = shared.popleft()
                elif reserve and not do_relay:              # 自己那份做完 → 接云端还没送出的（从前面拿，云端从后面拿）
                    d = reserve.popleft(); _log(f"[hybrid] 本机做完自己的，接手云端保留的 {d.name}")
                else:
                    d = relay.pop(0) if do_relay and relay else None
            if d is None:
                return
            if (d / "clip.mp4").exists():
                continue
            ts = time.time()
            r = subprocess.run([pyh3, str(tools / "h3_shot.py"), str(d / "spec.json"), "--out", str(d)])
            ok = r.returncode == 0 and (d / "clip.mp4").exists()
            with lock:
                stats["local"] += ok
                if ok:
                    speed["local"].append(time.time() - ts)
            _log(f"[hybrid] 本机 {d.name}: {'OK' if ok else 'FAIL'}")

    def colab(k, *args, wait=True):
        # 第 k 台：自己的家目录（＝自己的 Colab 帐号）与 session 名称（h3、h3_2…）
        cmd = [sys.executable, str(REPO / "cloud" / "colab_h3.py"), "--name", name if k == 0 else f"{name}_{k + 1}", *map(str, args)]
        env = dict(os.environ, USERPROFILE=homes[k], HOME=homes[k]) if homes[k] else None
        return subprocess.run(cmd, env=env) if wait else subprocess.Popen(cmd, env=env)

    def colab_taken(k):
        """第 k 台的同名 session 是否已经开著（查不到视为没开，交给 start 自己处理）。"""
        tool = REPO / "cloud" / "colab_h3.py"
        code = f"import sys; sys.path.insert(0, {str(tool.parent)!r}); sys.argv = ['x']; import colab_h3; print('ALIVE' if colab_h3.alive({(name if k == 0 else f'{name}_{k + 1}')!r}) else 'FREE')"
        env = dict(os.environ, USERPROFILE=homes[k], HOME=homes[k]) if homes[k] else None
        return "ALIVE" in subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout

    def others_sec():
        """收尾估算用：「本机＋其他云端」合起来每支几秒（只有一台云端时就是本机速度）。"""
        loc, cl = avg("local", LOCAL_SEC), avg("cloud", CLOUD_SEC) + CLOUD_OVERHEAD / chunk
        return 1.0 / (1.0 / loc + (nc - 1) / cl)

    def cloud_worker(k):
        tag = f"云端{k + 1}" if nc > 1 else "云端"
        # 2026-11-06 踩坑：同名 session 已开著＝很可能是别的 session 的 VM；start 会直接沿用、做完的 stop 还会把它关掉 → 不碰。
        # 确定是自己 HYBRID_KEEP 留下的才设 COLAB_REUSE=1 或 HYBRID_KEEP=1 接著用。
        if os.environ.get("COLAB_REUSE") != "1" and not os.environ.get("HYBRID_KEEP") and colab_taken(k):
            _log(f"[hybrid] {tag} 同名 session 已经开著（可能是别的 session 的）→ 不用这个帐号，镜头由本机和其他云端接手"); return
        _log(f"[hybrid] {tag}开机中（只装 H3，约 3.5 分钟，本机先跑）")
        if colab(k, "start", "--h3-only").returncode != 0:
            _log(f"[hybrid] {tag} Colab 开不起来 → 它保留的镜头由本机和其他云端接手"); return
        try:
            first = True
            while True:
                with lock:
                    if reserve:                                     # 先做保留给云端的那份
                        rem = len(reserve) + len(shared)
                        # 收尾（2026-10-25 高斯 MV：最后一批云端一次拿 8 支跑 8 分，本机早做完闲了 6 分）：
                        # 剩不到两批时照实测速度估云端这批该拿几支，其余留在 reserve 让本机做完自己的之后接手
                        n = min(chunk, len(reserve)) if rem > 2 * chunk * nc else max(2, min(len(reserve), cloud_take(
                            rem, chunk, others_sec(), avg("cloud", CLOUD_SEC))))
                        n = min(n, len(reserve))                    # 2026-10-27：保留只剩 1 支时 max(2,…) 会多拿 → pop 空伫列
                        batch = [reserve.pop() for _ in range(n)]
                    else:
                        rem = len(shared)
                        n = min(chunk, rem) if rem > 2 * chunk * nc else cloud_take(rem, chunk, others_sec(), avg("cloud", CLOUD_SEC))
                        if n < 2:                                   # 剩下的本机做比较快（不用上传下载、不用等云端）
                            return
                        batch = [shared.pop() for _ in range(n)]
                todo = [d for d in batch if not (d / "clip.mp4").exists()]
                if not todo:
                    continue
                _log(f"[hybrid] {tag}拿 {len(todo)} 支（伫列剩 {rem - n}）：{' '.join(d.name for d in todo)}")
                ts = time.time()
                colab(k, "batch", *[d / "spec.json" for d in todo])
                back = [d for d in todo if not (d / "clip.mp4").exists()]
                done = len(todo) - len(back)
                with lock:
                    stats["cloud"] += done; stats[tag] = stats.get(tag, 0) + done
                    shared.extend(back)                             # 失败的放回伫列，本机会拿去做
                    if done and not first:                          # 第一批含载模型暖机，不拿来估速度（会把云端估得太慢）
                        speed["cloud"].append(max(1.0, (time.time() - ts - CLOUD_OVERHEAD) / done))
                _log(f"[hybrid] {tag}这批 {done} 支 {time.time() - ts:.0f} 秒" + ("（第一批含暖机）" if first else ""))
                first = False
                if back:
                    _log(f"[hybrid] {tag}失败 {len(back)} 支，放回伫列：{' '.join(d.name for d in back)}")
        finally:
            if keep:
                _log(f"[hybrid] HYBRID_KEEP=1：{tag} Colab 不关（闲置约 20 分钟会被收回；用完记得 colab_h3.py stop）")
            else:
                _log(f"[hybrid] 背景关闭{tag} Colab（不用等）")
                colab(k, "stop", wait=False)

    th = [threading.Thread(target=local_worker)] + ([threading.Thread(target=cloud_worker, args=(k,)) for k in range(nc)] if cloud_on else [])
    for t in th:
        t.start()
    for t in th:
        t.join()
    local_worker(do_relay=True)                                     # 云端最后放回来的失败镜头＋接力镜头
    miss = [d for d in dirs if not (d / "clip.mp4").exists()]
    per = "".join(f"（{k}：{v}）" for k, v in stats.items() if k.startswith("云端") and nc > 1)
    _log(f"[hybrid] 完成 {time.time() - t0:.0f} 秒：本机 {stats['local']} 支、云端 {stats['cloud']} 支{per}、失败 {len(miss)} 支")
    return miss


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sys.exit(1 if run_hybrid(sys.argv[1:]) else 0)
