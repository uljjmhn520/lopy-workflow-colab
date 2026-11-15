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
CHAIN_DIR = DRAMA_DIR / "chaining"
AUDIO_DIR = DRAMA_DIR / "audio"
VIDEO_DIR = DRAMA_DIR / "video"
OUTPUTS_DIR = REPO_DIR / "runtime" / "outputs"

for d in [CHAIN_DIR, AUDIO_DIR, VIDEO_DIR, OUTPUTS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

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
    print("=== [1/5] 检查与下载 H3 视频生成模型 (aria2c 极速并发) ===")
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
    print("[1/5] 视频模型准备完毕！\n")


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
        if not Path("/workspace").exists():
            try:
                os.symlink(str(REPO_DIR), "/workspace")
            except Exception:
                pass

        extra_cfg = COMFY_DIR / "extra_model_paths.yaml"
        if not extra_cfg.exists():
            extra_cfg = REPO_DIR / "setup" / "extra_model_paths_linux.yaml"

        print(f"正在后台启动 ComfyUI (模型配置: {extra_cfg})...")
        cmd = [
            "python3", "main.py",
            "--listen", "127.0.0.1",
            "--port", "8188",
            "--lowvram",
            "--extra-model-paths-config", str(extra_cfg),
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


def step_render_s02():
    print("=== [3/5] 渲染接力镜头 2 (S02 环绕推进，以 S01 最后一帧为首帧) ===")
    s01_last = CHAIN_DIR / "s01_last_frame.png"
    if not s01_last.exists():
        s01_video = VIDEO_DIR / "s01.mp4"
        run_cmd([
            "ffmpeg", "-y", "-loglevel", "error",
            "-sseof", "-0.1", "-i", str(s01_video),
            "-update", "1", "-q:v", "1", str(s01_last)
        ], "提取 S01 视频终点帧")

    out_s02 = VIDEO_DIR / "s02_chained.mp4"
    if out_s02.exists() and out_s02.stat().st_size > 1024 * 1024:
        print(f"[已存在跳过] {out_s02.name}")
        return out_s02

    spec_s02 = {
        "duration": 4.5,
        "size": [768, 1344],
        "seed": 3002,
        "steps": 14,
        "style": "a realistic cinematic film still from a high-end crime drama, anamorphic lens flare, warm cinematic lighting, clean 35mm film grain, photorealistic human skin texture",
        "setting": "a dim industrial safehouse with harsh sunlight beams through blinds, bloodstained leather sofa, two dead bodies",
        "first_frame": str(s01_last),
        "subjects": [
            {
                "key": "emma",
                "desc": "Emma Lynne, a blonde female boss in a charcoal wool trench coat and black leather gloves",
                "voice": "subtle ambient air and breathing tension"
            }
        ],
        "shots": [
            {
                "camera": "The camera smoothly orbits from behind Emma to her front 3/4 profile while dollying forward steadily toward the sofa.",
                "action": "Starting from <Picture 1>, Emma walks steadily forward, the camera orbiting smoothly to reveal her calm unblinking face and piercing blue eyes, as she approaches the dark red leather sofa with two dead bodies slumped on it, stopping directly in front of the sofa.",
                "dialogue": []
            }
        ],
        "soundscape": "Tense cartel safehouse room tone.",
        "music": "N/A"
    }

    spec_file = CHAIN_DIR / "spec_s02.json"
    spec_file.write_text(json.dumps(spec_s02, ensure_ascii=False, indent=2), encoding="utf-8")

    shot_out_dir = CHAIN_DIR / "render_s02"
    shot_out_dir.mkdir(parents=True, exist_ok=True)
    run_cmd([
        "python3", str(REPO_DIR / "tools" / "h3_shot.py"),
        str(spec_file),
        "--out", str(shot_out_dir),
        "--force"
    ], "渲染分镜 S02 接力视频")

    matches = sorted(shot_out_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not matches:
        alt_dir = REPO_DIR / "runtime" / "outputs" / "h3_shot"
        matches = sorted(alt_dir.glob("*s02*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not matches:
        print("❌ 未找到生成的 S02 视频！")
        sys.exit(1)

    shutil.copy2(matches[0], out_s02)
    print(f"✔ 分镜 S02 接力视频生成完毕: {out_s02.name} ({out_s02.stat().st_size / 1024**2:.2f} MB)")
    return out_s02


def step_render_s03(s02_video):
    print("=== [4/5] 渲染接力镜头 3 (S03 落座与台词，以 S02 最后一帧为首帧) ===")
    s02_last = CHAIN_DIR / "s02_last_frame.png"
    run_cmd([
        "ffmpeg", "-y", "-loglevel", "error",
        "-sseof", "-0.1", "-i", str(s02_video),
        "-update", "1", "-q:v", "1", str(s02_last)
    ], "提取 S02 视频终点帧")

    out_s03 = VIDEO_DIR / "s03_chained.mp4"
    if out_s03.exists() and out_s03.stat().st_size > 1024 * 1024:
        print(f"[已存在跳过] {out_s03.name}")
        return out_s03

    spec_s03 = {
        "duration": 4.8,
        "size": [768, 1344],
        "seed": 3003,
        "steps": 14,
        "style": "a realistic cinematic film still from a high-end crime drama, anamorphic lens flare, warm cinematic lighting, clean 35mm film grain, photorealistic human skin texture",
        "setting": "a dim industrial safehouse with harsh sunlight beams through blinds, bloodstained leather sofa, two dead bodies",
        "first_frame": str(s02_last),
        "subjects": [
            {
                "key": "emma",
                "desc": "Emma Lynne, a fearless blonde cartel boss sitting between two corpses",
                "voice": "a cold, deep, authoritative female voice speaking with icy conviction"
            }
        ],
        "audio": {
            "voice_ref": {
                "subject": "emma",
                "file": str(AUDIO_DIR / "s04.wav")
            }
        },
        "shots": [
            {
                "camera": "Low-angle close-to-medium camera holding steady at a 45-degree angle in front of the sofa.",
                "action": "Starting from <Picture 1>, Emma calmly and smoothly sits down on the center of the leather sofa directly between the two lifeless corpses, resting her black gloved hands on her lap with absolute cold composure, subtly lifting her chin while articulating her dialogue firmly.",
                "dialogue": [
                    {
                        "subject": "emma",
                        "line": "尸体处理完之前，我们先把货款结了。叫能做主的人出来。",
                        "lang": "Chinese",
                        "after": "Maintains chilling calm expression."
                    }
                ]
            }
        ],
        "soundscape": "Tense cartel safehouse room tone.",
        "music": "N/A"
    }

    spec_file = CHAIN_DIR / "spec_s03.json"
    spec_file.write_text(json.dumps(spec_s03, ensure_ascii=False, indent=2), encoding="utf-8")

    shot_out_dir = CHAIN_DIR / "render_s03"
    shot_out_dir.mkdir(parents=True, exist_ok=True)
    run_cmd([
        "python3", str(REPO_DIR / "tools" / "h3_shot.py"),
        str(spec_file),
        "--out", str(shot_out_dir),
        "--force"
    ], "渲染分镜 S03 接力视频")

    matches = sorted(shot_out_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not matches:
        alt_dir = REPO_DIR / "runtime" / "outputs" / "h3_shot"
        matches = sorted(alt_dir.glob("*s03*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not matches:
        print("❌ 未找到生成的 S03 视频！")
        sys.exit(1)

    shutil.copy2(matches[0], out_s03)
    print(f"✔ 分镜 S03 接力视频生成完毕: {out_s03.name} ({out_s03.stat().st_size / 1024**2:.2f} MB)")
    return out_s03


def step_assemble():
    print("=== [5/5] 执行 3 段纯物理连贯长镜头拼接与压制 ===")
    s01_v = VIDEO_DIR / "s01.mp4"
    s02_v = VIDEO_DIR / "s02_chained.mp4"
    s03_v = VIDEO_DIR / "s03_chained.mp4"

    concat_txt = CHAIN_DIR / "concat_list.txt"
    with open(concat_txt, "w") as f:
        f.write(f"file '{s01_v.resolve()}'\n")
        f.write(f"file '{s02_v.resolve()}'\n")
        f.write(f"file '{s03_v.resolve()}'\n")

    raw_merged = CHAIN_DIR / "raw_merged.mp4"
    res = subprocess.run([
        "ffmpeg", "-y", "-loglevel", "warning",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_txt),
        "-c", "copy",
        str(raw_merged)
    ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    if res.returncode != 0 or not raw_merged.exists() or raw_merged.stat().st_size < 1024:
        print(f"注意: Stream copy 拼接提示: {res.stdout.strip()}，平滑切换 filter_complex 统一规范拼接...")
        run_cmd([
            "ffmpeg", "-y", "-loglevel", "warning",
            "-i", str(s01_v),
            "-i", str(s02_v),
            "-i", str(s03_v),
            "-filter_complex", "[0:v][0:a][1:v][1:a][2:v][2:a]concat=n=3:v=1:a=1[v][a]",
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-crf", "18", "-preset", "fast",
            "-c:a", "aac", "-b:a", "192k",
            str(raw_merged)
        ], "无缝串联 3 段视频 (统一重采样)")
    else:
        print("✔ 无缝串联 3 段视频 (Stream Copy)")

    # 生成字幕
    ass_path = CHAIN_DIR / "subtitles.ass"
    ass_content = """[Script Info]
ScriptType: v4.00+
PlayResX: 768
PlayResY: 1344
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Noto Sans CJK SC,42,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3.5,1.5,2,30,30,130,1
Style: Punchline,Noto Sans CJK SC,46,&H0000E5FF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4.0,2.0,2,30,30,130,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:09.50,0:00:13.80,Punchline,,0,0,0,,尸体处理完之前，我们先把货款结了。叫能做主的人出来。
"""
    ass_path.write_text(ass_content, encoding="utf-8")

    final_film = OUTPUTS_DIR / "drama_zerozerozero_chained_v2.mp4"
    run_cmd([
        "ffmpeg", "-y", "-loglevel", "warning",
        "-i", str(raw_merged),
        "-vf", f"subtitles={ass_path.resolve()}",
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        "-c:a", "aac", "-b:a", "192k",
        str(final_film)
    ], "压制最终接力长镜头成片")
    print(f"🎉 最终接力长镜头成片已导出: {final_film}")


def main():
    print("==========================================================")
    print("🎬 LoPy 《零零零·单刀赴会》 尾帧接力一镜到底流水线启动")
    print("==========================================================")
    ensure_video_models()
    ensure_comfy()
    s02_v = step_render_s02()
    s03_v = step_render_s03(s02_v)
    step_assemble()
    Path("/content/CHAINING_DONE.txt").write_text("DONE\n")
    print("==========================================================")
    print("🎉 3 段纯物理接力长镜头已 100% 连贯出片！")
    print("==========================================================")


if __name__ == "__main__":
    main()
