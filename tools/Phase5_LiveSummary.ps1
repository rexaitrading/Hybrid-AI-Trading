param(
    [string]$Day = $(Get-Date -Format "yyyy-MM-dd")
)

$ErrorActionPreference = "Stop"

# Determine repo root: tools/ -> repo root
$toolsDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

Write-Host "[LIVE-SUMMARY] Phase-5 LIVE summary for $Day" -ForegroundColor Cyan

# Delegate to Phase5_DailyLiveReport.ps1 to produce the actual text summary
# This prints per-symbol PnL and overall stats for the given day.
.\tools\Phase5_DailyLiveReport.ps1 -Day $Day