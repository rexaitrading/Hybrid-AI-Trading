[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
$logsDir  = Join-Path $repoRoot "logs"

if (-not (Test-Path $logsDir)) {
    Write-Host "[GS-EXPORT] ERROR: logs directory not found at $logsDir" -ForegroundColor Red
    exit 1
}

$srcPath = Join-Path $logsDir "gatescore_daily_summary.csv"
$outPath = Join-Path $logsDir "nvda_gatescore_for_notion.csv"

if (-not (Test-Path $srcPath)) {
    Write-Host "[GS-EXPORT] WARN: gatescore_daily_summary.csv not found at $srcPath" -ForegroundColor Yellow
    exit 0
}

Write-Host "[GS-EXPORT] Loading GateScore daily summary from $srcPath" -ForegroundColor Cyan
$rows = Import-Csv -Path $srcPath

# Normalize to array regardless of single-row vs multi-row vs empty
[array]$rowArray = $rows

if ($rowArray.Length -eq 0) {
    Write-Host "[GS-EXPORT] WARN: No rows in gatescore_daily_summary.csv" -ForegroundColor Yellow
    exit 0
}

$nvdaRows = $rowArray | Where-Object { $_.symbol -eq "NVDA" }
[array]$nvdaArray = $nvdaRows

if ($nvdaArray.Length -eq 0) {
    Write-Host "[GS-EXPORT] WARN: No NVDA rows found in gatescore_daily_summary.csv" -ForegroundColor Yellow
    exit 0
}

Write-Host "[GS-EXPORT] Writing NVDA GateScore subset to $outPath" -ForegroundColor Cyan
$nvdaArray |
    Select-Object `
        as_of_date,
        symbol,
        count_signals,
        mean_edge_ratio,
        mean_micro_score,
        pnl_samples,
        mean_pnl |
    Export-Csv -Path $outPath -NoTypeInformation -Encoding UTF8

Write-Host "[GS-EXPORT] Sample NVDA rows:" -ForegroundColor Yellow
$nvdaArray |
    Select-Object -First 5 as_of_date, symbol, count_signals, mean_edge_ratio, mean_micro_score, pnl_samples, mean_pnl |
    Format-Table -AutoSize

exit 0