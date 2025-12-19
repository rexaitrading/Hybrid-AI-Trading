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
    Write-Host "[MICRO-GATE] CSV not found at $csvPath" -ForegroundColor Yellow
    exit 1
}

Write-Host "[MICRO-GATE] Spy/QQQ micro gate snapshot from $csvPath" -ForegroundColor Cyan

$rows = Import-Csv $csvPath

# We only care about today
$today = (Get-Date).ToString("yyyy-MM-dd")
$todayRows = $rows | Where-Object {
    $_.ts -and $_.ts.Substring(0,10) -eq $today
}

if (-not $todayRows) {
    Write-Host "[MICRO-GATE] No rows for today ($today)" -ForegroundColor Yellow
    exit 0
}

# Python helper classify_micro_regime
$code = @"
from hybrid_ai_trading.microstructure import classify_micro_regime
import sys, json

data = json.loads(sys.stdin.read())
regime = classify_micro_regime(data['ms_range_pct'], data['est_spread_bps'], data['est_fee_bps'])
print(regime)
"@

foreach ($sym in "SPY","QQQ") {
    $symRows = $todayRows | Where-Object { $_.symbol -eq $sym }
    if (-not $symRows) {
        Write-Host "[MICRO-GATE] $($sym): no micro rows for today" -ForegroundColor Yellow
        continue
    }

    # Use latest row for decision
    $row = $symRows[-1] | Select-Object symbol, ms_range_pct, est_spread_bps, est_fee_bps
    $json = $row | ConvertTo-Json -Compress

    # Pipe JSON into python
    $regime = $json | & $python -c $code
    $regime = $regime.Trim()

    Write-Host ("[MICRO-GATE] {0}: regime={1} (ms_range_pct={2}, spread={3}, fee={4})" -f `
        $sym, $regime, $row.ms_range_pct, $row.est_spread_bps, $row.est_fee_bps) -ForegroundColor Green
}
