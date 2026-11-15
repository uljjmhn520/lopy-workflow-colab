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
DRAMA_DIR = REPO_DIR / "pipeline" / "drama_zerozerozero"
AUDIO_DIR = DRAMA_DIR / "audio"
FRAMES_DIR = DRAMA_DIR / "frames"
VIDEO_DIR = DRAMA_DIR / "video"

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
    print("=== [3/5] 生成艾玛基准肖像与 4 镜锁衣控姿首尾帧 (MiniMax-H3-Image) ===")
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)

    # 1. 生成艾玛基准肖像
    ref_emma = FRAMES_DIR / "ref_emma.png"
    if not ref_emma.exists():
        prompt_emma = (
            "A 35-year-old European female cartel boss with sleek cropped blonde hair, cold piercing grey-blue eyes, "
            "sculpted high cheekbones, wearing a tailored charcoal dark wool trench coat with a high collar, "
            "black turtleneck underneath, black leather gloves, standing in a dimly lit warehouse, "
            "cinematic moody lighting, high contrast, anamorphic film grain, photorealistic, 8k resolution."
        )
        run_cmd([
            "python3", str(REPO_DIR / "tools" / "gen_image.py"),
            "--model", "minimax-image",
            "--prompt", prompt_emma,
            "--out", str(ref_emma),
            "--seed", "801",
            "--steps", "6"
        ], "生成艾玛基准定妆肖像")

    # 2. 生成各镜首尾帧
    shots_info = [
        ("frame_s01.png", ref_emma, (
            "Edit <Picture 1>. The clothing and hairstyle in <Picture 1> are strictly preserved. "
            "Back medium tracking shot: Emma walking forward through a concrete industrial doorway into a dark safehouse. "
            "Two masked armed cartel guards in tactical vests with assault rifles stand on both sides, cinematic shadows."
        ), "802"),
        ("frame_s02.png", ref_emma, (
            "Edit <Picture 1>. The clothing and face in <Picture 1> are strictly preserved. "
            "Frontal medium shot: Emma walking steadily forward, piercing cold gaze looking straight into camera, "
            "stopping directly in front of an old bloodstained dark red leather sofa. In the background, two dead cartel members lie slumped on the sofa."
        ), "803"),
        ("frame_s03_first.png", ref_emma, (
            "Edit <Picture 1>. The clothing and face in <Picture 1> are strictly preserved. "
            "Side 45-degree angle medium shot: Emma standing directly between two dead bodies slumped on the sofa, "
            "looking down calmly at the empty middle cushion, preparing to sit down."
        ), "804"),
        ("frame_s03_last.png", ref_emma, (
            "Edit <Picture 1>. The clothing and face in <Picture 1> are strictly preserved. "
            "Side 45-degree angle medium shot: Emma is now completely seated in the center of the dark red leather sofa, "
            "flanked by the two lifeless bodies slumped on either side. Her back is leaning calmly against the sofa, gloved hands resting on her lap."
        ), "805"),
        ("frame_s04.png", ref_emma, (
            "Edit <Picture 1>. The clothing and face in <Picture 1> are strictly preserved. "
            "Low-angle heroic close-up: Emma sitting dead center between the two slumped lifeless corpses. "
            "Her chin is slightly raised, icy intimidating gaze fixed forward, commanding the entire room with ruthless aura."
        ), "806"),
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
            ], f"生成分镜帧 {fname}")
    print("[3/5] 首尾帧与角色一致性锁定完成！\n")


def step_videos():
    print("=== [4/5] 批量渲染 4 镜影视级伪长镜头视频 (MiniMax H3 Ref2VA) ===")
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)

    shots_specs = [
        {
            "id": "s01",
            "duration": 3.8,
            "seed": 2001,
            "first_frame": str(FRAMES_DIR / "frame_s01.png"),
            "audio_file": str(AUDIO_DIR / "s01.wav"),
            "subject_key": "emma",
            "subject_desc": "Emma Lynne, a blonde female boss in a charcoal wool trench coat and black leather gloves",
            "voice_desc": "deep atmospheric room tone with heavy stone footsteps",
            "camera": "The camera follows steadily behind Emma in a smooth forward back-tracking motion.",
            "action": "Starting from <Picture 1>, Emma walks steadily forward through the doorway into the dim industrial room with upright posture. Armed cartel guards stand frozen on both sides holding rifles.",
            "dialogue": "",
        },
        {
            "id": "s02",
            "duration": 4.2,
            "seed": 2002,
            "first_frame": str(FRAMES_DIR / "frame_s02.png"),
            "audio_file": str(AUDIO_DIR / "s02.wav"),
            "subject_key": "emma",
            "subject_desc": "Emma Lynne, a ruthless female boss with sleek blonde hair and cold piercing blue eyes",
            "voice_desc": "subtle ambient air and breathing tension",
            "camera": "The camera dollies backwards smoothly at eye level, matching Emma's forward walking pace.",
            "action": "Starting from <Picture 1>, Emma steps forward steadily facing the camera with an unblinking cold gaze, coming to a smooth stop directly in front of the bloodstained leather sofa between the two lifeless corpses.",
            "dialogue": "",
        },
        {
            "id": "s03",
            "duration": 4.5,
            "seed": 2003,
            "first_frame": str(FRAMES_DIR / "frame_s03_first.png"),
            "last_frame": str(FRAMES_DIR / "frame_s03_last.png"),
            "audio_file": str(AUDIO_DIR / "s03.wav"),
            "subject_key": "emma",
            "subject_desc": "Emma Lynne, a blonde cartel boss in a dark charcoal trench coat",
            "voice_desc": "heavy leather sofa compression friction sound",
            "camera": "LOCKED-OFF STATIC CAMERA on a tripod at a 45-degree angle.",
            "action": "Starting from <Picture 1> and moving toward <Picture 2>, Emma calmly and smoothly lowers her body to sit down directly on the center of the sofa between the two slumped corpses, resting her hands on her lap with absolute cold composure.",
            "dialogue": "",
        },
        {
            "id": "s04",
            "duration": 4.5,
            "seed": 2004,
            "first_frame": str(FRAMES_DIR / "frame_s04.png"),
            "audio_file": str(AUDIO_DIR / "s04.wav"),
            "subject_key": "emma",
            "subject_desc": "Emma Lynne, a fearless blonde cartel boss sitting between two corpses",
            "voice_desc": "a cold, deep, authoritative female voice speaking with icy conviction",
            "camera": "Low-angle close-up camera pushing forward extremely slowly toward Emma's face.",
            "action": "Starting from <Picture 1>, Emma sits perfectly composed between the dead bodies, subtly lifting her chin with ruthless authority, looking forward while speaking with precise cold lip movements, eyes narrow and commanding.",
            "dialogue": "尸体处理完之前，我们先把货款结了。叫能做主的人出来。",
        },
    ]

    for spec in shots_specs:
        out_mp4 = VIDEO_DIR / f"{spec['id']}.mp4"
        if out_mp4.exists():
            print(f"[已存在跳过] {out_mp4.name}")
            continue

        prompt_text = (
            f"Subject: {spec['subject_desc']}.\n"
            f"Atmosphere: dim cartel safehouse, harsh sunlight beams through blinds, cinematic suspense, 8k.\n"
            f"Camera: {spec['camera']}\n"
            f"Action: {spec['action']}\n"
            f"Voice: {spec['voice_desc']}.\n"
            f"Dialogue: \"{spec['dialogue']}\""
        )

        cmd = [
            "python3", str(REPO_DIR / "tools" / "h3_shot.py"),
            "--first", spec["first_frame"],
            "--prompt", prompt_text,
            "--sec", str(spec["duration"]),
            "--seed", str(spec["seed"]),
            "--out", str(out_mp4)
        ]
        if "last_frame" in spec:
            cmd.extend(["--last", spec["last_frame"]])
        if Path(spec["audio_file"]).exists():
            cmd.extend(["--audio", spec["audio_file"]])

        run_cmd(cmd, f"渲染分镜视频 {spec['id']}")

    print("[4/5] 4 镜伪长镜头视频渲染完成！\n")


def step_assembly():
    print("=== [5/5] 执行自动剪辑、音效混流与成片导出 ===")
    run_cmd([
        "python3", str(DRAMA_DIR / "assemble_film.py")
    ], "Stage 4 剪辑总装")
    print("[5/5] 全流程顺利完成！成片保存在 runtime/outputs/drama_zerozerozero_v1.mp4\n")


if __name__ == "__main__":
    t_start = time.time()
    ensure_models()
    ensure_comfy()
    step_keyframes()
    step_videos()
    step_assembly()
    print(f"🎉 全部流程执行成功，累计耗时: {time.time()-t_start:.1f} 秒！")
