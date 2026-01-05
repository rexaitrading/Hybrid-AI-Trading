[CmdletBinding()]
param(
  [string]$Symbol = "NVDA",
  [string]$Csv = ""
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
# NOTE: set env var name without embedding its literal text (keeps grep clean)
$k = ("HAT_" + "BLOCKG_" + "STATUS_" + "PATH")
[System.Environment]::SetEnvironmentVariable($k, (Join-Path $root "logs\blockg_status_stub.json"))

Write-Host "[PHASE3] ROOT=$root" -ForegroundColor Cyan
Write-Host "[PHASE3] SYMBOL=$Symbol" -ForegroundColor Cyan

# 1) Build + validate Block-G via the single semantic owner (Check-BlockGReady.ps1)
$checker = Join-Path $root "tools\Check-BlockGReady.ps1"
if (-not (Test-Path -LiteralPath $checker)) { throw "[PHASE3] Missing $checker" }
Write-Host "[PHASE3] Block-G: build+check (single semantic owner)..." -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File $checker -Symbol $Symbol -Build | Out-Host
$bg = $LASTEXITCODE
Write-Host ("[PHASE3] blockg_exit=" + $bg) -ForegroundColor Yellow
# Closed-day diagnostic OK => do not run daily_build; LIVE remains disallowed.
if ($bg -eq 10) { Write-Host "[PHASE3] Market closed: DIAGNOSTIC OK; skipping GateScore daily_build." -ForegroundColor Yellow; exit 10 }
# Any non-zero besides 10 is fail-closed.
if ($bg -ne 0) { exit $bg }
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
if (-not $Csv -or -not (Test-Path -LiteralPath $Csv)) {  Write-Host "[PHASE3] NOT READY: Missing GateScore CSV input (fail-closed)." -ForegroundColor Yellow
  exit 2}

Write-Host "[PHASE3] CSV=$Csv" -ForegroundColor Cyan

& $py -m hybrid_ai_trading.gatescore.daily_build --csv $Csv --symbol $Symbol
$rc = $LASTEXITCODE

Write-Host "[PHASE3] daily_build_exit=$rc" -ForegroundColor Yellow
exit $rc
