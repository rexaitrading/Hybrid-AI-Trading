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

Write-Host "[ARM-SPY] Mode=$Mode" -ForegroundColor Cyan

powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Build-GateScoreDailySummary.ps1 -Symbol SPY -Mode $Mode
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Build-BlockGStatusStub.ps1 -Symbol SPY
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Check-BlockGReady.ps1 -Symbol SPY
exit $LASTEXITCODE