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
SESSION = "lopy_zero"
GPU = "L4"
OUTPUTS_DIR = REPO_ROOT / "runtime" / "outputs"
VIDEO_DIR = REPO_ROOT / "pipeline" / "drama_zerozerozero" / "video"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
VIDEO_DIR.mkdir(parents=True, exist_ok=True)

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
    print("🎬 Stage 3: 云端 L4 视频扩散渲染与剪辑总装启动 (抗瞬断全托管版)")
    print("==========================================================")

    # 1. 资产打包 (13MB)
    tar_file = REPO_ROOT / "runtime" / "lopy_code_stage3.tar.gz"
    tar_file.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        f"tar --exclude='*.mp4' --exclude='.git' --exclude='models' --exclude='runtime' --exclude='pipeline/drama_real_fake_daughter' --exclude='pipeline/drama_workplace' --exclude='pipeline/example_D-7' --exclude='sfx' --exclude='templates' -czf {tar_file} -C {REPO_ROOT} cloud configs setup tools pipeline/drama_zerozerozero",
        shell=True, check=True
    )
    print(f"✔ 资产包已就绪 ({tar_file.stat().st_size / 1024**2:.1f} MB)")

    # 2. 拉起 Colab L4 会话
    print(f"正在向 Google Colab 申请 {GPU} 算力实例...")
    out_new = cx(["new", "--gpu", GPU, "-s", SESSION])
    print(out_new.strip())

    try:
        # 3. 上传资产包
        print("正在极速上传资产包至 Colab...")
        upload(SESSION, tar_file, "/content/lopy_code.tar.gz")
        print("✔ 资产包上传完毕！")

        # 4. 解压并建立软链接
        print("正在云端解压并部署工作目录...")
        setup_script = (
            "import os, shutil, pathlib\n"
            "base = pathlib.Path('/content/lopy-workflow-colab')\n"
            "base.mkdir(parents=True, exist_ok=True)\n"
            "shutil.unpack_archive('/content/lopy_code.tar.gz', str(base))\n"
            "for d in ['inputs', 'outputs', 'chars', 'first']:\n"
            "    (base / f'runtime/{d}').mkdir(parents=True, exist_ok=True)\n"
            "if not (base / 'input').exists(): (base / 'input').symlink_to(base / 'runtime/inputs')\n"
            "if not (base / 'output').exists(): (base / 'output').symlink_to(base / 'runtime/outputs')\n"
            "print('UNPACK_OK')\n"
        )
        vm(SESSION, setup_script)

        # 5. 安装 ComfyUI 与必要环境
        print("正在执行 colab_setup.sh 配置 ComfyUI 推理环境...")
        vm_sh(SESSION, "bash /content/lopy-workflow-colab/cloud/colab_setup.sh > /content/setup.log 2>&1")
        print("✔ ComfyUI 环境配置完成！")

        # 6. 后台脱机启动视频生成流水线
        print("正在后台启动 run_colab_video.py 视频扩散渲染任务...")
        vm_sh(SESSION, "nohup python3 -u /content/lopy-workflow-colab/pipeline/drama_zerozerozero/run_colab_video.py > /content/video_pipeline.log 2>&1 &")
        print("✔ 云端任务已在后台挂机运行！")

        # 7. 轮询监控日志 (抗断连、每 25 秒检查)
        print("\n>>> 开始监控云端生成进度 (预计需 35~40 分钟)...")
        t_start = time.time()
        last_log = ""
        while time.time() - t_start < 3600:
            time.sleep(25)
            log_tail = vm(
                SESSION,
                "import os\np='/content/video_pipeline.log'\n"
                "if os.path.exists(p):\n"
                "    lines = open(p, errors='replace').readlines()\n"
                "    print(''.join(lines[-10:]))\n"
                "else: print('WAITING_LOG')\n"
            )
            if log_tail.strip() != last_log.strip():
                print(f"[{time.strftime('%H:%M:%S')}] 云端进展:\n{log_tail.strip()}\n", flush=True)
                last_log = log_tail

            status = vm(
                SESSION,
                "import os\n"
                "if os.path.exists('/content/VIDEO_ALL_DONE.txt'): print('STATE_ALL_DONE')\n"
                "else: print('STILL_RUNNING')\n"
            )
            if "STATE_ALL_DONE" in status:
                print("🎉 检测到云端视频渲染与总装全部圆满完成！")
                break

        # 8. 下载最终成片与分镜视频
        print("\n>>> 正在将最终交付成片下载回本地...")
        remote_film = "/content/lopy-workflow-colab/runtime/outputs/drama_zerozerozero_v1.mp4"
        local_film = OUTPUTS_DIR / "drama_zerozerozero_v1.mp4"
        download(SESSION, remote_film, local_film)

        for s_id in ["s01.mp4", "s02.mp4", "s03.mp4", "s04.mp4"]:
            rem_v = f"/content/lopy-workflow-colab/pipeline/drama_zerozerozero/video/{s_id}"
            loc_v = VIDEO_DIR / s_id
            download(SESSION, rem_v, loc_v)

    finally:
        # 9. 立即停机释放云端算力 (防闲置扣费)
        print("\n>>> 安全释放 Colab 实例，停止扣费...")
        cx(["stop", "-s", SESSION], check=False)
        print("✔ 算力实例已注销，扣费终止。")

    print("==========================================================")
    print("🎉 Stage 3 视频渲染与剪辑总装全部圆满完成！")
    print(f"最终成片路径: {OUTPUTS_DIR / 'drama_zerozerozero_v1.mp4'}")
    print("==========================================================")


if __name__ == "__main__":
    main()
