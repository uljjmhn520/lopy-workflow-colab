#!/usr/bin/env python3
import subprocess
import sys
import time
from pathlib import Path

REPO_DIR = Path("/content/lopy-workflow-colab")

def main():
    print("==========================================================")
    print("🎬 双任务联合流水线启动: FlashVSR 2K 超分 + DMAD 4步 V4 极速")
    print("==========================================================")
    t_start = time.time()

    # Task 1: FlashVSR on V3
    print("\n>>> [1/2] 正在执行任务一：FlashVSR 2X 超分升阶 V3...")
    t1 = time.time()
    p1 = subprocess.run(["python3", "-u", str(REPO_DIR / "tools" / "run_flashvsr_pipeline.py")])
    if p1.returncode != 0:
        print("❌ 任务一 FlashVSR 超分失败！")
        sys.exit(1)
    print(f"✔ 任务一 FlashVSR 2K 超分完成，耗时 {time.time()-t1:.1f}s！\n")

    # Task 2: DMAD 4-step on V4
    print(">>> [2/2] 正在执行任务二：drama_zerozerozero_v4 DMAD 4步极速管线...")
    t2 = time.time()
    p2 = subprocess.run(["python3", "-u", str(REPO_DIR / "pipeline" / "drama_zerozerozero_v4" / "run_v4_colab.py")])
    if p2.returncode != 0:
        print("❌ 任务二 DMAD V4 渲染失败！")
        sys.exit(1)
    print(f"✔ 任务二 DMAD 4 步极速渲染完成，耗时 {time.time()-t2:.1f}s！\n")

    Path("/content/ALL_TASKS_DONE.txt").write_text("ALL_DONE\n")
    print("==========================================================")
    print(f"🎉 双任务全部圆满完成！总累计耗时 {time.time()-t_start:.1f}s")
    print("==========================================================")

if __name__ == "__main__":
    main()
