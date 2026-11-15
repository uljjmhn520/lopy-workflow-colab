#!/usr/bin/env python3
import importlib.util
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
DRAMA_DIR = REPO_DIR / "pipeline" / "drama_zerozerozero_v5"
CHAIN_DIR = DRAMA_DIR / "chaining"
AUDIO_DIR = DRAMA_DIR / "audio"
FRAMES_DIR = DRAMA_DIR / "frames"
VIDEO_DIR = DRAMA_DIR / "video"
VIDEO_2K_DIR = DRAMA_DIR / "video_2k"
OUTPUTS_DIR = REPO_DIR / "runtime" / "outputs"
FLASHVSR_MODELS_DIR = COMFY_DIR / "models" / "FlashVSR-v1.1"

for d in [CHAIN_DIR, AUDIO_DIR, FRAMES_DIR, VIDEO_DIR, VIDEO_2K_DIR, OUTPUTS_DIR, FLASHVSR_MODELS_DIR]:
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

FLASHVSR_DOWNLOADS = [
    ("LQ_proj_in.ckpt", "https://huggingface.co/JunhaoZhuang/FlashVSR-v1.1/resolve/27561b186ded3402d7c975f4fd722e2885b6135f/LQ_proj_in.ckpt"),
    ("TCDecoder.ckpt", "https://huggingface.co/JunhaoZhuang/FlashVSR-v1.1/resolve/27561b186ded3402d7c975f4fd722e2885b6135f/TCDecoder.ckpt"),
    ("Wan2.1_VAE.pth", "https://huggingface.co/JunhaoZhuang/FlashVSR-v1.1/resolve/27561b186ded3402d7c975f4fd722e2885b6135f/Wan2.1_VAE.pth"),
    ("diffusion_pytorch_model_streaming_dmd.safetensors", "https://huggingface.co/JunhaoZhuang/FlashVSR-v1.1/resolve/27561b186ded3402d7c975f4fd722e2885b6135f/diffusion_pytorch_model_streaming_dmd.safetensors")
]


def ensure_models():
    print("=== [1/6] 检查与下载模型资源 (H3 + FlashVSR) ===")
    subprocess.run(["apt-get", "install", "-y", "-qq", "aria2"], check=True)
    # H3 视频生成模型
    for rel_path, url in MODELS_TO_DOWNLOAD:
        target = H3_MODELS / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.stat().st_size > 1024 * 1024:
            print(f"[已存在跳过] {target.name}")
            continue
        print(f"[极速并发下载] {target.name} ...")
        cmd = ["aria2c", "-c", "-x", "16", "-s", "16", "--console-log-level=warn", url, "-d", str(target.parent), "-o", target.name]
        subprocess.run(cmd, check=True)

    # FlashVSR 超分模型
    for name, url in FLASHVSR_DOWNLOADS:
        dest = FLASHVSR_MODELS_DIR / name
        if dest.exists() and dest.stat().st_size > 1024 * 1024:
            print(f"[已存在跳过] {name}")
            continue
        print(f"[极速下载超分] {name} ...")
        cmd = ["aria2c", "-c", "-x", "16", "-s", "16", "--console-log-level=warn", url, "-d", str(FLASHVSR_MODELS_DIR), "-o", name]
        subprocess.run(cmd, check=True)

    # 扩展节点与依赖
    node_dir = COMFY_DIR / "custom_nodes" / "ComfyUI-FlashVSR_Ultra_Fast"
    if not node_dir.exists():
        subprocess.run(["git", "clone", "--depth", "1", "https://github.com/lihaoyun6/ComfyUI-FlashVSR_Ultra_Fast", str(node_dir)], check=True)
    subprocess.run(["uv", "pip", "install", "--system", "-q", "einops", "rotary-embedding-torch", "diffusers"], check=True)
    print("✔ 所有模型与推理环境就绪！\n")


def ensure_comfy():
    print("=== [2/6] 检查与启动 ComfyUI 推理服务 ===")
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
    print("[2/6] 推理服务就绪！\n")


def run_cmd(cmd, desc):
    print(f">>> {desc}...")
    t0 = time.time()
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if p.returncode != 0:
        print(f"❌ 失败: {desc}\n{p.stdout}")
        sys.exit(1)
    print(f"✔ 完成: {desc} (耗时 {time.time()-t0:.1f}s)")
    return p.stdout


def step_render_s05():
    print("=== [3/6] 渲染分镜 S05 (H3-ADV-05: 过肩拔枪上膛持枪战术对峙) ===")
    s04_last = CHAIN_DIR / "s04_last_frame.png"
    if not s04_last.exists():
        s04_video = VIDEO_DIR / "s04.mp4"
        run_cmd([
            "ffmpeg", "-y", "-loglevel", "error",
            "-sseof", "-0.1", "-i", str(s04_video),
            "-update", "1", "-q:v", "1", str(s04_last)
        ], "提取 S04 终点帧")

    out_s05 = VIDEO_DIR / "s05.mp4"
    if out_s05.exists() and out_s05.stat().st_size > 1024 * 1024:
        print(f"[已存在跳过] {out_s05.name}")
        return out_s05

    spec_s05 = {
        "duration": 4.8,
        "size": [768, 1344],
        "seed": 5005,
        "steps": 14,
        "style": "a realistic cinematic film still from a high-end crime drama, anamorphic lens flare, warm cinematic lighting, clean 35mm film grain, photorealistic human skin texture",
        "setting": "a dim industrial safehouse with harsh sunlight beams through blinds, bloodstained leather sofa, two dead bodies",
        "first_frame": str(s04_last),
        "subjects": [
            {
                "key": "guard",
                "desc": "a cartel guard in black tactical gear and black gloves drawing a black semi-automatic pistol",
                "voice": "subtle mechanical cocking sound"
            },
            {
                "key": "emma",
                "desc": "Emma Lynne, a blonde female boss in a charcoal wool trench coat sitting between two corpses",
                "voice": "calm steady breathing"
            }
        ],
        "audio": {
            "voice_ref": {
                "subject": "guard",
                "file": str(AUDIO_DIR / "s05.wav")
            }
        },
        "shots": [
            {
                "camera": "Over-the-shoulder close-up holding steady from behind the right foreground.",
                "action": "Starting from <Picture 1>, a cartel guard abruptly thrusts his hand forward from the right foreground, gripping a black semi-automatic pistol and racking the slide with a crisp metallic cocking sound, aiming the gun barrel firmly at Emma's forehead. In the background between the two lifeless corpses, Emma sits perfectly composed and completely unflinching, her blue eyes staring cold and unwavering.",
                "dialogue": []
            }
        ],
        "soundscape": "Tense cartel safehouse room tone with sharp gun racking sound.",
        "music": "N/A"
    }

    spec_file = CHAIN_DIR / "spec_s05.json"
    spec_file.write_text(json.dumps(spec_s05, ensure_ascii=False, indent=2), encoding="utf-8")

    shot_out_dir = CHAIN_DIR / "render_s05"
    shot_out_dir.mkdir(parents=True, exist_ok=True)
    run_cmd([
        "python3", str(REPO_DIR / "tools" / "h3_shot.py"),
        str(spec_file),
        "--out", str(shot_out_dir),
        "--force"
    ], "渲染分镜 S05 拔枪对峙视频 (14步满血)")

    matches = sorted(shot_out_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not matches:
        alt_dir = REPO_DIR / "runtime" / "outputs" / "h3_shot"
        matches = sorted(alt_dir.glob("*s05*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not matches:
        print("❌ 未找到生成的 S05 视频！")
        sys.exit(1)

    shutil.copy2(matches[0], out_s05)
    print(f"✔ 分镜 S05 (拔枪战术对峙) 生成完毕: {out_s05.name} ({out_s05.stat().st_size / 1024**2:.2f} MB)")
    return out_s05


def step_render_s06(s05_video):
    print("=== [4/6] 渲染高潮分镜 S06 (H3-ADV-04: 双角色同框交替对白与唇形同步) ===")
    s05_last = CHAIN_DIR / "s05_last_frame.png"
    run_cmd([
        "ffmpeg", "-y", "-loglevel", "error",
        "-sseof", "-0.1", "-i", str(s05_video),
        "-update", "1", "-q:v", "1", str(s05_last)
    ], "提取 S05 终点帧")

    out_s06 = VIDEO_DIR / "s06.mp4"
    if out_s06.exists() and out_s06.stat().st_size > 1024 * 1024:
        print(f"[已存在跳过] {out_s06.name}")
        return out_s06

    spec_s06 = {
        "duration": 5.5,
        "size": [768, 1344],
        "seed": 5006,
        "steps": 14,
        "style": "a realistic cinematic film still from a high-end crime drama, anamorphic lens flare, warm cinematic lighting, clean 35mm film grain, photorealistic human skin texture",
        "setting": "a dim industrial safehouse with harsh sunlight beams through blinds, bloodstained leather sofa, two dead bodies",
        "first_frame": str(s05_last),
        "subjects": [
            {
                "key": "boss",
                "desc": "a rugged middle-aged cartel boss with weathered features and dark leather coat",
                "voice": "a deep, gritty, authoritative male voice"
            },
            {
                "key": "emma",
                "desc": "Emma Lynne, a fearless blonde female cartel boss sitting between two dead bodies",
                "voice": "a cold, deep, authoritative female voice speaking with icy conviction"
            }
        ],
        "audio": {
            "voice_refs": [
                {
                    "subject": "boss",
                    "file": str(AUDIO_DIR / "boss.wav")
                },
                {
                    "subject": "emma",
                    "file": str(AUDIO_DIR / "emma_reply.wav")
                }
            ]
        },
        "shots": [
            {
                "camera": "45-degree angle medium shot holding steady in front of the sofa.",
                "action": "Starting from <Picture 1>, the cartel boss steps firmly out from the shadows into the warm window light, holding up one hand to signal his guards to lower their weapons, speaking to Emma with a chilling authoritative voice. Emma remains seated motionless between the two dead bodies, subtly lifting her chin as she delivers her cold sharp retort, staring directly into the boss's eyes.",
                "dialogue": [
                    {
                        "subject": "boss",
                        "line": "Lynne 小姐，钱一分不少，但你的胆子比我想象的还要大。",
                        "lang": "Chinese",
                        "after": "Lowers hand slightly with confident smirk."
                    },
                    {
                        "subject": "emma",
                        "line": "做生意的胆子，取决于货物的纯度。签字吧。",
                        "lang": "Chinese",
                        "after": "Stares cold and unwavering."
                    }
                ]
            }
        ],
        "soundscape": "Tense cartel safehouse room tone.",
        "music": "N/A"
    }

    spec_file = CHAIN_DIR / "spec_s06.json"
    spec_file.write_text(json.dumps(spec_s06, ensure_ascii=False, indent=2), encoding="utf-8")

    shot_out_dir = CHAIN_DIR / "render_s06"
    shot_out_dir.mkdir(parents=True, exist_ok=True)
    run_cmd([
        "python3", str(REPO_DIR / "tools" / "h3_shot.py"),
        str(spec_file),
        "--out", str(shot_out_dir),
        "--force"
    ], "渲染分镜 S06 双角色交替谈判视频 (14步满血)")

    matches = sorted(shot_out_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not matches:
        alt_dir = REPO_DIR / "runtime" / "outputs" / "h3_shot"
        matches = sorted(alt_dir.glob("*s06*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not matches:
        print("❌ 未找到生成的 S06 视频！")
        sys.exit(1)

    shutil.copy2(matches[0], out_s06)
    print(f"✔ 分镜 S06 (双角色交替对白) 生成完毕: {out_s06.name} ({out_s06.stat().st_size / 1024**2:.2f} MB)")
    return out_s06


def step_assemble_and_flashvsr():
    print("=== [5/6] 执行 6 镜全流程无缝总装与 FlashVSR 2X 升阶 ===")
    import numpy as np
    import torch

    sys.path.insert(0, str(COMFY_DIR))
    NODE_PATH = COMFY_DIR / "custom_nodes" / "ComfyUI-FlashVSR_Ultra_Fast"
    spec = importlib.util.spec_from_file_location("flashvsr_node", NODE_PATH / "__init__.py", submodule_search_locations=[str(NODE_PATH)])
    mod = importlib.util.module_from_spec(spec)
    sys.modules["flashvsr_node"] = mod
    spec.loader.exec_module(mod)
    Node = mod.NODE_CLASS_MAPPINGS["FlashVSRNode"]

    shot_ids = ["s01", "s02", "s03", "s04", "s05", "s06"]
    upscaled_2k_clips = []
    for sid in shot_ids:
        src = VIDEO_DIR / f"{sid}.mp4"
        out_2k = VIDEO_2K_DIR / f"{sid}_2k.mp4"
        if out_2k.exists() and out_2k.stat().st_size > 1024 * 1024:
            print(f"[已存在跳过 2K] {out_2k.name}")
        else:
            w, h = map(int, subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(src)],
                                           capture_output=True, text=True).stdout.strip().split(","))
            raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(src), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
            frames = torch.from_numpy(np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3).astype(np.float32) / 255.0)

            t0 = time.time()
            print(f">>> 正在对 {src.name} 进行 FlashVSR 2X 超分 ({len(frames)} 帧)...")
            out = Node().main(model="FlashVSR-v1.1", frames=frames, mode="tiny", scale=2, tiled_vae=True, tiled_dit=True, unload_dit=False, seed=0)[0]
            wall = time.time() - t0

            o = (out.clamp(0, 1).cpu().numpy() * 255).round().astype(np.uint8)
            n, oh, ow, _ = o.shape
            print(f"✔ {src.name} 超分完成 -> {ow}x{oh} (耗时 {wall:.1f}s)")

            tmp_v = out_2k.parent / f"tmp_{out_2k.name}"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{ow}x{oh}", "-r", "24", "-i", "-",
                            "-c:v", "libx264", "-crf", "14", "-preset", "fast", "-pix_fmt", "yuv420p", str(tmp_v)], input=o.tobytes(), check=True)

            has_audio = bool(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(src)],
                                            capture_output=True, text=True).stdout.strip())
            if has_audio:
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp_v), "-i", str(src),
                                "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", str(out_2k)], check=True)
            else:
                shutil.move(str(tmp_v), str(out_2k))
            if tmp_v.exists():
                tmp_v.unlink()

        upscaled_2k_clips.append(out_2k)

    # 6 镜拼接
    concat_txt = VIDEO_2K_DIR / "concat_2k.txt"
    with open(concat_txt, "w") as f:
        for c in upscaled_2k_clips:
            f.write(f"file '{c.resolve()}'\n")

    raw_2k_merged = VIDEO_2K_DIR / "raw_2k_merged.mp4"
    res = subprocess.run([
        "ffmpeg", "-y", "-loglevel", "warning",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_txt),
        "-c", "copy",
        str(raw_2k_merged)
    ], capture_output=True, text=True)

    if res.returncode != 0 or not raw_2k_merged.exists() or raw_2k_merged.stat().st_size < 1024:
        print("切换为 filter_complex 6 镜 2K 拼接...")
        inputs = []
        for c in upscaled_2k_clips:
            inputs.extend(["-i", str(c)])
        filter_str = "".join([f"[{i}:v][{i}:a]" for i in range(len(upscaled_2k_clips))]) + f"concat=n={len(upscaled_2k_clips)}:v=1:a=1[v][a]"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "warning"] + inputs + [
            "-filter_complex", filter_str, "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-crf", "14", "-preset", "fast",
            "-c:a", "aac", "-b:a", "192k", str(raw_2k_merged)
        ], check=True)

    # 压制原生 2K ASS 双色矢量字幕 (3 句台词时间对齐)
    ass_path = VIDEO_2K_DIR / "subtitles_v5_2k.ass"
    ass_content = """[Script Info]
ScriptType: v4.00+
PlayResX: 1536
PlayResY: 2688
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Noto Sans CJK SC,84,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,7.0,3.0,2,60,60,260,1
Style: Punchline,Noto Sans CJK SC,92,&H0000E5FF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,8.0,4.0,2,60,60,260,1
Style: BossLine,Noto Sans CJK SC,92,&H0033CCFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,8.0,4.0,2,60,60,260,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:13.60,0:00:17.80,Punchline,,0,0,0,,尸体处理完之前，我们先把货款结了。叫能做主的人出来。
Dialogue: 0,0:00:20.50,0:00:25.20,BossLine,,0,0,0,,Lynne 小姐，钱一分不少，但你的胆子比我想象的还要大。
Dialogue: 0,0:00:25.40,0:00:29.80,Punchline,,0,0,0,,做生意的胆子，取决于货物的纯度。签字吧。
"""
    ass_path.write_text(ass_content, encoding="utf-8")

    final_film = OUTPUTS_DIR / "drama_zerozerozero_v5.mp4"
    print(f">>> 正在压制 6 镜 2K 最终微电影成片: {final_film.name}...")
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "warning",
        "-i", str(raw_2k_merged),
        "-vf", f"subtitles={ass_path.resolve()}",
        "-c:v", "libx264", "-crf", "14", "-preset", "fast",
        "-c:a", "aac", "-b:a", "192k",
        str(final_film)
    ], check=True)
    print(f"🎉 最终 6 镜 2K 院线级成片已导出: {final_film} ({final_film.stat().st_size / 1024**2:.2f} MB)")


def main():
    print("==========================================================")
    print("🎬 LoPy 《零零零·单刀赴会》 V5 (双人交替对嘴 + 拔枪对峙 + 2K) 启动")
    print("==========================================================")
    ensure_models()
    ensure_comfy()
    s05_v = step_render_s05()
    s06_v = step_render_s06(s05_v)
    step_assemble_and_flashvsr()
    Path("/content/V5_DONE.txt").write_text("ALL_DONE\n")
    print("==========================================================")
    print("🎉 V5 6 镜完整微电影已 100% 圆满出片！")
    print("==========================================================")


if __name__ == "__main__":
    main()
