[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ")][string]$Symbol = "NVDA",
  [switch]$InfoOnly
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent (Split-Path -Parent $toolsDir)
Set-Location $repoRoot

Write-Host "`n[SMOKE] Phase-5 Risk + Block-G safety slice" -ForegroundColor Cyan
Write-Host "RepoRoot = $repoRoot" -ForegroundColor Gray

$py = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "Missing Python venv: $py" }

$env:PYTHONPATH = Join-Path $repoRoot "src"

# 1) Combined gates
Write-Host "`n[1/3] Combined gates tests" -ForegroundColor Cyan
& $py -m pytest -q tests\test_phase5_riskmanager_combined_gates.py
if ($LASTEXITCODE -ne 0) { throw "Combined gates failed (exit=$LASTEXITCODE)" }

# 2) Phase-4 harness
Write-Host "`n[2/3] Phase-4 harness" -ForegroundColor Cyan
$phase4 = ".\tools\Run-Phase4Validation.ps1"
if (-not (Test-Path $phase4)) { throw "Missing Phase-4 harness: $phase4" }
powershell -NoProfile -ExecutionPolicy Bypass -File $phase4
if ($LASTEXITCODE -ne 0) { throw "Phase-4 harness failed (exit=$LASTEXITCODE)" }

# 3) Block-G checker
Write-Host "`n[3/3] Block-G checker (-Symbol $Symbol)" -ForegroundColor Cyan
$checker = ".\tools\Check-BlockGReady.ps1"
if (-not (Test-Path $checker)) { throw "Missing Block-G checker: $checker" }

powershell -NoProfile -ExecutionPolicy Bypass -File $checker -Symbol $Symbol
$rc = $LASTEXITCODE
Write-Host ("[BLOCKG] ExitCode={0}" -f $rc) -ForegroundColor Gray

# Print key contract fields (if present)
$contractPath = ".\logs\blockg_status_stub.json"
if (Test-Path $contractPath) {
  try {
    $c = Get-Content $contractPath -Raw | ConvertFrom-Json
    $c | Select-Object as_of_date,phase4_ok_today,phase23_health_ok_today,ev_hard_daily_ok_today,gatescore_ok_today,nvda_blockg_ready,spy_blockg_ready,qqq_blockg_ready | Format-List
  } catch {
    Write-Host "[BLOCKG] Could not parse blockg_status_stub.json" -ForegroundColor Yellow
  }
} else {
  Write-Host "[BLOCKG] Missing logs\blockg_status_stub.json" -ForegroundColor Yellow
}

# Fail smoke unless READY
if ($rc -ne 0) {
  if ($InfoOnly) {
    Write-Host "[SMOKE] InfoOnly: Block-G not ready (exit=$rc) but not failing the smoke." -ForegroundColor Yellow
    exit 0
  }
  exit $rc
}

Write-Host "`n[SMOKE] PASS (combined gates + Phase-4 + Block-G READY)" -ForegroundColor Green
exit 0