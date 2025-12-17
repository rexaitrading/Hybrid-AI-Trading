[CmdletBinding()]
param(
  [Parameter(Mandatory=$false)][int]$Limit = 50
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$env:PYTHONPATH = Join-Path $repoRoot "src"
$py = Join-Path $repoRoot ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { Write-Host "[PHASE6] Missing python: $py" -ForegroundColor Red; exit 2 }

Write-Host "[PHASE6] NVDA_BPLUS PAPER router run (safe)" -ForegroundColor Cyan
Write-Host "[PHASE6] RepoRoot=$repoRoot" -ForegroundColor DarkCyan

# Ensure paper candidates exist (fail-closed if missing)
$paper = Join-Path $repoRoot "logs\paper_trades.jsonl"
if (-not (Test-Path $paper)) {
  Write-Host "[PHASE6] FAIL-CLOSED: missing logs\paper_trades.jsonl. Run your paper pipeline first." -ForegroundColor Red
  exit 3
}

& $py .\tools\phase6_route_nvda_bplus_paper.py
$code = $LASTEXITCODE
if ($code -ne 0) { Write-Host "[PHASE6] FAIL router (exit=$code)" -ForegroundColor Red; exit $code }

# Best-effort proof
$log = Join-Path $repoRoot "logs\portfolio_order_intents.jsonl"
if (Test-Path $log) {
  Write-Host "[PHASE6] OK wrote logs\portfolio_order_intents.jsonl" -ForegroundColor Green
} else {
  Write-Host "[PHASE6] WARN: did not see logs\portfolio_order_intents.jsonl (best-effort logging)" -ForegroundColor Yellow
}

exit 0