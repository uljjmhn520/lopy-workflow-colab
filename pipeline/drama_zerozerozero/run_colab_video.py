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
AUDIO_DIR = DRAMA_DIR / "audio"
FRAMES_DIR = DRAMA_DIR / "frames"
VIDEO_DIR = DRAMA_DIR / "video"
VIDEO_DIR.mkdir(parents=True, exist_ok=True)

MODELS_TO_DOWNLOAD = [
    ("diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors",
     "https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/7e75982b97cd5a41d2dcfa1904ee88d0686d6fd1/diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors"),
    ("text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors",
     "https://huggingface.co/Comfy-Org/MiniMax-H3-Image/resolve/main/text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"),
    ("vae/minimax_h3_video_vae_fp16.safetensors",
     "https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/7e75982b97cd5a41d2dcfa1904ee88d0686d6fd1/vae/minimax_h3_video_vae_fp16.safetensors"),
    ("vae/minimax_h3_audio_vae_fp32.safetensors",
     "https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/7e75982b97cd5a41d2dcfa1904ee88d0686d6fd1/vae/minimax_h3_audio_vae_fp32.safetensors")
]

def ensure_video_models():
    print("=== [1/4] 检查与下载 H3 视频生成模型 (aria2c 极速并发) ===")
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
    print("[1/4] 视频模型准备完毕！\n")

def ensure_comfy():
    print("=== [2/4] 检查与启动 ComfyUI 推理服务 ===")
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
    print("[2/4] 推理服务就绪！\n")

def run_cmd(cmd, desc):
    print(f">>> {desc}...")
    t0 = time.time()
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if p.returncode != 0:
        print(f"❌ 失败: {desc}\n{p.stdout}")
        sys.exit(1)
    print(f"✔ 完成: {desc} (耗时 {time.time()-t0:.1f}s)")
    return p.stdout

def step_videos():
    print("=== [3/4] 批量渲染 4 镜影视级伪长镜头视频 (MiniMax H3 Ref2VA) ===")
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)

    shots_specs = [
        {
            "id": "s01",
            "duration": 3.8,
            "seed": 2001,
            "first_frame": str(FRAMES_DIR / "frame_s01.png"),
            "subject_desc": "Emma Lynne, a blonde female boss in a charcoal wool trench coat and black leather gloves",
            "voice_desc": "deep atmospheric room tone with heavy stone footsteps",
            "camera": "The camera follows steadily behind Emma in a smooth forward back-tracking motion on a tripod.",
            "action": "Starting from <Picture 1>, Emma walks steadily forward through the doorway into the dim industrial room with upright posture. Armed cartel guards stand frozen on both sides holding rifles.",
            "audio_file": str(AUDIO_DIR / "s01.wav"),
            "dialogue": "",
        },
        {
            "id": "s02",
            "duration": 4.2,
            "seed": 2002,
            "first_frame": str(FRAMES_DIR / "frame_s02.png"),
            "subject_desc": "Emma Lynne, a ruthless female boss with sleek blonde hair and cold piercing blue eyes",
            "voice_desc": "subtle ambient air and breathing tension",
            "camera": "The camera dollies backwards smoothly at eye level, matching Emma's forward walking pace.",
            "action": "Starting from <Picture 1>, Emma steps forward steadily facing the camera with an unblinking cold gaze, coming to a smooth stop directly in front of the bloodstained leather sofa between the two lifeless corpses.",
            "audio_file": str(AUDIO_DIR / "s02.wav"),
            "dialogue": "",
        },
        {
            "id": "s03",
            "duration": 4.5,
            "seed": 2003,
            "first_frame": str(FRAMES_DIR / "frame_s03_first.png"),
            "last_frame": str(FRAMES_DIR / "frame_s03_last.png"),
            "subject_desc": "Emma Lynne, a blonde cartel boss in a dark charcoal trench coat",
            "voice_desc": "heavy leather sofa compression friction sound",
            "camera": "LOCKED-OFF STATIC CAMERA on a tripod at a 45-degree angle.",
            "action": "Starting from <Picture 1> and moving toward <Picture 2>, Emma calmly and smoothly lowers her body to sit down directly on the center of the sofa between the two slumped corpses, resting her hands on her lap with absolute cold composure.",
            "audio_file": str(AUDIO_DIR / "s03.wav"),
            "dialogue": "",
        },
        {
            "id": "s04",
            "duration": 4.5,
            "seed": 2004,
            "first_frame": str(FRAMES_DIR / "frame_s04.png"),
            "subject_desc": "Emma Lynne, a fearless blonde cartel boss sitting between two corpses",
            "voice_desc": "a cold, deep, authoritative female voice speaking with icy conviction",
            "camera": "Low-angle close-up camera pushing forward extremely slowly toward Emma's face.",
            "action": "Starting from <Picture 1>, Emma sits perfectly composed between the dead bodies, subtly lifting her chin with ruthless authority, looking forward while speaking with precise cold lip movements, eyes narrow and commanding.",
            "audio_file": str(AUDIO_DIR / "s04.wav"),
            "dialogue": "尸体处理完之前，我们先把货款结了。叫能做主的人出来。",
        },
    ]

    for item in shots_specs:
        sid = item["id"]
        out_mp4 = VIDEO_DIR / f"{sid}.mp4"
        if out_mp4.exists() and out_mp4.stat().st_size > 1024 * 1024:
            print(f"[已存在跳过] {out_mp4.name}")
            continue

        spec = {
            "duration": item["duration"],
            "size": [768, 1344],
            "seed": item["seed"],
            "steps": 14,
            "style": "a realistic cinematic film still from a high-end crime drama, anamorphic lens flare, warm cinematic lighting, clean 35mm film grain, photorealistic human skin texture",
            "setting": "a dim industrial safehouse with harsh sunlight beams through blinds, bloodstained leather sofa, two dead bodies",
            "first_frame": item["first_frame"],
            "subjects": [
                {
                    "key": "emma",
                    "desc": item["subject_desc"],
                    "voice": item["voice_desc"]
                }
            ],
            "shots": [
                {
                    "camera": item["camera"],
                    "action": item["action"],
                    "dialogue": [
                        {
                            "subject": "emma",
                            "line": item["dialogue"],
                            "lang": "Chinese",
                            "after": "Maintains chilling calm expression."
                        }
                    ] if item["dialogue"] else []
                }
            ],
            "soundscape": "Tense cartel safehouse room tone.",
            "music": "N/A"
        }
        if "last_frame" in item:
            spec["last_frame"] = item["last_frame"]
        if Path(item["audio_file"]).exists():
            spec["audio"] = {
                "voice_ref": {
                    "subject": "emma",
                    "file": item["audio_file"]
                }
            }

        spec_file = DRAMA_DIR / f"spec_{sid}.json"
        spec_file.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")

        print(f"\n>>> 正在向 ComfyUI 提交分镜 {sid} 视频渲染任务...")
        t0 = time.time()
        shot_out_dir = DRAMA_DIR / f"render_{sid}"
        shot_out_dir.mkdir(parents=True, exist_ok=True)
        run_cmd([
            "python3", str(REPO_DIR / "tools" / "h3_shot.py"),
            str(spec_file),
            "--out", str(shot_out_dir),
            "--force"
        ], f"渲染分镜 {sid} 视频")

        # 扫描产物
        matches = sorted(shot_out_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not matches:
            alt_dir = REPO_DIR / "runtime" / "outputs" / "h3_shot"
            matches = sorted(alt_dir.glob(f"*{sid}*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)

        if not matches:
            print(f"❌ 未找到生成的 {sid} 视频！")
            sys.exit(1)

        shutil.copy2(matches[0], out_mp4)
        print(f"✔ 分镜 {sid} 视频成功归档至 {out_mp4.name} ({out_mp4.stat().st_size / 1024**2:.2f} MB, 耗时 {time.time()-t0:.1f}s)")

    print("[3/4] 4 镜伪长镜头视频全部渲染完成！\n")

def step_assembly():
    print("=== [4/4] 执行 Stage 4 自动剪辑、音效混流与成片导出 ===")
    run_cmd([
        "python3", str(DRAMA_DIR / "assemble_film.py")
    ], "Stage 4 剪辑总装")
    print("[4/4] 最终成片导出完毕！保存在 runtime/outputs/drama_zerozerozero_v1.mp4\n")

def main():
    print("==========================================================")
    print("🎬 LoPy 《零零零·单刀赴会》 Stage 3 - 视频渲染与总装启动")
    print("==========================================================")
    ensure_video_models()
    ensure_comfy()
    step_videos()
    step_assembly()
    Path("/content/VIDEO_ALL_DONE.txt").write_text("DONE\n")
    print("==========================================================")
    print("🎉 影视级成片已顺利生成！")
    print("==========================================================")

if __name__ == "__main__":
    main()
