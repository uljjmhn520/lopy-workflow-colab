#!/usr/bin/env bash
set -e

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HERE"

export AI_ROOT="$HERE/models"

echo "[download] 确保基础模型目录结构..."
mkdir -p "$AI_ROOT/H3/models/diffusion_models"
mkdir -p "$AI_ROOT/H3/models/text_encoders"
mkdir -p "$AI_ROOT/H3/models/vae"
mkdir -p "$AI_ROOT/H3/models/loras/dmad_raw"
mkdir -p "$AI_ROOT/H3/ComfyUI-0.36.0"
[ -L "$AI_ROOT/H3/ComfyUI-0.36.0/models" ] || ln -sfn "$AI_ROOT/H3/models" "$AI_ROOT/H3/ComfyUI-0.36.0/models"

download_with_retry() {
    local manifest="$1"
    local desc="$2"
    echo "[download] 开始同步: $desc ($manifest)..."
    until python3 setup/download.py "$manifest"; do
        echo "[download] $manifest 连接波动，3 秒后自动断点续传..."
        sleep 3
    done
    echo "[download] $desc 校验完成！"
}

download_with_retry "setup/downloads_qwen_image_edit.json" "阶段二 Qwen-Image-Edit 模型 (~30GB)"
download_with_retry "setup/downloads_dmad.json" "阶段三 DMAD 4步蒸馏 LoRA (~2.7GB)"
download_with_retry "setup/downloads.json" "阶段三 MiniMax H3 视频模型及组件 (~42GB)"

echo "[download] 全部模型权重校验下载完成！"
