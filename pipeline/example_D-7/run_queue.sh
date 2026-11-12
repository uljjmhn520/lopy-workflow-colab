#!/usr/bin/env bash
# GPU 排队（〈连假后第一天〉起的标准版；〈D-7〉当时是手动逐步跑）。每 60 秒看一次：GPU 使用率 < 20% 且 ComfyUI 伫列是空的，连续 3 次才算空闲；
# 空闲后请 ComfyUI 释放显存，再确认显存 < 12GB（别的程式没占著）才开工。
# 依序：配音候选（VoxCPM2＋edge 参考）→ Breeze 候选 → 挑音 →（等 frames_ok 档，首帧审过才有）→ H3 出片。
# 每步写 queue.log；任一步失败就停。
cd "$(dirname "$0")"
LOG=queue.log
say() { echo "$(date '+%m-%d %H:%M:%S') $*" | tee -a "$LOG"; }
VOICE=C:/AI/Voice/venv/Scripts/python.exe
BREEZE=C:/AI/BreezeTTS/venv/Scripts/python.exe
BZ=C:/AI/tools/breeze_batch.py
H3PY=C:/AI/H3/venv/Scripts/python.exe

comfy_busy() {
  curl -s --max-time 5 http://127.0.0.1:8188/queue | python -c "import sys,json;d=json.load(sys.stdin);print(len(d['queue_running'])+len(d['queue_pending']))" 2>/dev/null || echo 0
}

wait_gpu() {
  say "等待 GPU 空闲（$1）"
  while true; do
    local ok=0
    while [ $ok -lt 3 ]; do
      util=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits | tr -d ' ')
      if [ "$util" -lt 20 ] && [ "$(comfy_busy)" = "0" ]; then ok=$((ok+1)); else ok=0; fi
      sleep 60
    done
    curl -s -X POST http://127.0.0.1:8188/free -H "Content-Type: application/json" -d '{"unload_models":true,"free_memory":true}' >/dev/null 2>&1
    sleep 15
    mem=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | tr -d ' ')
    if [ "$mem" -lt 12000 ]; then say "GPU 空闲（显存 ${mem}MiB），开始：$1"; return; fi
    say "使用率低但显存仍被占 ${mem}MiB，继续等"
  done
}

step() { local name=$1; shift; say "▶ $name"; "$@" >> "$name.log" 2>&1 || { say "✗ $name 失败，见 $name.log"; exit 1; }; say "✓ $name"; }

if [ ! -f voice_state.json ]; then
  wait_gpu "配音"
  step voice1 "$VOICE" voice_stage1.py --n 6
  step breeze "$BREEZE" "$BZ" breeze_jobs.json
  step pick "$VOICE" voice_pick.py
fi
while [ ! -f frames_ok ]; do sleep 60; done
say "首帧已审过（frames_ok）"
wait_gpu "H3"
step gen1 "$H3PY" pipeline_gen.py
say "QUEUE_DONE"
