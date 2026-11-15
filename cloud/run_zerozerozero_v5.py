#!/usr/bin/env python3
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SESSION = "lopy_v5"
GPU = "L4"
OUTPUTS_DIR = REPO_ROOT / "runtime" / "outputs"
V5_DIR = REPO_ROOT / "pipeline" / "drama_zerozerozero_v5"
VIDEO_DIR = V5_DIR / "video"
CHAIN_DIR = V5_DIR / "chaining"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
VIDEO_DIR.mkdir(parents=True, exist_ok=True)
CHAIN_DIR.mkdir(parents=True, exist_ok=True)

RETRY = (
    "Connection was lost", "Timeout waiting for reply", "Read timed out",
    "ConnectionError", "RemoteDisconnected", "503 Server Error", "Service Unavailable", "502 Server Error"
)


def colab_bin():
    return shutil.which("colab") or "/home/debian/.local/bin/colab"


def cx(args, inp=None, timeout=900, tries=5, check=True):
    out = ""
    for k in range(tries):
        try:
            r = subprocess.run(
                [colab_bin()] + [str(a) for a in args],
                input=inp, capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=timeout, env={**os.environ, "PYTHONIOENCODING": "utf-8"}
            )
            out = r.stdout + r.stderr
        except subprocess.TimeoutExpired:
            out = "Timeout waiting for reply (local timeout)"
        if not any(m in out for m in RETRY):
            break
        print(f"[colab] 网络瞬断/重试 ({k+1}/{tries}): {out.strip()[-120:]}", flush=True)
        time.sleep(6 * (k + 1))
    if check and "Session not found" in out:
        sys.exit("Colab 会话已失效，请重新执行。")
    return out


def vm(name, code, timeout=300):
    return cx(["exec", "-s", name], inp=code, timeout=timeout)


def vm_sh(name, cmd, timeout=600):
    code = f"import subprocess\nr = subprocess.run({cmd!r}, shell=True, capture_output=True, text=True)\nprint(r.stdout[-4000:] + r.stderr[-2000:])"
    return vm(name, code, timeout=timeout)


def upload(name, local, remote, tries=4):
    for k in range(tries):
        out = cx(["upload", "-s", name, str(local), remote], timeout=1800)
        if "Uploaded" in out:
            return
        print(f"[colab] 上传重试 ({k+1}/{tries}): {out.strip()[-140:]}", flush=True)
        time.sleep(8 * (k + 1))
    sys.exit(f"上传失败: {local}")


def download(name, remote, local, tries=4):
    Path(local).parent.mkdir(parents=True, exist_ok=True)
    for k in range(tries):
        out = cx(["download", "-s", name, remote, str(local)], timeout=1800)
        if "Downloaded" in out:
            return
        print(f"[colab] 下载重试 ({k+1}/{tries}): {out.strip()[-140:]}", flush=True)
        time.sleep(8 * (k + 1))
    print(f"下载未完成: {remote}")


def main():
    print("==========================================================")
    print("🎬 V5 完整大戏启动: 拔枪战术对峙 + 双人交替谈判 + FlashVSR 2K")
    print("==========================================================")

    # 1. 构建资产包
    tar_file = REPO_ROOT / "runtime" / "v5_code.tar.gz"
    tar_file.parent.mkdir(parents=True, exist_ok=True)
    print("正在构建 V5 资产包 (包含 S01~S04 基础视频 + S05/S06 脚本与音轨)...")
    subprocess.run(
        f"tar -czf {tar_file} -C {REPO_ROOT} cloud configs setup tools pipeline/drama_zerozerozero_v5",
        shell=True, check=True
    )
    print(f"✔ V5 资产包已就绪 ({tar_file.stat().st_size / 1024**2:.1f} MB)")

    # 2. 申请 Colab L4 会话
    print(f"正在向 Google Colab 申请 {GPU} 算力实例...")
    out_new = cx(["new", "--gpu", GPU, "-s", SESSION])
    print(out_new.strip())

    try:
        # 3. 上传资产包
        print("正在极速上传资产包至 Colab...")
        upload(SESSION, tar_file, "/content/v5_code.tar.gz")
        print("✔ 资产包上传完毕！")

        # 4. 解压并部署工作目录
        print("正在云端解压并部署工作目录...")
        setup_script = (
            "import os, shutil, pathlib\n"
            "base = pathlib.Path('/content/lopy-workflow-colab')\n"
            "base.mkdir(parents=True, exist_ok=True)\n"
            "shutil.unpack_archive('/content/v5_code.tar.gz', str(base))\n"
            "for d in ['inputs', 'outputs', 'chars', 'first', 'shots', 'temp']:\n"
            "    (base / f'runtime/{d}').mkdir(parents=True, exist_ok=True)\n"
            "if not (base / 'input').exists(): (base / 'input').symlink_to(base / 'runtime/inputs')\n"
            "if not (base / 'output').exists(): (base / 'output').symlink_to(base / 'runtime/outputs')\n"
            "print('UNPACK_OK')\n"
        )
        vm(SESSION, setup_script)

        # 5. 配置 ComfyUI 环境
        print("正在执行 colab_setup.sh 配置 ComfyUI 推理环境...")
        vm_sh(SESSION, "bash /content/lopy-workflow-colab/cloud/colab_setup.sh > /content/setup.log 2>&1")
        print("✔ ComfyUI 环境配置完成！")

        # 6. 后台脱机启动 V5 生成流水线
        print("正在后台启动 run_v5_colab.py 任务...")
        vm_sh(SESSION, "nohup python3 -u /content/lopy-workflow-colab/pipeline/drama_zerozerozero_v5/run_v5_colab.py > /content/v5_pipeline.log 2>&1 &")
        print("✔ 云端任务已在后台挂机运行！")

        # 7. 轮询监控日志 (抗断连、每 20 秒检查)
        print("\n>>> 开始监控云端任务进度 (S05拔枪 14步 + S06双人对嘴 14步 + FlashVSR 2K，预计需 24~28 分钟)...")
        t_start = time.time()
        last_log = ""
        while time.time() - t_start < 5400:
            time.sleep(20)
            log_tail = vm(
                SESSION,
                "import os\np='/content/v5_pipeline.log'\n"
                "if os.path.exists(p):\n"
                "    lines = open(p, errors='replace').readlines()\n"
                "    print(''.join(lines[-14:]))\n"
                "else: print('WAITING_LOG')\n"
            )
            if log_tail.strip() != last_log.strip():
                print(f"[{time.strftime('%H:%M:%S')}] 云端进展:\n{log_tail.strip()}\n", flush=True)
                last_log = log_tail

            status = vm(
                SESSION,
                "import os\n"
                "if os.path.exists('/content/V5_DONE.txt'): print('STATE_V5_DONE')\n"
                "else: print('STILL_RUNNING')\n"
            )
            if "STATE_V5_DONE" in status:
                print("🎉 检测到云端 V5 完整大戏渲染与 2K 总装全部圆满完成！")
                break

        # 8. 下载最终产物
        print("\n>>> 正在将最终交付成片下载回本地...")
        rem_film = "/content/lopy-workflow-colab/runtime/outputs/drama_zerozerozero_v5.mp4"
        loc_film = OUTPUTS_DIR / "drama_zerozerozero_v5.mp4"
        download(SESSION, rem_film, loc_film)

        for s_id in ["s05.mp4", "s06.mp4"]:
            rem_v = f"/content/lopy-workflow-colab/pipeline/drama_zerozerozero_v5/video/{s_id}"
            loc_v = VIDEO_DIR / s_id
            download(SESSION, rem_v, loc_v)

    finally:
        # 9. 立即停机释放云端算力 (防闲置扣费)
        print("\n>>> 安全释放 Colab 实例，停止扣费...")
        cx(["stop", "-s", SESSION], check=False)
        print("✔ 算力实例已注销，扣费终止。")

    print("==========================================================")
    print("🎉 V5 6 镜完整微电影全部圆满完成！")
    print(f"最终成片路径: {OUTPUTS_DIR / 'drama_zerozerozero_v5.mp4'}")
    print("==========================================================")


if __name__ == "__main__":
    main()
