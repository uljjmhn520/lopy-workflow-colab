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
DRAMA_DIR = REPO_DIR / "pipeline" / "drama_zerozerozero"
FRAMES_DIR = DRAMA_DIR / "frames"
FRAMES_DIR.mkdir(parents=True, exist_ok=True)

# 仅需 H3-Image 图像三件套，秒速下载
MODELS_TO_DOWNLOAD = [
    ("diffusion_models/minimax_h3_image_pruned_int8_convrot.safetensors",
     "https://huggingface.co/Comfy-Org/MiniMax-H3-Image/resolve/main/diffusion_models/minimax_h3_image_pruned_int8_convrot.safetensors"),
    ("text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors",
     "https://huggingface.co/Comfy-Org/MiniMax-H3-Image/resolve/main/text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"),
    ("vae/minimax_h3_image_vae_fp16.safetensors",
     "https://huggingface.co/Comfy-Org/MiniMax-H3-Image/resolve/main/vae/minimax_h3_image_vae_fp16.safetensors"),
]

def ensure_models():
    print("=== [1/3] 检查与下载 H3 图像模型 (aria2c 极速并发) ===")
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
    print("[1/3] 模型准备完毕！\n")

def ensure_comfy():
    print("=== [2/3] 检查与启动 ComfyUI 推理服务 ===")
    running = False
    try:
        with urllib.request.urlopen(f"{COMFY_HOST}/system_stats", timeout=3) as r:
            if r.status == 200: running = True
    except Exception: pass

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
    print("[2/3] 推理服务就绪！\n")

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
    print("=== [3/3] 渲染艾玛基准定妆肖像与 4 镜首尾帧 (MiniMax-H3-Image) ===")
    
    # 1. 艾玛基准定妆立绘
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
        ], "生成艾玛基准肖像")

    # 2. 4 镜首尾帧渲染
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

    # 合成 2x2 审查画廊
    gallery_out = FRAMES_DIR / "gallery_zerozerozero_preview.png"
    frames_for_gallery = [
        str(FRAMES_DIR / "frame_s01.png"),
        str(FRAMES_DIR / "frame_s02.png"),
        str(FRAMES_DIR / "frame_s03_last.png"),
        str(FRAMES_DIR / "frame_s04.png"),
    ]
    if all(Path(f).exists() for f in frames_for_gallery):
        run_cmd([
            "python3", str(REPO_DIR / "tools" / "make_gallery.py"),
            *frames_for_gallery,
            "--out", str(gallery_out)
        ], "合成 2x2 首帧审查画廊")

    print("[3/3] 4 镜首尾帧与角色一致性锁定全部完成！\n")
    Path("/content/KEYFRAMES_DONE.txt").write_text("DONE\n")

def main():
    print("==========================================================")
    print("🎬 LoPy 《零零零·单刀赴会》 Stage 2 - 首帧极速生产启动")
    print("==========================================================")
    ensure_models()
    ensure_comfy()
    step_keyframes()
    print("==========================================================")
    print("🎉 首帧渲染全部圆满达成！请创作者查看画廊并核验确认。")
    print("==========================================================")

if __name__ == "__main__":
    main()
