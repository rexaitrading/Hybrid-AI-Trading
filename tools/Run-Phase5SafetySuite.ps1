[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path ".").Path
$py = Join-Path $repoRoot "C:\HAT\.venv\Scripts\python.exe"
if(-not (Test-Path $py)){ throw "python not found: $py" }

& $py -m pytest -q `
  .\tests\test_execution_engine_phase5_guard.py `
  .\tests\test_ib_phase5_guard.py `
  .\tests\test_blockg_broker_base_guard.py `
  .\tests\test_blockg_risk_flatten_guard.py `
  .\tests\test_runcontext_precedence.py

exit $LASTEXITCODE
