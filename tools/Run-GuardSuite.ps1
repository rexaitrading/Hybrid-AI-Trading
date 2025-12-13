[CmdletBinding()]
param()

$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

# Script lives under repoRoot\tools -> go up to repo root
$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$py = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "Missing venv python at $py" }

& $py -m py_compile .\src\hybrid_ai_trading\execution\execution_engine_phase5_guard.py
& $py -m pytest -q .\tests\test_execution_engine_phase5_guard.py
& $py -m pytest -q .\tests\test_phase5_riskmanager_combined_gates.py .\tests\test_phase5_riskmanager_daily_loss_integration.py

Write-Host "[OK] Guard + Phase5 risk suite green." -ForegroundColor Green