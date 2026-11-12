# 确保本机 ComfyUI 在 127.0.0.1:8188 执行中；没有的话启动它。
# 音乐（YuE2）与影片（H3）都共用这个服务。
$ErrorActionPreference = 'Stop'
try {
  Invoke-RestMethod -Uri 'http://127.0.0.1:8188/system_stats' -TimeoutSec 4 | Out-Null
  Write-Output 'ComfyUI already running.'
  exit 0
} catch { }
$extra = @(); if ($env:COMFY_EXTRA_ARGS) { $extra = $env:COMFY_EXTRA_ARGS -split ' ' }   # 例如 --reserve-vram 1.5，由 configs\profile.cmd 设定
Start-Process -FilePath 'C:\AI\H3\venv\Scripts\python.exe' `
  -ArgumentList (@('-X','utf8','C:\AI\H3\ComfyUI-0.36.0\main.py','--listen','127.0.0.1','--port','8188','--disable-auto-launch','--preview-method','none','--cache-none','--fast','fp16_accumulation') + $extra) `
  -WorkingDirectory 'C:\AI\H3\ComfyUI-0.36.0'
for ($i = 0; $i -lt 60; $i++) {
  Start-Sleep -Seconds 2
  try { Invoke-RestMethod -Uri 'http://127.0.0.1:8188/system_stats' -TimeoutSec 4 | Out-Null; Write-Output "ComfyUI started after $(($i+1)*2)s."; exit 0 } catch { }
}
Write-Error 'ComfyUI did not come up within 120s.'
