[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
$logsPath = Join-Path $repoRoot "logs"
$csvPath  = Join-Path $logsPath "spy_qqq_micro_for_notion.csv"

$env:PYTHONPATH = Join-Path $repoRoot "src"
$python = ".\.venv\Scripts\python.exe"

if (-not (Test-Path $csvPath)) {
    Write-Host "[MICRO-PRE] CSV not found at $csvPath" -ForegroundColor Yellow
    exit 0
}

$rows = Import-Csv $csvPath

$today = (Get-Date).ToString("yyyy-MM-dd")
$todayRows = $rows | Where-Object { $_.ts -and $_.ts.Substring(0,10) -eq $today }

if (-not $todayRows) {
    Write-Host "[MICRO-PRE] No rows for today ($today) in spy_qqq_micro_for_notion.csv" -ForegroundColor Yellow
    exit 0
}

$code = @"
from hybrid_ai_trading.risk.risk_phase5_micro_gate import micro_gate_for_symbol
import sys, json

data = json.loads(sys.stdin.read())
dec = micro_gate_for_symbol(
    data['symbol'],
    float(data['ms_range_pct']),
    float(data['est_spread_bps']),
    float(data['est_fee_bps']),
)
# simple JSON-like line for PS to parse/print
print(dec.allowed, dec.regime, dec.reason)
"@

Write-Host "`n[MICRO-PRE] Shadow micro-gate decisions for SPY/QQQ (today)" -ForegroundColor Cyan

foreach ($sym in "SPY","QQQ") {
    $symRows = $todayRows | Where-Object { $_.symbol -eq $sym }
    if (-not $symRows) {
        Write-Host "[MICRO-PRE] $($sym): no rows for today" -ForegroundColor Yellow
        continue
    }

    $row  = $symRows[-1] | Select-Object symbol, ms_range_pct, est_spread_bps, est_fee_bps
    $json = $row | ConvertTo-Json -Compress

    $result = $json | & $python -c $code
    $parts  = $result -split ' ', 3
    $allowed = $parts[0]
    $regime  = $parts[1]
    $reason  = $parts[2]

    Write-Host ("[MICRO-PRE] {0}: allowed={1}, regime={2}, reason={3}" -f `
        $sym, $allowed, $regime, $reason) -ForegroundColor Green

    if ($allowed -eq "False") {
        Write-Host ("[MICRO-PRE] HARD WARN: {0} micro regime is RED. Do NOT run live SPY/QQQ today." -f $sym) `
            -ForegroundColor Red
    }
}

