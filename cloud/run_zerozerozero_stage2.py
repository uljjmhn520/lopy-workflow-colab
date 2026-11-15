#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SESSION = "lopy_zero"
GPU = "L4"
FRAMES_DIR = REPO_ROOT / "pipeline" / "drama_zerozerozero" / "frames"
FRAMES_DIR.mkdir(parents=True, exist_ok=True)


def run(cmd, desc, check=True):
    print(f"\n>>> [{desc}] ...", flush=True)
    t0 = time.time()
    p = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    if p.stdout.strip():
        print(p.stdout.strip())
    if p.returncode != 0:
        if p.stderr.strip():
            print(f"❌ 输出/错误: {p.stderr.strip()}", flush=True)
        if check:
            sys.exit(p.returncode)
        return False
    print(f"✔ 完成: [{desc}] (耗时 {time.time()-t0:.1f}s)", flush=True)
    return True


def main():
    print("==========================================================")
    print("🎬 Stage 2: 云端 L4 首帧极速生成流水线启动")
    print("==========================================================")

    # 1. 创建精简打包 (小于 1MB，杜绝上传超时与 SSL EOF)
    tar_file = REPO_ROOT / "runtime" / "lopy_code.tar.gz"
    tar_file.parent.mkdir(parents=True, exist_ok=True)
    run(f"tar --exclude='*.mp4' --exclude='*.wav' --exclude='*.png' --exclude='.git' --exclude='models' --exclude='runtime' --exclude='pipeline/drama_real_fake_daughter' --exclude='pipeline/drama_workplace' --exclude='pipeline/example_D-7' --exclude='sfx' --exclude='templates' -czf {tar_file} -C {REPO_ROOT} cloud configs pipeline/drama_zerozerozero setup tools",
        "打包精简代码与分镜工程包")

    # 2. 拉起 Colab L4 会话
    print(f"正在向 Google Colab 申请 {GPU} 算力实例...")
    run(f"colab new --gpu {GPU} -s {SESSION}", f"拉起 Colab {GPU} 实例")

    try:
        # 3. 上传代码
        print("正在高速上传代码包至 Colab...")
        run(f"colab upload -s {SESSION} {tar_file} /content/lopy_code.tar.gz", "上传代码包")

        # 4. 后台脱机解压并执行（防 WebSocket 30s 超时）
        start_runner_code = """
import os, shutil, subprocess
from pathlib import Path

print("解压工程包...")
base = Path("/content/lopy-workflow-colab")
base.mkdir(parents=True, exist_ok=True)
shutil.unpack_archive("/content/lopy_code.tar.gz", str(base))

# 建立快捷软链接
for d in ["inputs", "outputs", "chars", "first"]:
    (base / f"runtime/{d}").mkdir(parents=True, exist_ok=True)
if not (base / "input").exists():
    (base / "input").symlink_to(base / "runtime/inputs")
if not (base / "output").exists():
    (base / "output").symlink_to(base / "runtime/outputs")

# 后台启动 setup 和 keyframes 渲染
cmd = "nohup bash -c 'bash /content/lopy-workflow-colab/cloud/colab_setup.sh && python3 -u /content/lopy-workflow-colab/pipeline/drama_zerozerozero/run_colab_keyframes.py' > /content/keyframes_pipeline.log 2>&1 &"
os.system(cmd)
print("✔ 云端任务已在后台挂机启动！")
"""
        py_tmp = REPO_ROOT / "runtime" / "start_runner.py"
        with open(py_tmp, "w", encoding="utf-8") as f:
            f.write(start_runner_code)

        run(f"colab upload -s {SESSION} {py_tmp} /content/start_runner.py", "上传启动脚本")
        run(f"colab exec -s {SESSION} < {py_tmp}", "在 Colab 后台启动生成进程")

        # 5. 循环轮询日志与完成标记 (避免静默断连)
        print("\n>>> 开始监控云端生成进度 (每 15 秒同步一次最新日志)...")
        t_start = time.time()
        completed = False

        while time.time() - t_start < 900:  # 最长 15 分钟
            time.sleep(15)
            # 检查是否有完成标记
            res = subprocess.run(
                f"colab exec -s {SESSION}",
                shell=True, text=True, capture_output=True,
                input="import os\nif os.path.exists('/content/KEYFRAMES_DONE.txt'): print('STATE_ALL_DONE')\nelse: os.system('tail -n 6 /content/keyframes_pipeline.log 2>/dev/null')\n"
            )
            out = res.stdout.strip()
            print(f"[{time.strftime('%H:%M:%S')}] 云端进展:\n{out}\n", flush=True)

            if "STATE_ALL_DONE" in out:
                print("🎉 检测到云端首帧已全部渲染完毕！")
                completed = True
                break

        if not completed:
            print("❌ 渲染超时未完成，正在抓取错误日志...")
            subprocess.run(
                f"colab exec -s {SESSION}",
                shell=True, text=True,
                input="import os; os.system('cat /content/keyframes_pipeline.log 2>/dev/null; cat /content/comfy_server.log 2>/dev/null')"
            )
            sys.exit(1)

        # 6. 下载画廊与关键帧
        remote_gallery = "/content/lopy-workflow-colab/pipeline/drama_zerozerozero/frames/gallery_zerozerozero_preview.png"
        local_gallery = FRAMES_DIR / "gallery_zerozerozero_preview.png"
        run(f"colab download -s {SESSION} {remote_gallery} {local_gallery}", "拉回 2x2 首帧审查画廊")

        for f in ["ref_emma.png", "frame_s01.png", "frame_s02.png", "frame_s03_first.png", "frame_s03_last.png", "frame_s04.png"]:
            rem = f"/content/lopy-workflow-colab/pipeline/drama_zerozerozero/frames/{f}"
            loc = FRAMES_DIR / f
            run(f"colab download -s {SESSION} {rem} {loc}", f"拉回首帧 {f}", check=False)

    finally:
        # 7. 立即停机释放云端算力 (防闲置扣费)
        print("\n>>> 安全释放 Colab 实例，停止扣费...")
        run(f"colab stop -s {SESSION}", "释放 Colab 算力实例", check=False)

    print("==========================================================")
    print("🎉 Stage 2 首尾帧生成完毕！已安全释放云端算力。")
    print(f"画廊路径: {FRAMES_DIR / 'gallery_zerozerozero_preview.png'}")
    print("==========================================================")


if __name__ == "__main__":
    main()
