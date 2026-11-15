import os
import sys
import time
import subprocess
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DRAMA_DIR = REPO_ROOT / "pipeline" / "drama_real_fake_daughter"
VIDEO_DIR = DRAMA_DIR / "video"
VIDEO_DIR.mkdir(parents=True, exist_ok=True)
BRAIN_DIR = Path("/home/debian/.gemini/antigravity-cli/brain/d4452bed-7fc1-42de-9113-f401c1bd643e")

print("================================================================================")
print("🚀 LoPy Real-Time Collector & Zero-Cost Shutdown Watchdog Started")
print("================================================================================")

CHECK_INTERVAL = 20
MAX_WAIT_SECONDS = 3600  # 1 hour max
start_time = time.time()

log_tmp = Path("/tmp/colab_watchdog_video.log")
shots = ["s01", "s02", "s03", "s04"]

while time.time() - start_time < MAX_WAIT_SECONDS:
    # 1. 尝试检查并拉取每一镜
    for sid in shots:
        local_p = VIDEO_DIR / f"{sid}.mp4"
        if not local_p.exists():
            marker = Path(f"/tmp/{sid}_DONE.txt")
            if marker.exists():
                marker.unlink()
            cmd_check = ["colab", "download", "-s", "lopy", f"/content/{sid}_DONE.txt", str(marker)]
            subprocess.run(cmd_check, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if marker.exists() and "DONE" in marker.read_text():
                print(f"\n🎉 发现分镜 {sid} 已在云端渲染完成，立即拉取到本地！")
                remote_p = f"/content/lopy-workflow-colab/pipeline/drama_real_fake_daughter/video/{sid}.mp4"
                cmd_dl = ["colab", "download", "-s", "lopy", remote_p, str(local_p)]
                subprocess.run(cmd_dl, check=True)
                print(f"✔ [即产即拉] 分镜 {sid}.mp4 已成功落盘本地 ({local_p.stat().st_size / 1024**2:.2f} MB)！\n", flush=True)

    # 检查是否全部 4 镜均已落盘
    downloaded = [sid for sid in shots if (VIDEO_DIR / f"{sid}.mp4").exists()]
    if len(downloaded) == len(shots):
        print("\n\n🎉 全部 4 镜视频素材已完整安全落盘本地！")
        break

    # 2. 读取并刷新日志进度
    if log_tmp.exists():
        log_tmp.unlink()
    cmd_log = ["colab", "download", "-s", "lopy", "/content/video_pipeline.log", str(log_tmp)]
    subprocess.run(cmd_log, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if log_tmp.exists():
        content = log_tmp.read_text(errors="ignore")
        if "❌ 失败" in content:
            print("\n❌ 发现云端渲染异常！正在紧急停止 Colab 实例...")
            subprocess.run(["colab", "stop", "-s", "lopy"])
            sys.exit(1)
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        last_info = lines[-1] if lines else "Waiting..."
        print(f"[{time.strftime('%H:%M:%S')}] 云端进度 (已落盘 {len(downloaded)}/4): {last_info[:90]}", flush=True)

    time.sleep(CHECK_INTERVAL)
else:
    print("\n❌ 超时！正在紧急关闭 Colab 实例以保护算力...")
    subprocess.run(["colab", "stop", "-s", "lopy"])
    sys.exit(1)

elapsed = time.time() - start_time
print(f"全流程耗时: {elapsed:.1f} 秒 (~{elapsed/60:.1f} 分钟)")

# 3. 【严苛铁律】立即关闭 Colab 实例，彻底释放 GPU 算力！
print("\n================================================================================")
print("🛑 [铁律执行] 所有视频素材已落盘本地，立刻关闭 Colab A100 实例停机！")
print("================================================================================")
stop_res = subprocess.run(["colab", "stop", "-s", "lopy"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
print(stop_res.stdout)

# 4. 执行本地 Stage 4 短剧剪辑、字幕压制与 SFX 混音
print("\n================================================================================")
print("🎬 [Stage 4] 开始本地自动化影视级剪辑 (FFmpeg 对齐、ASS 双语字幕、音效混音)...")
print("================================================================================")
cmd_assemble = ["python3", str(DRAMA_DIR / "assemble_film.py")]
subprocess.run(cmd_assemble, check=True)

final_film = REPO_ROOT / "runtime" / "outputs" / "drama_real_fake_daughter_v1.mp4"
if not final_film.exists():
    print("❌ 最终成片未成功生成！")
    sys.exit(1)

# 5. 归档到 artifacts
if BRAIN_DIR.exists():
    target_artifact = BRAIN_DIR / "drama_real_fake_daughter_v1.mp4"
    shutil.copy2(final_film, target_artifact)
    print(f"✔ 成片已同步至 Artifacts 目录: {target_artifact}")

print("\n================================================================================")
print("🎉🎉🎉 LoPy 《真假千金·初见交锋》 全流程自动化生产与闭环停机 100% 成功达成！")
print("================================================================================")
