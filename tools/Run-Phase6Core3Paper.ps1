[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$env:PYTHONPATH = Join-Path $repoRoot "src"
$py = Join-Path $repoRoot ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { Write-Host "[PHASE6] Missing python: $py" -ForegroundColor Red; exit 2 }

# Fail-closed: require paper candidates (router reads logs/paper_trades.jsonl)
if (-not (Test-Path ".\logs\paper_trades.jsonl")) {
  Write-Host "[PHASE6] FAIL-CLOSED: missing logs\paper_trades.jsonl. Run your paper pipeline first." -ForegroundColor Red
  exit 3
}

Write-Host "[PHASE6] CORE3 PAPER router run (NVDA_BPLUS + SPY_ORB + QQQ_ORB)" -ForegroundColor Cyan
& $py .\tools\phase6_route_core3_paper.py
exit $LASTEXITCODE