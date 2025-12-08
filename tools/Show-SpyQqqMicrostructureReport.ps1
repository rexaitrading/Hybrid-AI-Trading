[CmdletBinding()]
param(
    [string] $Symbol = "",      # e.g. "SPY" or "QQQ"
    [string] $Regime = ""       # e.g. "SPY_ORB_REPLAY"
)

$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$reportPath = Join-Path $repoRoot "logs\spy_qqq_microstructure_report.csv"

if (-not (Test-Path $reportPath)) {
    Write-Host "[MICRO-REPORT] Report not found at $reportPath. Run Run-SpyQqqMicrostructureReport.ps1 first." -ForegroundColor Red
    exit 1
}

Write-Host "`n[MICRO-REPORT] Loading $reportPath ..." -ForegroundColor Cyan

$rows = Import-Csv $reportPath

if (-not $rows) {
    Write-Host "[MICRO-REPORT] No rows in report." -ForegroundColor Yellow
    exit 0
}

if ($Symbol) {
    $rows = $rows | Where-Object { $_.symbol -eq $Symbol }
}

if ($Regime) {
    $rows = $rows | Where-Object { $_.regime -eq $Regime }
}

if (-not $rows) {
    Write-Host "[MICRO-REPORT] No rows after filters (Symbol='$Symbol', Regime='$Regime')." -ForegroundColor Yellow
    exit 0
}

$rows | Sort-Object symbol, regime, ms_range_bucket, ms_trend_label |
    Format-Table `
        symbol,
        regime,
        ms_range_bucket,
        ms_trend_label,
        trade_count,
        avg_ev,
        avg_realized_pnl_paper,
        win_rate,
        avg_ev_gap_abs -AutoSize

Write-Host "`n[MICRO-REPORT] Use -Symbol SPY or -Symbol QQQ to filter; -Regime for more detail." -ForegroundColor Cyan