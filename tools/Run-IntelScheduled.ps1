$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest
chcp 65001 | Out-Null

$repo = "C:\HATJ\HybridAITrading"
Set-Location -LiteralPath $repo

$logDir = Join-Path $repo "logs\scheduled"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$ts  = Get-Date -Format "yyyyMMdd_HHmmss"
$out = Join-Path $logDir ("intel_task_" + $ts + ".out.log")
$err = Join-Path $logDir ("intel_task_" + $ts + ".err.log")

try {
  & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repo "tools\Run-IntelPipeline-Minimal.ps1") 1>> $out 2>> $err
  exit $LASTEXITCODE
} catch {
  $_ | Out-String | Add-Content -LiteralPath $err -Encoding utf8
  exit 1
}


