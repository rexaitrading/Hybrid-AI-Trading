[CmdletBinding()]
param(
  [ValidateSet("DEV_REPLAY","REAL")]
  [string]$Mode = "REAL"
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

Write-Host "[ARM-QQQ] Mode=$Mode" -ForegroundColor Cyan

powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Build-GateScoreDailySummary.ps1 -Symbol QQQ -Mode $Mode
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Build-BlockGStatusStub.ps1 -Symbol QQQ
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Check-BlockGReady.ps1 -Symbol QQQ
exit $LASTEXITCODE