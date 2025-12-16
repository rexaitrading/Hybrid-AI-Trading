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

Write-Host "[ARM-NVDA] Mode=$Mode" -ForegroundColor Cyan

# 1) GateScore daily summary (Mode governs REAL vs DEV_REPLAY)
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Build-GateScoreDailySummary.ps1 -Symbol NVDA -Mode $Mode
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# 2) Build Block-G contract
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Build-BlockGStatusStub.ps1 -Symbol NVDA
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# 3) Deterministic readiness check
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Check-BlockGReady.ps1 -Symbol NVDA
exit $LASTEXITCODE