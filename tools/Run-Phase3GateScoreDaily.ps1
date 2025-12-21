[CmdletBinding()]
param(
  [string]$Symbol = "NVDA",
  [string]$Csv = "",
  [string]$StatusPath = ".\logs\blockg_status_stub.json"
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$root = (Resolve-Path ".").Path
$py   = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "[PHASE3] Python exe not found: $py" }

# Hard lock imports to this repo
$env:PYTHONNOUSERSITE = "1"
$env:PYTHONPATH = (Join-Path $root "src")
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"

# Deterministic Block-G contract path (single source of truth)
$env:HAT_BLOCKG_STATUS_PATH = (Join-Path $root "logs\blockg_status_stub.json")

Write-Host "[PHASE3] ROOT=$root" -ForegroundColor Cyan
Write-Host "[PHASE3] SYMBOL=$Symbol" -ForegroundColor Cyan

# 1) Build Block-G contract first (single source of truth)
$builder = Join-Path $root "tools\Build-BlockGStatusStub.ps1"
if (-not (Test-Path $builder)) { throw "[PHASE3] Missing $builder" }
& $builder | Out-Host

# 2) Choose CSV input for daily_build (REAL CLI)
if (-not $Csv) {
  $cands = @(
    (Join-Path $root "logs\gatescore_pnl_summary.csv"),
    (Join-Path $root "logs\gatescore_daily_summary.csv"),
    (Join-Path $root "logs\gatescore_daily_summary_nvda.csv"),
    (Join-Path $root "logs\nvda_gatescore_samples.csv")
  )
  $Csv = ($cands | Where-Object { Test-Path $_ } | Select-Object -First 1)
}
if (-not $Csv -or -not (Test-Path -LiteralPath $Csv)) {
  throw "[PHASE3] Missing GateScore CSV input. Provide -Csv or ensure logs\gatescore_pnl_summary.csv exists."
}

Write-Host "[PHASE3] CSV=$Csv" -ForegroundColor Cyan

# 3) Run GateScore daily_build (current CLI supports --csv/--symbol only)
& $py -m hybrid_ai_trading.gatescore.daily_build --csv $Csv --symbol $Symbol
$rc = $LASTEXITCODE

Write-Host "[PHASE3] daily_build_exit=$rc" -ForegroundColor Yellow
exit $rc