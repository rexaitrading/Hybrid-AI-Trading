[CmdletBinding()]
param(
  [string]$Csv = "",
  [string]$Symbol = "NVDA",
  [string]$StatusPath = ".\logs\blockg_status_stub.json",
  [string]$Out = ".\logs\gatescore_daily_build.jsonl"
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$root = (Resolve-Path ".").Path
$py   = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "[PHASE3] Python exe not found: $py" }

# Hard lock imports to this repo
$env:PYTHONNOUSERSITE = "1"
$env:PYTHONPATH = (Join-Path $root "src")
# Block-G deterministic contract path (single source of truth)
$env:HAT_BLOCKG_STATUS_PATH = (Join-Path $root "logs\blockg_status_stub.json")
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"

Write-Host "[PHASE3] ROOT=$root" -ForegroundColor Cyan
Write-Host "[PHASE3] SYMBOL=$Symbol" -ForegroundColor Cyan
Write-Host "[PHASE3] STATUS_PATH=$StatusPath" -ForegroundColor Cyan
Write-Host "[PHASE3] OUT=$Out" -ForegroundColor Cyan

# 1) Build Block-G contract first (single source of truth)
$builder = Join-Path $root "tools\Build-BlockGStatusStub.ps1"
if (-not (Test-Path $builder)) { throw "[PHASE3] Missing $builder" }
& $builder | Out-Host

# 2) Run GateScore daily_build (fail-closed: returns 0/2)
#
$rc = $LASTEXITCODE

Write-Host "[PHASE3] daily_build_exit=$rc" -ForegroundColor Yellow
exit $rc
