import os
import sys
import time
import json
import shutil
import subprocess
import urllib.request
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from huggingface_hub import hf_hub_download

REPO_DIR = Path("/content/lopy-workflow-colab")
H3_MODELS = REPO_DIR / "models" / "H3" / "models"
COMFY_DIR = Path("/content/ComfyUI")
COMFY_HOST = "http://127.0.0.1:8188"
DRAMA_DIR = REPO_DIR / "pipeline" / "drama_workplace"
AUDIO_DIR = DRAMA_DIR / "audio"
FRAMES_DIR = DRAMA_DIR / "frames"
VIDEO_DIR = DRAMA_DIR / "video"

# 1. 下载模型定义
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
    print("=== [1/5] 检查与多线程下载 H3 图像与视频模型 (aria2c 极速下载) ===")
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
    print("[1/5] 模型准备完毕！\n")


def ensure_comfy():
    print("=== [2/5] 检查与启动 ComfyUI 推理服务 ===")
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
    print("[2/5] 推理服务就绪！\n")


def run_cmd(cmd, desc):
    print(f">>> {desc}...")
    t0 = time.time()
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if p.returncode != 0:
        print(f"❌ 失败: {desc}\n{p.stdout}")
        sys.exit(1)
    print(f"✔ 完成: {desc} (耗时 {time.time()-t0:.1f}s)")
    return p.stdout


def step_keyframes():
    print("=== [3/5] 生成角色基准肖像与 4 镜锁衣首帧 (MiniMax-H3-Image) ===")
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)

    # 1. 生成林总基准肖像
    ref_lin = FRAMES_DIR / "ref_lin.png"
    if not ref_lin.exists():
        prompt_lin = (
            "A 35-year-old Chinese female corporate executive with shoulder-length neat black hair and sharp piercing eyes, "
            "wearing a dark grey tailored business blazer over a white silk blouse, sitting in a luxury modern executive office, "
            "cinematic corporate lighting, shallow depth of field, high-contrast rim light, 8k resolution, photorealistic."
        )
        run_cmd([
            "python3", str(REPO_DIR / "tools" / "gen_image.py"),
            "--model", "minimax-image",
            "--prompt", prompt_lin,
            "--out", str(ref_lin),
            "--seed", "101",
            "--steps", "6"
        ], "生成林总基准立绘")

    # 2. 生成周明基准肖像
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

    # 3. 锁衣控姿生成 4 镜首帧
    shots_info = [
        ("frame_s01.png", ref_lin, (
            "Edit <Picture 1>. The clothing in <Picture 1> is fully preserved: she wears the exact identical dark grey tailored business blazer "
            "over a white silk blouse. Medium close-up, sitting behind a dark executive desk, body leaning slightly forward, "
            "staring intensely forward with authoritative questioning anger."
        ), "301"),
        ("frame_s02.png", ref_zhou, (
            "Edit <Picture 1>. The clothing in <Picture 1> is fully preserved: he wears the exact identical crisp white formal dress shirt. "
            "Reverse close-up angle, eye-level, composed and completely unfazed, calm confident expression."
        ), "302"),
        ("frame_s03.png", ref_lin, (
            "Edit <Picture 1>. The clothing in <Picture 1> is fully preserved: identical dark grey blazer and white blouse. "
            "Tight close-up on the 35-year-old female executive's face, frowning slightly, suspicious and unsettled eyes, cold questioning tension."
        ), "303"),
        ("frame_s04.png", ref_zhou, (
            "Edit <Picture 1>. The clothing in <Picture 1> is fully preserved: identical crisp white formal dress shirt. "
            "Medium shot, slight low angle, sliding a corporate appointment agreement with a red stamp forward across the table, "
            "confident slight smile on his lips, cinematic victory lighting."
        ), "304"),
    ]

    for fname, ref_img, prompt, seed in shots_info:
        dst = FRAMES_DIR / fname
        if not dst.exists():
            run_cmd([
                "python3", str(REPO_DIR / "tools" / "gen_image.py"),
                "--model", "minimax-image",
                "--ref", str(ref_img),
                "--prompt", prompt,
                "--out", str(dst),
                "--seed", seed,
                "--steps", "6"
            ], f"生成分镜首帧 {fname}")
    print("[3/5] 4 镜首帧与角色一致性锁定完成！\n")


def step_videos():
    print("=== [4/5] 批量渲染 4 镜 9:16 影视级动态口型视频 (MiniMax H3 Ref2VA) ===")
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)

    shots_specs = [
        {
            "id": "s01",
            "duration": 5.34,
            "seed": 1001,
            "first_frame": str(FRAMES_DIR / "frame_s01.png"),
            "audio_file": str(AUDIO_DIR / "s01.wav"),
            "subject_key": "lin",
            "subject_desc": "Lin Zong, a 35-year-old Chinese female executive in a dark grey business blazer and white silk blouse",
            "voice_desc": "an authoritative, sharp mature Chinese female voice",
            "camera": "The camera holds a steady medium close-up shot at eye level on a tripod.",
            "action": "Starting from <Picture 1>, Lin Zong leans forward with an authoritative intense expression, staring forward behind her executive desk, speaking firmly with clear articulation and commanding authority.",
            "dialogue": "周明，公司刚拿到两千万融资，你现在跟我提离职？",
        },
        {
            "id": "s02",
            "duration": 4.32,
            "seed": 1002,
            "first_frame": str(FRAMES_DIR / "frame_s02.png"),
            "audio_file": str(AUDIO_DIR / "s02.wav"),
            "subject_key": "zhou",
            "subject_desc": "Zhou Ming, a 26-year-old handsome Chinese male professional in a crisp white formal dress shirt",
            "voice_desc": "a calm, composed confident young Chinese male voice",
            "camera": "The camera holds a reverse close-up angle at eye level on a tripod.",
            "action": "Starting from <Picture 1>, Zhou Ming stands composed and completely calm, facing the camera at eye level, breathing steadily and articulating his response with effortless confidence.",
            "dialogue": "林总，您可能误会了，我不是来提离职的。",
        },
        {
            "id": "s03",
            "duration": 3.38,
            "seed": 1003,
            "first_frame": str(FRAMES_DIR / "frame_s03.png"),
            "audio_file": str(AUDIO_DIR / "s03.wav"),
            "subject_key": "lin",
            "subject_desc": "Lin Zong, a 35-year-old Chinese female executive in a dark grey business blazer",
            "voice_desc": "a questioning, suspicious mature Chinese female voice",
            "camera": "The camera holds a tight close-up on Lin Zong's face with a very subtle push-in.",
            "action": "Starting from <Picture 1>, Lin Zong's eyebrows knit slightly in suspicion and unease, her eyes narrowing as she questions the document in front of her with cold questioning intensity.",
            "dialogue": "那你递这份协议是什么意思？",
        },
        {
            "id": "s04",
            "duration": 5.14,
            "seed": 1004,
            "first_frame": str(FRAMES_DIR / "frame_s04.png"),
            "audio_file": str(AUDIO_DIR / "s04.wav"),
            "subject_key": "zhou",
            "subject_desc": "Zhou Ming, a 26-year-old handsome Chinese male professional in a crisp white formal dress shirt",
            "voice_desc": "a victorious, confident young Chinese male voice",
            "camera": "The camera holds a medium shot from a slight low heroic angle on a tripod.",
            "action": "Starting from <Picture 1>, Zhou Ming smoothly slides the red-stamped corporate appointment agreement across the dark table, his eyes shining with victory, curling a calm confident smile at the corners of his lips.",
            "dialogue": "这是新资方的委派函，从今天起，我是这里的控股股东。",
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
            "style": "a realistic cinematic film still from a high-end corporate drama, warm corporate lighting, clean 35mm film grain, photorealistic human skin texture",
            "setting": "a luxury modern executive office with floor-to-ceiling skyscraper window view",
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
            "soundscape": "Quiet executive office room tone.",
            "music": "N/A"
        }

        spec_file = DRAMA_DIR / f"spec_{sid}.json"
        spec_file.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")

        print(f"\n>>> 正在向 ComfyUI 提交分镜 {sid} 视频渲染任务 (约需 3~4 分钟)...")
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
            # 备选扫描
            alt_dir = REPO_DIR / "runtime" / "outputs" / "h3_shot"
            matches = sorted(alt_dir.glob(f"*{sid}*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)

        if not matches:
            print(f"❌ 未找到生成的 {sid} 视频！")
            sys.exit(1)

        shutil.copy2(matches[0], out_mp4)
        print(f"✔ 分镜 {sid} 视频成功归档至 {out_mp4.name} ({out_mp4.stat().st_size / 1024**2:.2f} MB, 耗时 {time.time()-t0:.1f}s)")

    print("[4/5] 4 镜视频渲染全部圆满完成！\n")


def main():
    print("==========================================================")
    print("🎬 LoPy 《离职底牌》 4 镜短剧 - Colab 批量渲染管线启动")
    print("==========================================================")
    ensure_models()
    ensure_comfy()
    step_keyframes()
    step_videos()
    print("==========================================================")
    print("🎉 Colab 端 4 镜全流程渲染全部顺利达成！")
    print("==========================================================")


if __name__ == "__main__":
    main()
