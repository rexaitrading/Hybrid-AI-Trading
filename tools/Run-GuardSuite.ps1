[CmdletBinding()]
param()

$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

# Script lives under repoRoot\tools -> go up to repo root
$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$py = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "Missing venv python at $py" }

# Ensure tests can import src/hybrid_ai_trading consistently
$oldPyPath = $env:PYTHONPATH
$env:PYTHONPATH = (Join-Path $repoRoot "src")

function Run-Step([string]$label, [scriptblock]$action) {
  Write-Host ("[GUARDSUITE] {0}" -f $label) -ForegroundColor Cyan
  & $action
  $code = $LASTEXITCODE
  if ($code -ne 0) {
    Write-Host ("[GUARDSUITE] FAIL: {0} (exit={1})" -f $label, $code) -ForegroundColor Red
    exit $code
  }
}

try {
  Run-Step "py_compile execution_engine_phase5_guard.py" {
    & $py -m py_compile .\src\hybrid_ai_trading\execution\execution_engine_phase5_guard.py
  }

  Run-Step "pytest test_execution_engine_phase5_guard.py" {
    & $py -m pytest -q .\tests\test_execution_engine_phase5_guard.py
  }

  Run-Step "pytest phase5 riskmanager slice" {
    & $py -m pytest -q .\tests\test_phase5_riskmanager_combined_gates.py .\tests\test_phase5_riskmanager_daily_loss_integration.py
  }

  Write-Host "[OK] Guard + Phase5 risk suite green." -ForegroundColor Green
  exit 0
}
finally {
  $env:PYTHONPATH = $oldPyPath
}