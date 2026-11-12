#!/usr/bin/env bash
set -e

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HERE"

CMD="${1:-help}"

case "$CMD" in
    start|up)
        echo "[docker_comfy] 正在后台启动 ComfyUI 服务容器 (端口 8188)..."
        docker compose up -d comfy
        echo "[docker_comfy] 等待 ComfyUI 启动响应..."
        for i in {1..30}; do
            if curl -s http://127.0.0.1:8188/system_stats >/dev/null 2>&1; then
                echo "[docker_comfy] ComfyUI 已在 http://127.0.0.1:8188 就绪！"
                exit 0
            fi
            sleep 2
        done
        echo "[docker_comfy] 警告：30 秒内未能探测到 8188 端口，请使用 '$0 logs' 查看容器输出。"
        ;;
    stop|down)
        echo "[docker_comfy] 停止 ComfyUI 服务容器..."
        docker compose stop comfy
        ;;
    restart)
        echo "[docker_comfy] 重启 ComfyUI 服务容器..."
        docker compose restart comfy
        ;;
    status)
        docker compose ps comfy
        ;;
    logs)
        docker compose logs -f comfy
        ;;
    gen)
        shift
        # 运行生图 CLI
        python3 tools/gen_image.py "$@"
        ;;
    help|*)
        echo "用法: $0 {start|stop|restart|status|logs|gen [args...]}"
        echo "示例:"
        echo "  $0 start              # 启动 ComfyUI 容器"
        echo "  $0 status             # 查看服务状态"
        echo "  $0 stop               # 停止容器以释放显存"
        ;;
esac
