[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

$srcPath = Join-Path $repoRoot "logs\gatescore_pnl_summary.csv"
$outPath = Join-Path $repoRoot "logs\gatescore_daily_summary.csv"

function Write-Utf8NoBom {
    param([string]$Path, [string]$Text)
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $full = $Path
    if (-not [System.IO.Path]::IsPathRooted($full)) { $full = Join-Path $repoRoot $full }
    [System.IO.File]::WriteAllText($full, $Text, $utf8NoBom)
}

if (-not (Test-Path -LiteralPath $srcPath)) {
    Write-Host "GateScore daily summary: source CSV not found at $srcPath" -ForegroundColor Yellow
    exit 2
}

Write-Host "GateScore daily summary: loading $srcPath" -ForegroundColor Cyan
$rows = Import-Csv -LiteralPath $srcPath
$rowArray = @($rows)

if ($rowArray.Count -eq 0) {
    Write-Host "GateScore daily summary: no rows found in $srcPath" -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

$today = (Get-Date).ToString("yyyy-MM-dd")

# IMPORTANT: NO CARRY-FORWARD.
# Only write rows that are truly stamped today in the source pnl summary.
$todayRows = @($rowArray | Where-Object { ($_.as_of_date + "") -eq $today })

if (-not $todayRows -or $todayRows.Count -eq 0) {
    Write-Host ("GateScore daily summary: WARN no rows for today={0}; fail-closed (no carry-forward)" -f $today) -ForegroundColor Yellow
    $hdr = 'symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date' + "`n"
    Write-Utf8NoBom -Path $outPath -Text $hdr
    exit 2
}

Write-Host "GateScore daily summary: writing $outPath" -ForegroundColor Cyan
$todayRows | Export-Csv -LiteralPath $outPath -NoTypeInformation -Encoding UTF8

Write-Host "GateScore daily summary: sample rows:" -ForegroundColor Yellow
$todayRows |
    Select-Object -First 5 symbol, count_signals, mean_edge_ratio, mean_micro_score, pnl_samples, mean_pnl, as_of_date |
    Format-Table -AutoSize

exit 0
