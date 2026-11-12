# H3 分镜生成（官方 MiniMax 提示词格式；2026-09-28 起专案规定）。任何 agent 或人都可呼叫。
# 例：
#   C:\AI\tools\make_shot.cmd -Spec shot.json -Out D:\out\s01            # 组提示词 + 检查 + 生成
#   C:\AI\tools\make_shot.cmd -Spec shot.json -Out D:\out\s01 -DryRun    # 只组提示词 + 检查（不用 GPU）
#   C:\AI\tools\make_shot.cmd -Lint prompt.txt -Duration 4               # 检查手写提示词是否合官方格式
param(
  [string]$Spec,
  [string]$Out,
  [switch]$DryRun,
  [switch]$Force,
  [string]$Lint,
  [double]$Duration = 0
)
$ErrorActionPreference = 'Stop'
$py = 'C:\AI\H3\venv\Scripts\python.exe'
$tool = Join-Path $PSScriptRoot 'h3_shot.py'
$env:PYTHONIOENCODING = 'utf-8'
if ($Lint) {
  $a = @($tool, '--lint', (Resolve-Path $Lint).Path)
  if ($Duration -gt 0) { $a += @('--duration', $Duration) }
} else {
  $a = @($tool, (Resolve-Path $Spec).Path)
  if ($Out)    { $a += @('--out', $Out) }
  if ($DryRun) { $a += '--dry-run' }
  if ($Force)  { $a += '--force' }
}
& $py @a
exit $LASTEXITCODE
