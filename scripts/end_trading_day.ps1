Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$root      = Split-Path -Parent $scriptDir
Set-Location $root

$logDir = Join-Path $root ".logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

$ts      = Get-Date -Format "yyyyMMdd_HHmmss"
$logPath = Join-Path $logDir ("end_of_day_{0}.log" -f $ts)

$lines = @()
$lines += "[HybridAITrading] END OF DAY SUMMARY"
$lines += "Timestamp: $(Get-Date -Format o)"
$lines += "NOTE: Extend this script to call Python to dump portfolio, PnL, drawdown, etc."

$content = ($lines -join [Environment]::NewLine) + [Environment]::NewLine
[System.IO.File]::WriteAllText($logPath, $content, (New-Object System.Text.UTF8Encoding($false)))

Write-Host "[HybridAITrading] END OF DAY log written: $logPath" -ForegroundColor Green
