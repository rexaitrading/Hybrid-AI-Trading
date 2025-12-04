param(
    [string]$Day = $(Get-Date -Format "yyyy-MM-dd")   # optional override, e.g. "2025-11-29"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $repoRoot
Set-Location $repoRoot

# Parse Day as local date
try {
    $dayDate = [datetime]::Parse($Day).Date
} catch {
    Write-Host "[ERROR] Could not parse Day='$Day' as a date." -ForegroundColor Red
    return
}

$csvs = @(
    'logs\nvda_phase5_paper_for_notion.csv',
    'logs\spy_phase5_paper_for_notion.csv',
    'logs\qqq_phase5_paper_for_notion.csv'
)

Write-Host "`n[PHASE5] Daily LIVE paper report for $($dayDate.ToString('yyyy-MM-dd'))" -ForegroundColor Cyan

$records = @()

foreach ($rel in $csvs) {
    $full = Join-Path $repoRoot $rel
    if (-not (Test-Path $full)) {
        Write-Host "[WARN] CSV not found: $full" -ForegroundColor Yellow
        continue
    }

    $rows = Import-Csv $full

    foreach ($r in $rows) {
        if ($r.PSObject.Properties['regime'] -eq $null -or $r.regime -notlike '*LIVE*') { continue }

        $ts = $null
        try {
            $ts = [datetime]$r.ts
        } catch {
            continue
        }
        $tsLocal = $ts.ToLocalTime()

        if ($tsLocal.Date -ne $dayDate.Date) { continue }

        if ($r.PSObject.Properties['realized_pnl'] -eq $null -or
            [string]::IsNullOrWhiteSpace($r.realized_pnl)) { continue }

        [double]$pnl = 0.0
        if (-not [double]::TryParse($r.realized_pnl.ToString(), [ref]$pnl)) { continue }

        $records += [pscustomobject]@{
            ts           = $tsLocal
            symbol       = $r.symbol
            regime       = $r.regime
            side         = $r.side
            realized_pnl = $pnl
        }
    }
}

if (($records | Measure-Object).Count -eq 0) {
    Write-Host "`n[SUMMARY] No LIVE trades found in CSVs for $($dayDate.ToString('yyyy-MM-dd')) (local)." -ForegroundColor Yellow

    # Phase-5 EV hard-veto configuration summary (SPY/QQQ)
    Write-Host ""
    Write-Host "[EV-HARD] Phase-5 EV hard-veto summary (SPY/QQQ):" -ForegroundColor Cyan
    & (Join-Path $PSScriptRoot 'Build-EvHardVetoSummary.ps1')

    return
}

Write-Host "`n[SUMMARY] Per-symbol LIVE paper PnL" -ForegroundColor Cyan

$records |
    Group-Object symbol, regime |
    ForEach-Object {
        $sym     = $_.Group[0].symbol
        $regime  = $_.Group[0].regime
        $count   = ($_.Group | Measure-Object).Count
        $sumPnl  = ($_.Group | Measure-Object -Property realized_pnl -Sum).Sum
        $avgPnl  = ($_.Group | Measure-Object -Property realized_pnl -Average).Average

        Write-Host ""
        Write-Host "  [$sym / $regime]" -ForegroundColor Green
        Write-Host ("    trades: {0}" -f $count)
        Write-Host ("    sum PnL: {0:N4}" -f $sumPnl)
        Write-Host ("    avg PnL: {0:N4}" -f $avgPnl)

        $_.Group |
            Sort-Object ts |
            Select-Object -Last 5 ts, side, realized_pnl |
            Format-Table -Auto
    }

$totalTrades = ($records | Measure-Object).Count
$totalPnlObj = ($records | Measure-Object -Property realized_pnl -Sum)
$avgPnlObj   = ($records | Measure-Object -Property realized_pnl -Average)

$totalPnl    = $totalPnlObj.Sum
$avgTradePnl = $avgPnlObj.Average

Write-Host "`n[SUMMARY] ALL SYMBOLS (LIVE paper, $($dayDate.ToString('yyyy-MM-dd')))" -ForegroundColor Cyan
Write-Host ("  total trades: {0}"   -f $totalTrades)
Write-Host ("  total PnL:    {0:N4}" -f $totalPnl)
Write-Host ("  avg/trade:    {0:N4}" -f $avgTradePnl)

# Phase-5 EV hard-veto configuration summary (SPY/QQQ)
Write-Host ""
Write-Host "[EV-HARD] Phase-5 EV hard-veto summary (SPY/QQQ):" -ForegroundColor Cyan
& (Join-Path $PSScriptRoot 'Build-EvHardVetoSummary.ps1')