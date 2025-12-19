[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path ".").Path

Write-Host "[GS] Build-GateScorePnlSummary" -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Build-GateScorePnlSummary.ps1")

Write-Host "[GS] Build-GateScoreDailySummary" -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Build-GateScoreDailySummary.ps1")

Write-Host "[GS] DONE" -ForegroundColor Green
