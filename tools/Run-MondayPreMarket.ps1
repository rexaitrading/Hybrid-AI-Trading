[CmdletBinding()]
param(
  [ValidateSet("REAL","DEV_REPLAY")]
  [string]$GateScoreMode = "REAL"
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

Write-Host "[MONDAY-PREMKT] start ts_utc=$([DateTime]::UtcNow.ToString('o')) mode=$GateScoreMode" -ForegroundColor Cyan

# 1) NVDA arming (single authority)
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Run-NvdaLiveArming.ps1 -Mode $GateScoreMode
if ($LASTEXITCODE -ne 0) {
  Write-Host "[MONDAY-PREMKT] NVDA NOT READY (fail-closed). exit=$LASTEXITCODE" -ForegroundColor Yellow
  exit $LASTEXITCODE
}

Write-Host "[MONDAY-PREMKT] NVDA READY ✅" -ForegroundColor Green
exit 0