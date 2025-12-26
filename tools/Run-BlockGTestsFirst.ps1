[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "[BLOCKG-FIRST] Running Block-G critical tests..." -ForegroundColor Cyan

pytest -q tests\test_blockg_enforce.py -q
pytest -q tests\test_blockg_enforce_live_order_path.py -q
pytest -q tests\test_execution_engine_phase5_guard.py -q
pytest -q tests\test_ib_adapter_blockg_enforce.py -q
pytest -q tests\test_no_direct_ib_placeorder.py -q

Write-Host "[BLOCKG-FIRST] OK" -ForegroundColor Green
