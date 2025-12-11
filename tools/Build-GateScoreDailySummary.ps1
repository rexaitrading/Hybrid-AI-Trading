[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

$srcPath = Join-Path $repoRoot "logs\\gatescore_pnl_summary.csv"
$outPath = Join-Path $repoRoot "logs\\gatescore_daily_summary.csv"

if (-not (Test-Path $srcPath)) {
    Write-Host "GateScore daily summary: source CSV not found at $srcPath" -ForegroundColor Yellow
    return
}

Write-Host "GateScore daily summary: loading $srcPath" -ForegroundColor Cyan
$rows = Import-Csv -Path $srcPath

# Normalize to array to avoid StrictMode issues on Count
$rowArray = @($rows)

if ($rowArray.Count -eq 0) {
    Write-Host "GateScore daily summary: no rows found in $srcPath" -ForegroundColor Yellow
    return
}

$today = (Get-Date).ToString("yyyy-MM-dd")

# Attach as_of_date to each row
$rowArray | ForEach-Object {
    $_ | Add-Member -NotePropertyName "as_of_date" -NotePropertyValue $today -Force
}

Write-Host "GateScore daily summary: writing $outPath" -ForegroundColor Cyan
$rowArray | Export-Csv -Path $outPath -NoTypeInformation -Encoding UTF8

Write-Host "GateScore daily summary: sample rows:" -ForegroundColor Yellow
$rowArray |
    Select-Object -First 5 symbol, count_signals, mean_edge_ratio, mean_micro_score, pnl_samples, mean_pnl, as_of_date |
    Format-Table -AutoSize