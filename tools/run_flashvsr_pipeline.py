#!/usr/bin/env python3
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO_DIR = Path("/content/lopy-workflow-colab")
COMFY_DIR = Path("/content/ComfyUI")
V3_DIR = REPO_DIR / "pipeline" / "drama_zerozerozero_v3"
V3_VIDEO_DIR = V3_DIR / "video"
V3_2K_DIR = V3_DIR / "video_2k"
OUTPUTS_DIR = REPO_DIR / "runtime" / "outputs"
FLASHVSR_MODELS_DIR = COMFY_DIR / "models" / "FlashVSR-v1.1"

V3_2K_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
FLASHVSR_MODELS_DIR.mkdir(parents=True, exist_ok=True)

FLASHVSR_DOWNLOADS = [
    ("LQ_proj_in.ckpt", "https://huggingface.co/JunhaoZhuang/FlashVSR-v1.1/resolve/27561b186ded3402d7c975f4fd722e2885b6135f/LQ_proj_in.ckpt"),
    ("TCDecoder.ckpt", "https://huggingface.co/JunhaoZhuang/FlashVSR-v1.1/resolve/27561b186ded3402d7c975f4fd722e2885b6135f/TCDecoder.ckpt"),
    ("Wan2.1_VAE.pth", "https://huggingface.co/JunhaoZhuang/FlashVSR-v1.1/resolve/27561b186ded3402d7c975f4fd722e2885b6135f/Wan2.1_VAE.pth"),
    ("diffusion_pytorch_model_streaming_dmd.safetensors", "https://huggingface.co/JunhaoZhuang/FlashVSR-v1.1/resolve/27561b186ded3402d7c975f4fd722e2885b6135f/diffusion_pytorch_model_streaming_dmd.safetensors")
]


def ensure_flashvsr_node():
    node_dir = COMFY_DIR / "custom_nodes" / "ComfyUI-FlashVSR_Ultra_Fast"
    if not node_dir.exists():
        print("正在拉取 ComfyUI-FlashVSR_Ultra_Fast 扩展节点...")
        subprocess.run(["git", "clone", "--depth", "1", "https://github.com/lihaoyun6/ComfyUI-FlashVSR_Ultra_Fast", str(node_dir)], check=True)
    subprocess.run(["uv", "pip", "install", "--system", "-q", "einops", "rotary-embedding-torch", "diffusers"], check=True)


def ensure_flashvsr_models():
    print("=== [FlashVSR] 检查与下载 FlashVSR-v1.1 超分模型 ===")
    for name, url in FLASHVSR_DOWNLOADS:
        dest = FLASHVSR_MODELS_DIR / name
        if dest.exists() and dest.stat().st_size > 1024 * 1024:
            print(f"[已存在跳过] {name} ({dest.stat().st_size / 1024**2:.1f} MB)")
            continue
        print(f"[下载超分模型] {name} ...")
        t0 = time.time()
        cmd = ["aria2c", "-c", "-x", "16", "-s", "16", "--console-log-level=warn", url, "-d", str(FLASHVSR_MODELS_DIR), "-o", name]
        subprocess.run(cmd, check=True)
        print(f"✔ 完成: {name} (耗时 {time.time()-t0:.1f}s)")


def upscale_shot(src_video, out_video):
    import numpy as np
    import torch

    sys.path.insert(0, str(COMFY_DIR))
    NODE_PATH = COMFY_DIR / "custom_nodes" / "ComfyUI-FlashVSR_Ultra_Fast"
    spec = importlib.util.spec_from_file_location("flashvsr_node", NODE_PATH / "__init__.py", submodule_search_locations=[str(NODE_PATH)])
    mod = importlib.util.module_from_spec(spec)
    sys.modules["flashvsr_node"] = mod
    spec.loader.exec_module(mod)
    Node = mod.NODE_CLASS_MAPPINGS["FlashVSRNode"]

    w, h = map(int, subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(src_video)],
                                   capture_output=True, text=True).stdout.strip().split(","))

    print(f">>> 正在读取 {src_video.name} (原始尺寸: {w}x{h})...")
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(src_video), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    frames = torch.from_numpy(np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3).astype(np.float32) / 255.0)

    t0 = time.time()
    print(f">>> 正在执行 FlashVSR 2X 超分时空推理 (共 {len(frames)} 帧)...")
    out = Node().main(model="FlashVSR-v1.1", frames=frames, mode="tiny", scale=2, tiled_vae=True, tiled_dit=True, unload_dit=False, seed=0)[0]
    wall = time.time() - t0

    o = (out.clamp(0, 1).cpu().numpy() * 255).round().astype(np.uint8)
    n, oh, ow, _ = o.shape
    print(f"✔ 超分完成: {n} 帧 -> {ow}x{oh} (耗时 {wall:.1f}s, 平均 {(wall/n):.2f}s/帧)")

    # 提取原音频并 mux
    tmp_v = out_video.parent / f"tmp_{out_video.name}"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{ow}x{oh}", "-r", "24", "-i", "-",
                    "-c:v", "libx264", "-crf", "14", "-preset", "fast", "-pix_fmt", "yuv420p", str(tmp_v)], input=o.tobytes(), check=True)

    # 合并原视频音频
    has_audio = bool(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(src_video)],
                                    capture_output=True, text=True).stdout.strip())
    if has_audio:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp_v), "-i", str(src_video),
                        "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", str(out_video)], check=True)
    else:
        shutil.move(str(tmp_v), str(out_video))
    if tmp_v.exists():
        tmp_v.unlink()
    return out_video


def run_flashvsr_v3():
    print("==========================================================")
    print("🎬 方向一：FlashVSR 2K 工业级视频超分任务启动")
    print("==========================================================")
    ensure_flashvsr_node()
    ensure_flashvsr_models()

    shot_ids = ["s01", "s02", "s03", "s04"]
    upscaled_clips = []
    for sid in shot_ids:
        src = V3_VIDEO_DIR / f"{sid}.mp4"
        out_2k = V3_2K_DIR / f"{sid}_2k.mp4"
        if out_2k.exists() and out_2k.stat().st_size > 1024 * 1024:
            print(f"[已存在跳过] {out_2k.name}")
        else:
            upscale_shot(src, out_2k)
        upscaled_clips.append(out_2k)

    # 4 镜 2K 拼接
    concat_txt = V3_2K_DIR / "concat_2k.txt"
    with open(concat_txt, "w") as f:
        for c in upscaled_clips:
            f.write(f"file '{c.resolve()}'\n")

    raw_2k_merged = V3_2K_DIR / "raw_2k_merged.mp4"
    res = subprocess.run([
        "ffmpeg", "-y", "-loglevel", "warning",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_txt),
        "-c", "copy",
        str(raw_2k_merged)
    ], capture_output=True, text=True)

    if res.returncode != 0 or not raw_2k_merged.exists() or raw_2k_merged.stat().st_size < 1024:
        print("Stream copy 切换为 filter_complex 2K 拼接...")
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "warning",
            "-i", str(upscaled_clips[0]), "-i", str(upscaled_clips[1]),
            "-i", str(upscaled_clips[2]), "-i", str(upscaled_clips[3]),
            "-filter_complex", "[0:v][0:a][1:v][1:a][2:v][2:a][3:v][3:a]concat=n=4:v=1:a=1[v][a]",
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-crf", "14", "-preset", "fast",
            "-c:a", "aac", "-b:a", "192k",
            str(raw_2k_merged)
        ], check=True)

    # 压制原生 2K ASS 双色矢量字幕 (1536x2688 坐标空间)
    ass_path = V3_2K_DIR / "subtitles_2k.ass"
    ass_content = """[Script Info]
ScriptType: v4.00+
PlayResX: 1536
PlayResY: 2688
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Noto Sans CJK SC,84,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,7.0,3.0,2,60,60,260,1
Style: Punchline,Noto Sans CJK SC,92,&H0000E5FF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,8.0,4.0,2,60,60,260,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:13.60,0:00:17.80,Punchline,,0,0,0,,尸体处理完之前，我们先把货款结了。叫能做主的人出来。
"""
    ass_path.write_text(ass_content, encoding="utf-8")

    final_2k = OUTPUTS_DIR / "drama_zerozerozero_v3.fv.mp4"
    print(f">>> 正在压制原生 2K 最终成片: {final_2k.name}...")
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "warning",
        "-i", str(raw_2k_merged),
        "-vf", f"subtitles={ass_path.resolve()}",
        "-c:v", "libx264", "-crf", "14", "-preset", "fast",
        "-c:a", "aac", "-b:a", "192k",
        str(final_2k)
    ], check=True)
    print(f"🎉 方向一 FlashVSR 2K 交付成片已导出: {final_2k} ({final_2k.stat().st_size / 1024**2:.2f} MB)")


if __name__ == "__main__":
    run_flashvsr_v3()
