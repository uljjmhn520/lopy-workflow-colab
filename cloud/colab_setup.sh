#!/usr/bin/env bash
# ==============================================================================
# Google Colab Environment Setup Script for LoPy Pipeline
# Supports: L4 (24GB), A100 (40GB/80GB), T4 (16GB)
# ==============================================================================
set -euo pipefail

echo "=========================================================="
echo ">>> [1/5] 检查 GPU 与系统环境"
echo "=========================================================="
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader || {
    echo "[ERROR] 未检测到 NVIDIA GPU，请在 Colab 顶部菜单 [运行时] -> [更改运行时类型] 中选择 T4/L4/A100 GPU"
    exit 1
}

WORKSPACE_DIR="${WORKSPACE_DIR:-/content/lopy-workflow-colab}"
MODELS_DIR="${MODELS_DIR:-${WORKSPACE_DIR}/models}"
COMFY_DIR="/content/ComfyUI"

echo "工作空间目录: ${WORKSPACE_DIR}"
echo "模型存储目录: ${MODELS_DIR}"
echo "ComfyUI 目录: ${COMFY_DIR}"

mkdir -p "${WORKSPACE_DIR}/runtime/inputs" \
         "${WORKSPACE_DIR}/runtime/outputs" \
         "${WORKSPACE_DIR}/runtime/temp" \
         "${WORKSPACE_DIR}/runtime/shots" \
         "${WORKSPACE_DIR}/runtime/chars" \
         "${WORKSPACE_DIR}/runtime/first"

echo "=========================================================="
echo ">>> [2/5] 安装系统依赖 (ffmpeg, aria2, git-lfs)"
echo "=========================================================="
apt-get update -qq && apt-get install -y -qq ffmpeg aria2 git-lfs > /dev/null

echo "=========================================================="
echo ">>> [3/5] 部署 ComfyUI 及加速推理插件"
echo "=========================================================="
if [ ! -d "${COMFY_DIR}" ]; then
    echo "Cloning ComfyUI latest master..."
    git clone -q --depth 1 https://github.com/comfyanonymous/ComfyUI "${COMFY_DIR}"
fi

pip install -q uv
# 保留 Colab 原生 torch/torchvision/torchaudio，仅安装 ComfyUI 纯 Python 依赖
grep -viE '^(torch|torchvision|torchaudio)([=<> ]|$)' "${COMFY_DIR}/requirements.txt" > /tmp/req_comfy.txt
uv pip install --system -q -r /tmp/req_comfy.txt "comfy-kitchen>=0.2.41" "comfy-aimdo>=0.6.0" huggingface_hub

# 部署 Veda Sparse Attention 节点
if [ ! -d "${COMFY_DIR}/custom_nodes/Veda-on-ComfyUI" ]; then
    echo "安装 Veda-on-ComfyUI 节点..."
    git clone -q https://github.com/veda-sparse/Veda-on-ComfyUI "${COMFY_DIR}/custom_nodes/Veda-on-ComfyUI"
    git -C "${COMFY_DIR}/custom_nodes/Veda-on-ComfyUI" checkout -q 67e4eb5541b648555563144401ebaba832bd73ec
fi

echo "=========================================================="
echo ">>> [4/5] 配置模型路径映射 (extra_model_paths.yaml)"
echo "=========================================================="
cat <<EOF > "${COMFY_DIR}/extra_model_paths.yaml"
lopy_colab:
    base_path: ${MODELS_DIR}/H3/models
    checkpoints: diffusion_models
    diffusion_models: diffusion_models
    clip: text_encoders
    text_encoders: text_encoders
    vae: vae
    loras: loras
EOF

echo "=========================================================="
echo ">>> [5/5] Colab 环境就绪"
echo "=========================================================="
echo "✅ 环境安装完成！"
echo "启动 ComfyUI 命令提示:"
echo "python3 ${COMFY_DIR}/main.py --listen 127.0.0.1 --port 8188 --input-directory ${WORKSPACE_DIR}/runtime/inputs --output-directory ${WORKSPACE_DIR}/runtime/outputs --lowvram"
