[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Set-Location $repoRoot

$py = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "Python exe not found: $py" }

$env:PYTHONPATH = Join-Path $repoRoot "src"

& $py -m pytest -q `
  tests/test_phase5_ev_bands_basic.py `
  tests/test_phase5_riskmanager_combined_gates.py `
  tests/test_phase5_riskmanager_daily_loss_integration.py `
  tests/test_execution_engine_phase5_guard.py `
  tests/test_ib_phase5_guard.py
exit $LASTEXITCODE