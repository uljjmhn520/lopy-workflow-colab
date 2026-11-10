#!/usr/bin/env bash
set -e

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HERE"

export AI_ROOT="$HERE/models"
mkdir -p "$AI_ROOT"

echo "=== 1/2: 下载 / 校验 BreezyVoice-300M 模型权重 ==="
python3 setup/download.py setup/downloads_breezyvoice.json

echo "=== 2/2: 下载 / 校验 G2PW 注音字典模型 ==="
python3 setup/download.py setup/downloads_g2pw.json

if [ -f "$AI_ROOT/BreezyVoice/G2PWModel_1.1.zip" ] && [ ! -d "$AI_ROOT/BreezyVoice/G2PWModel" ]; then
    echo "解压 G2PWModel..."
    unzip -q -o "$AI_ROOT/BreezyVoice/G2PWModel_1.1.zip" -d "$AI_ROOT/BreezyVoice/"
fi

if [ -f "$AI_ROOT/BreezyVoice/G2PWModel/g2pW.onnx" ] && [ ! -f "$AI_ROOT/BreezyVoice/G2PWModel/g2pw.onnx" ]; then
    ln -sf g2pW.onnx "$AI_ROOT/BreezyVoice/G2PWModel/g2pw.onnx"
fi

echo "=== 所有语音基础模型准备完成！ ==="
