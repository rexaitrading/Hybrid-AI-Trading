[CmdletBinding()]
param(
    [int]$MinTrades = 3
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
$logsPath = Join-Path $repoRoot "logs"

$today = (Get-Date).ToString("yyyy-MM-dd")

Write-Host "`n[EV-READINESS] Today = $today" -ForegroundColor Cyan

# --- Phase23 health check ---
$phase23Csv = Join-Path $logsPath "phase23_health_daily.csv"
$phase23Ok  = $false
if (Test-Path $phase23Csv) {
    $rows = Import-Csv $phase23Csv
    $row  = $rows | Select-Object -Last 1
    if ($row) {
        # Try as_of_date / date / day_id
        $props = $row.PSObject.Properties
        $dateVal = $null
        foreach ($name in @('as_of_date','date','day_id')) {
            $p = $props[$name]
            if ($p -ne $null -and $p.Value) {
                $dateVal = [string]$p.Value
                break
            }
        }
        if ($dateVal) {
            if ($dateVal.Length -ge 10) { $dateVal = $dateVal.Substring(0,10) }
            if ($dateVal -eq $today) {
                $phase23Ok = $true
            }
        }
    }
}
Write-Host ("[EV-READINESS] phase23_health_ok_today = {0}" -f $phase23Ok) -ForegroundColor Yellow

# --- EV-hard veto daily check ---
$evCsv     = Join-Path $logsPath "phase5_ev_hard_veto_daily.csv"
$evHardOk  = $false
if (Test-Path $evCsv) {
    $rows = Import-Csv $evCsv
    # simple: presence of today's row
    $row  = $rows | Where-Object { $_.date -eq $today } | Select-Object -First 1
    if ($row) {
        $evHardOk = $true
    }
}
Write-Host ("[EV-READINESS] ev_hard_daily_ok_today = {0}" -f $evHardOk) -ForegroundColor Yellow

# --- GateScore freshness for NVDA ---
$gsCsv = Join-Path $logsPath "gatescore_daily_summary.csv"
$gsFreshNvda = $false
if (Test-Path $gsCsv) {
    $rows = Import-Csv $gsCsv
    $row  = $rows | Where-Object { $_.symbol -eq 'NVDA' -and $_.as_of_date -like "$today*" } | Select-Object -First 1
    if ($row) {
        $gsFreshNvda = $true
    }
}
Write-Host ("[EV-READINESS] gatescore_fresh_today (NVDA) = {0}" -f $gsFreshNvda) -ForegroundColor Yellow

# --- EV-band daily summary (n_trades) ---
$bandCsv = Join-Path $logsPath "phase5_ev_band_daily_summary.csv"
if (-not (Test-Path $bandCsv)) {
    Write-Host "[EV-READINESS] MISSING logs\phase5_ev_band_daily_summary.csv" -ForegroundColor Red
    return
}

$rows = Import-Csv $bandCsv
$syms = "NVDA","SPY","QQQ"
foreach ($sym in $syms) {
    $row = $rows | Where-Object { $_.symbol -eq $sym -and $_.date -like "$today*" } | Select-Object -First 1
    if (-not $row) {
        Write-Host ("[EV-READINESS] {0}: NO row for today in EV-band summary." -f $sym) -ForegroundColor Yellow
        continue
    }

    $n = 0
    if ($row.PSObject.Properties.Name -contains "n_trades") {
        [void][int]::TryParse([string]$row.n_trades, [ref]$n)
    }
    $ok = ($n -ge $MinTrades)
    Write-Host ("[EV-READINESS] {0}: n_trades={1}, MinTrades={2}, EvBandSamplesOk={3}" -f `
        $sym, $n, $MinTrades, $ok) -ForegroundColor Green
}
