import os
import sys
import time
import json
import shutil
import subprocess
import urllib.request
from pathlib import Path

REPO_DIR = Path("/content/lopy-workflow-colab")
H3_MODELS = REPO_DIR / "models" / "H3" / "models"
COMFY_DIR = Path("/content/ComfyUI")
COMFY_HOST = "http://127.0.0.1:8188"
DRAMA_DIR = REPO_DIR / "pipeline" / "drama_real_fake_daughter"
AUDIO_DIR = DRAMA_DIR / "audio"
FRAMES_DIR = DRAMA_DIR / "frames"
VIDEO_DIR = DRAMA_DIR / "video"
VIDEO_DIR.mkdir(parents=True, exist_ok=True)

MODELS_TO_DOWNLOAD = [
    ("text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors",
     "https://huggingface.co/Comfy-Org/MiniMax-H3-Image/resolve/main/text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"),
    ("diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors",
     "https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/7e75982b97cd5a41d2dcfa1904ee88d0686d6fd1/diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors"),
    ("vae/minimax_h3_video_vae_fp16.safetensors",
     "https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/7e75982b97cd5a41d2dcfa1904ee88d0686d6fd1/vae/minimax_h3_video_vae_fp16.safetensors"),
    ("vae/minimax_h3_audio_vae_fp32.safetensors",
     "https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/7e75982b97cd5a41d2dcfa1904ee88d0686d6fd1/vae/minimax_h3_audio_vae_fp32.safetensors")
]


def ensure_models():
    print("=== [1/3] 检查与下载 H3 视频生成模型 (aria2c 极速并发) ===")
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
    print("[1/3] 视频模型准备完毕！\n")


def ensure_audio():
    print("=== [2/3] 检查音频素材 ===")
    if not (AUDIO_DIR / "s01.wav").exists():
        if Path("/content/drama_audio.tar.gz").exists():
            print("正在解压 /content/drama_audio.tar.gz ...")
            shutil.unpack_archive("/content/drama_audio.tar.gz", str(DRAMA_DIR))
    if not (AUDIO_DIR / "s01.wav").exists():
        raise RuntimeError("音频素材未找到，请检查 audio 目录！")
    print("[2/3] 音频素材检查完毕！\n")


def ensure_comfy():
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
            raise RuntimeError("ComfyUI 启动失败")
        print("ComfyUI 启动成功！")
    else:
        print("ComfyUI 已经在后台平稳运行。")


def run_cmd(cmd, desc):
    print(f">>> {desc}...", flush=True)
    t0 = time.time()
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    for line in iter(p.stdout.readline, ''):
        print(line, end='', flush=True)
    p.stdout.close()
    ret = p.wait()
    if ret != 0:
        print(f"❌ 失败: {desc} (退出码 {ret})", flush=True)
        sys.exit(1)
    print(f"✔ 完成: {desc} (耗时 {time.time()-t0:.1f}s)", flush=True)


def step_videos():
    print("=== [3/3] 批量渲染 4 镜 9:16 影视级动态口型视频 (MiniMax H3 Ref2VA) ===")

    shots_specs = [
        {
            "id": "s04",
            "duration": 4.8,
            "seed": 2004,
            "first_frame": str(FRAMES_DIR / "frame_s04.png"),
            "audio_file": str(AUDIO_DIR / "s04.wav"),
            "subject_key": "guchu",
            "subject_desc": "Gu Chu, a 22-year-old strikingly gorgeous Chinese young woman in a washed light grey linen cotton shirt",
            "voice_desc": "a calm, piercing victorious young Chinese female voice",
            "camera": "The camera holds a medium shot from a slight low heroic angle on a tripod.",
            "action": "Starting from <Picture 1>, Gu Chu tosses the DNA report onto the marble coffee table, her eyes piercing and commanding, articulating her words calmly with an overwhelming victorious sneer.",
            "dialogue": "苏夫人别急着心疼，当年换掉我的幕后主使，正是她的亲生母亲。",
        },
    ]

    for item in shots_specs:
        sid = item["id"]
        out_mp4 = VIDEO_DIR / f"{sid}.mp4"
        if out_mp4.exists() and out_mp4.stat().st_size > 1024 * 1024:
            print(f"[已存在跳过] {out_mp4.name} ({out_mp4.stat().st_size / 1024**2:.2f} MB)")
            continue

        spec = {
            "duration": item["duration"],
            "size": [768, 1344],
            "seed": item["seed"],
            "steps": 14,
            "style": "a realistic cinematic film still from a high-end luxury drama, warm cinematic European mansion lighting, 35mm film grain, photorealistic human skin texture",
            "setting": "a grand luxury European style mansion living room with crystal chandelier and marble floor",
            "first_frame": item["first_frame"],
            "subjects": [
                {
                    "key": item["subject_key"],
                    "desc": item["subject_desc"],
                    "voice": item["voice_desc"]
                }
            ],
            "audio": {
                "voice_ref": {
                    "subject": item["subject_key"],
                    "file": item["audio_file"]
                }
            },
            "shots": [
                {
                    "camera": item["camera"],
                    "action": item["action"],
                    "dialogue": [
                        {
                            "subject": item["subject_key"],
                            "line": item["dialogue"],
                            "lang": "Chinese",
                            "after": "Keeps natural posture and expression after speaking."
                        }
                    ]
                }
            ],
            "soundscape": "Quiet luxury European mansion room tone.",
            "music": "N/A"
        }

        spec_file = DRAMA_DIR / f"spec_{sid}.json"
        spec_file.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")

        print(f"\n>>> 正在向 ComfyUI 提交分镜 {sid} 视频渲染任务 (约需 1.5~2.5 分钟)...")
        t0 = time.time()
        shot_out_dir = DRAMA_DIR / f"render_{sid}"
        run_cmd([
            "python3", str(REPO_DIR / "tools" / "h3_shot.py"),
            str(spec_file),
            "--out", str(shot_out_dir),
            "--force"
        ], f"渲染分镜 {sid} 视频")

        # 找到渲染产物中的 mp4
        matches = sorted(shot_out_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not matches:
            alt_dir = REPO_DIR / "runtime" / "outputs" / "h3_shot"
            matches = sorted(alt_dir.glob(f"*{sid}*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)

        if not matches:
            print(f"❌ 未找到生成的 {sid} 视频！")
            sys.exit(1)

        shutil.copy2(matches[0], out_mp4)
        Path(f"/content/{sid}_DONE.txt").write_text("DONE\n")
        print(f"✔ 分镜 {sid} 视频成功归档至 {out_mp4.name} ({out_mp4.stat().st_size / 1024**2:.2f} MB, 耗时 {time.time()-t0:.1f}s)")

    print("[3/3] 4 镜视频渲染全部圆满完成！\n")
    Path("/content/VIDEO_DONE.txt").write_text("DONE\n")


def main():
    print("==========================================================")
    print("🎬 LoPy 《真假千金》 Stage 3 - 云端视频批量渲染启动")
    print("==========================================================")
    ensure_models()
    ensure_audio()
    ensure_comfy()
    step_videos()
    print("==========================================================")
    print("🎉 Stage 3 视频渲染全部顺利达成！")
    print("==========================================================")


if __name__ == "__main__":
    main()
