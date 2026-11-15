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
DRAMA_DIR = REPO_DIR / "pipeline" / "drama_real_fake_daughter"
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
            raise RuntimeError("ComfyUI 启动失败")
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

def step_keyframes():
    print("=== [3/3] 生成角色基准肖像与 4 镜锁衣控姿首帧 (MiniMax-H3-Image) ===")

    # 1. 真千金顾初基准立绘
    ref_guchu = FRAMES_DIR / "ref_guchu.png"
    if not ref_guchu.exists():
        prompt_guchu = (
            "A 22-year-old strikingly gorgeous Chinese young woman with porcelain skin, sharp bone structure, "
            "neat low black ponytail, wearing a washed simple light grey linen cotton shirt and dark jeans, "
            "standing proud with calm aloof confident eyes, cinematic soft daylight, high society villa background blurred, photorealistic 8k."
        )
        run_cmd([
            "python3", str(REPO_DIR / "tools" / "gen_image.py"),
            "--model", "minimax-image",
            "--prompt", prompt_guchu,
            "--out", str(ref_guchu),
            "--seed", "1101",
            "--steps", "6"
        ], "生成顾初基准立绘")

    # 2. 假千金苏晚晚基准立绘
    ref_wanwan = FRAMES_DIR / "ref_wanwan.png"
    if not ref_wanwan.exists():
        prompt_wanwan = (
            "A 22-year-old delicate-looking Chinese young heiress with softly curled chestnut brown hair, "
            "wearing an expensive pastel pink-and-white designer soft tulle organza dress, pearl drop earrings, "
            "delicate fake innocent teary eyes with subtle hidden smirk, luxury mansion interior lighting, 8k photorealistic."
        )
        run_cmd([
            "python3", str(REPO_DIR / "tools" / "gen_image.py"),
            "--model", "minimax-image",
            "--prompt", prompt_wanwan,
            "--out", str(ref_wanwan),
            "--seed", "1202",
            "--steps", "6"
        ], "生成苏晚晚基准立绘")

    # 3. 苏夫人基准立绘
    ref_mother = FRAMES_DIR / "ref_mother.png"
    if not ref_mother.exists():
        prompt_mother = (
            "A 48-year-old noble, arrogant and stern wealthy Chinese matriarch, wearing a luxurious dark emerald green velvet cheongsam "
            "with a beige cashmere shawl, jade bangle on wrist, cold dismissive aristocratic expression, sitting in a leather sofa, photorealistic."
        )
        run_cmd([
            "python3", str(REPO_DIR / "tools" / "gen_image.py"),
            "--model", "minimax-image",
            "--prompt", prompt_mother,
            "--out", str(ref_mother),
            "--seed", "1303",
            "--steps", "6"
        ], "生成苏夫人基准立绘")

    # 4. 锁衣控姿生成 4 镜首帧
    shots_info = [
        ("frame_s01.png", ref_wanwan, (
            "Edit <Picture 1>. The clothing in <Picture 1> is strictly preserved: identical pastel pink-and-white designer tulle organza dress. "
            "Medium shot, standing beside an older lady on a sofa, gently dabbing a tear with fingertip, looking forward with fake pity and subtle condescending smirk."
        ), "2001"),
        ("frame_s02.png", ref_guchu, (
            "Edit <Picture 1>. The clothing in <Picture 1> is strictly preserved: identical simple light grey linen cotton shirt. "
            "Front view close-up, hands casually in denim pockets, curling a sharp mocking smirk at corner of lips, fearless piercing gaze staring ahead."
        ), "2002"),
        ("frame_s03.png", ref_mother, (
            "Edit <Picture 1>. The clothing in <Picture 1> is strictly preserved: identical dark emerald green velvet cheongsam and cashmere shawl. "
            "Medium close-up, slamming a delicate white porcelain teacup onto the marble table, frowning deeply with icy reprimanding anger."
        ), "2003"),
        ("frame_s04.png", ref_guchu, (
            "Edit <Picture 1>. The clothing in <Picture 1> is strictly preserved: identical light grey linen cotton shirt. "
            "Heroic low angle close-up, throwing a thick manila envelope and DNA paternity report onto the marble table, imposing overwhelming aura, cold victorious sneer."
        ), "2004"),
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

    print("[3/3] 4 镜首帧与角色一致性锁定全部完成！\n")
    Path("/content/KEYFRAMES_DONE.txt").write_text("DONE\n")

def main():
    print("==========================================================")
    print("🎬 LoPy 《真假千金》 Stage 2 - 云端首帧极速生产启动")
    print("==========================================================")
    ensure_models()
    ensure_comfy()
    step_keyframes()
    print("==========================================================")
    print("🎉 首帧渲染全部圆满达成！")
    print("==========================================================")

if __name__ == "__main__":
    main()
