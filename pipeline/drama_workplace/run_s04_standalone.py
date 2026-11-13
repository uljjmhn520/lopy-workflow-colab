import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO_DIR = Path("/content/lopy-workflow-colab")
COMFY_DIR = Path("/content/ComfyUI")
COMFY_HOST = "http://127.0.0.1:8188"
H3_MODELS = REPO_DIR / "models" / "H3" / "models"
DRAMA_DIR = REPO_DIR / "pipeline" / "drama_workplace"
FRAMES_DIR = DRAMA_DIR / "frames"
AUDIO_DIR = DRAMA_DIR / "audio"
VIDEO_DIR = DRAMA_DIR / "video"

FRAMES_DIR.mkdir(parents=True, exist_ok=True)
VIDEO_DIR.mkdir(parents=True, exist_ok=True)

# 1. 快速检查与多线程下载 H3 必须模型 (aria2c 极速并发)
MODELS_TO_DOWNLOAD = [
    ("diffusion_models/minimax_h3_image_pruned_int8_convrot.safetensors",
     "https://huggingface.co/Comfy-Org/MiniMax-H3-Image/resolve/main/diffusion_models/minimax_h3_image_pruned_int8_convrot.safetensors"),
    ("text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors",
     "https://huggingface.co/Comfy-Org/MiniMax-H3-Image/resolve/main/text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"),
    ("vae/minimax_h3_image_vae_fp16.safetensors",
     "https://huggingface.co/Comfy-Org/MiniMax-H3-Image/resolve/main/vae/minimax_h3_image_vae_fp16.safetensors"),
    ("diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors",
     "https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/7e75982b97cd5a41d2dcfa1904ee88d0686d6fd1/diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors"),
    ("vae/minimax_h3_video_vae_fp16.safetensors",
     "https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/7e75982b97cd5a41d2dcfa1904ee88d0686d6fd1/vae/minimax_h3_video_vae_fp16.safetensors"),
    ("vae/minimax_h3_audio_vae_fp32.safetensors",
     "https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/7e75982b97cd5a41d2dcfa1904ee88d0686d6fd1/vae/minimax_h3_audio_vae_fp32.safetensors")
]

def ensure_models():
    print("=== [1/4] 检查与多线程下载 H3 图像与视频模型 (aria2c 极速下载) ===")
    subprocess.run(["apt-get", "install", "-y", "-qq", "aria2"], check=True)
    for rel_path, url in MODELS_TO_DOWNLOAD:
        target = H3_MODELS / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.stat().st_size > 1024 * 1024:
            print(f"[已存在跳过] {target.name} ({target.stat().st_size / 1024**3:.2f} GB)")
            continue
        print(f"[开始极速下载] {target.name} ...")
        t0 = time.time()
        cmd = ["aria2c", "-c", "-x", "16", "-s", "16", "--console-log-level=warn", url, "-d", str(target.parent), "-o", target.name]
        subprocess.run(cmd, check=True)
        print(f"[完成] {target.name} ({target.stat().st_size / 1024**3:.2f} GB) 耗时 {time.time()-t0:.1f}s")
    print("[1/4] 模型准备完毕！\n")


def ensure_comfy():
    print("=== [2/4] 检查与启动 ComfyUI 推理服务 ===")
    running = False
    try:
        with urllib.request.urlopen(f"{COMFY_HOST}/system_stats", timeout=3) as r:
            if r.status == 200:
                running = True
    except Exception:
        pass

    if not running:
        print("正在后台启动 ComfyUI...")
        cmd = [
            "python3", "main.py",
            "--listen", "127.0.0.1",
            "--port", "8188",
            "--lowvram",
            "--extra-model-paths-config", str(REPO_DIR / "setup" / "extra_model_paths_linux.yaml"),
            "--input-directory", str(REPO_DIR / "runtime" / "inputs"),
            "--output-directory", str(REPO_DIR / "runtime" / "outputs")
        ]
        log_f = open("/content/comfy_server.log", "w")
        subprocess.Popen(cmd, cwd=str(COMFY_DIR), stdout=log_f, stderr=subprocess.STDOUT)
        for _ in range(60):
            try:
                with urllib.request.urlopen(f"{COMFY_HOST}/system_stats", timeout=2) as r:
                    if r.status == 200:
                        running = True
                        break
            except Exception:
                time.sleep(1)
        if not running:
            raise RuntimeError("ComfyUI 启动失败，请检查 /content/comfy_server.log")
        print("ComfyUI 启动成功！")
    else:
        print("ComfyUI 已经在后台平稳运行。")
    print("[2/4] 推理服务就绪！\n")


def run_cmd(cmd, desc):
    print(f">>> {desc}...")
    t0 = time.time()
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if p.returncode != 0:
        print(f"❌ 失败: {desc}\n{p.stdout}")
        sys.exit(1)
    print(f"✔ 完成: {desc} (耗时 {time.time()-t0:.1f}s)")


def step_keyframes():
    print("=== [3/4] 生成周明基准肖像与 S04 首帧 (MiniMax-H3-Image) ===")
    ref_zhou = FRAMES_DIR / "ref_zhou.png"
    if not ref_zhou.exists():
        prompt_zhou = (
            "A 26-year-old handsome Chinese male professional with neat short black hair and calm confident expression, "
            "wearing a crisp white formal dress shirt with top button unbuttoned, standing in a blurred modern executive office, "
            "soft cinematic key light, clean film grain, 8k resolution, photorealistic."
        )
        run_cmd([
            "python3", str(REPO_DIR / "tools" / "gen_image.py"),
            "--model", "minimax-image",
            "--prompt", prompt_zhou,
            "--out", str(ref_zhou),
            "--seed", "202",
            "--steps", "6"
        ], "生成周明基准立绘")

    frame_s04 = FRAMES_DIR / "frame_s04.png"
    if not frame_s04.exists():
        prompt_s04 = (
            "Edit <Picture 1>. The clothing in <Picture 1> is fully preserved: identical crisp white formal dress shirt. "
            "Medium shot, slight low angle, sliding a corporate appointment agreement with a red stamp forward across the table, "
            "confident slight smile on his lips, cinematic victory lighting."
        )
        run_cmd([
            "python3", str(REPO_DIR / "tools" / "gen_image.py"),
            "--model", "minimax-image",
            "--ref", str(ref_zhou),
            "--prompt", prompt_s04,
            "--out", str(frame_s04),
            "--seed", "304",
            "--steps", "6"
        ], "生成分镜首帧 frame_s04.png")
    print("[3/4] S04 首帧与角色一致性锁定完成！\n")


def step_s04_video():
    print("=== [4/4] 渲染分镜 S04 9:16 影视级动态口型视频 (MiniMax H3 Ref2VA) ===")
    out_mp4 = VIDEO_DIR / "s04.mp4"
    if out_mp4.exists() and out_mp4.stat().st_size > 1024 * 1024:
        print(f"[已存在跳过] s04.mp4 ({out_mp4.stat().st_size / 1024**2:.2f} MB)")
        return

    spec = {
        "duration": 5.14,
        "size": [768, 1344],
        "seed": 1004,
        "steps": 14,
        "style": "a realistic cinematic film still from a high-end corporate drama, warm corporate lighting, clean 35mm film grain, photorealistic human skin texture",
        "setting": "a luxury modern executive office with floor-to-ceiling skyscraper window view",
        "first_frame": str(FRAMES_DIR / "frame_s04.png"),
        "subjects": [
            {
                "key": "zhou",
                "desc": "Zhou Ming, a 26-year-old handsome Chinese male professional in a crisp white formal dress shirt",
                "voice": "a victorious, confident young Chinese male voice"
            }
        ],
        "audio": {
            "voice_ref": {
                "subject": "zhou",
                "file": str(AUDIO_DIR / "s04.wav")
            }
        },
        "shots": [
            {
                "camera": "The camera holds a medium shot from a slight low heroic angle on a tripod.",
                "action": "Starting from <Picture 1>, Zhou Ming smoothly slides the red-stamped corporate appointment agreement across the dark table, his eyes shining with victory, curling a calm confident smile at the corners of his lips.",
                "dialogue": [
                    {
                        "subject": "zhou",
                        "line": "这是新资方的委派函，从今天起，我是这里的控股股东。",
                        "lang": "Chinese",
                        "after": "Keeps natural posture and expression after speaking."
                    }
                ]
            }
        ],
        "soundscape": "Quiet executive office room tone.",
        "music": "N/A"
    }

    spec_file = DRAMA_DIR / "spec_s04.json"
    spec_file.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n>>> 正在向 ComfyUI 提交分镜 s04 视频渲染任务 (约需 7~8 分钟)...")
    t0 = time.time()
    shot_out_dir = DRAMA_DIR / "render_s04"
    run_cmd([
        "python3", str(REPO_DIR / "tools" / "h3_shot.py"),
        str(spec_file),
        "--out", str(shot_out_dir),
        "--force"
    ], "渲染分镜 s04 视频")

    matches = sorted(shot_out_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not matches:
        alt_dir = REPO_DIR / "runtime" / "outputs" / "h3_shot"
        matches = sorted(alt_dir.glob("*s04*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)

    if not matches:
        print("❌ 未找到生成的 s04 视频！")
        sys.exit(1)

    shutil.copy2(matches[0], out_mp4)
    print(f"✔ 分镜 s04 视频成功归档至 {out_mp4.name} ({out_mp4.stat().st_size / 1024**2:.2f} MB, 耗时 {time.time()-t0:.1f}s)")
    Path("/content/S04_FINISHED.txt").write_text("DONE\n")


def main():
    print("==========================================================")
    print("🎬 LoPy 《离职底牌》 S04 最终反转镜头 - 极速独立渲染启动")
    print("==========================================================")
    ensure_models()
    ensure_comfy()
    step_keyframes()
    step_s04_video()
    print("==========================================================")
    print("🎉 S04 渲染与封装全部顺利达成！")
    print("==========================================================")


if __name__ == "__main__":
    main()
