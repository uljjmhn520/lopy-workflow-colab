#!/usr/bin/env bash
set -e

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HERE"

IMAGE_NAME="lopy-voice:latest"

# Ensure docker image is built
if ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
    echo "[docker_voice] 镜像 $IMAGE_NAME 未找到，正在首次构建..."
    docker compose build voice
fi

# Ensure BreezyVoice symlinks for container paths
mkdir -p "$HERE/models/BreezyVoice"
[ -L "$HERE/models/BreezyVoice/code" ] || ln -sfn /opt/BreezyVoice/code "$HERE/models/BreezyVoice/code"
[ -L "$HERE/models/BreezyVoice/winstub" ] || ln -sfn /opt/BreezyVoice/winstub "$HERE/models/BreezyVoice/winstub"

CMD="${1:-help}"

case "$CMD" in
    batch)
        shift
        if [ -z "$1" ]; then
            echo "用法: $0 batch <jobs.json>"
            exit 1
        fi
        docker compose run --rm voice python3 /workspace/tools/breezyvoice_batch.py "/workspace/$1"
        ;;
    pick)
        shift
        if [ -z "$1" ]; then
            echo "用法: $0 pick <jobs.json> [flags...]"
            exit 1
        fi
        JOB_FILE="$1"
        shift
        docker compose run --rm voice python3 /workspace/tools/breezyvoice_pick.py "/workspace/$JOB_FILE" "$@"
        ;;
    all|make)
        shift
        if [ -z "$1" ]; then
            echo "用法: $0 all <jobs.json>"
            exit 1
        fi
        echo "[docker_voice] 步骤 1/2: 批次生成候选音频..."
        docker compose run --rm voice python3 /workspace/tools/breezyvoice_batch.py "/workspace/$1"
        echo "[docker_voice] 步骤 2/2: ASR听写与自动挑音..."
        docker compose run --rm voice python3 /workspace/tools/breezyvoice_pick.py "/workspace/$1"
        echo "[docker_voice] 配音与挑音完成！"
        ;;
    run)
        shift
        docker compose run --rm voice "$@"
        ;;
    bash|shell)
        docker compose run --rm voice bash
        ;;
    build)
        docker compose build voice
        ;;
    *)
        echo "Lopy-Voice Docker CLI 辅助工具"
        echo "用法:"
        echo "  $0 all <jobs.json>      # 一键生成全部候选项并进行 ASR 挑音"
        echo "  $0 batch <jobs.json>    # 仅批次生成候选项"
        echo "  $0 pick <jobs.json>     # 仅执行 ASR 听写与腔调挑音"
        echo "  $0 run <command...>     # 在配音容器中执行任意命令"
        echo "  $0 bash                 # 进入容器交互终端"
        echo "  $0 build                # 重新构建配音镜像"
        ;;
esac
