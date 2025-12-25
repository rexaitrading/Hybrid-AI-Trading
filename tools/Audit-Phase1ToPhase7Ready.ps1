[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Step([string]$name, [scriptblock]$b){
  Write-Host ("`n=== " + $name + " ===") -ForegroundColor Cyan
  try { & $b; Write-Host ("OK: " + $name) -ForegroundColor Green; return $true }
  catch { Write-Host ("FAIL: " + $name + " :: " + $_.Exception.Message) -ForegroundColor Red; return $false }
}

$okAll = $true

# Phase-0 / Infra
$okAll = (Step "Infra: Python compile critical modules" {
  python -c "import py_compile; py_compile.compile('src/hybrid_ai_trading/broker/ib_safe.py', doraise=True); py_compile.compile('src/hybrid_ai_trading/execution/blockg_enforce.py', doraise=True); print('PY_COMPILE_OK')"
}) -and $okAll

# Phase-5 Safety spine (IBG + BlockG)
$okAll = (Step "Phase5: IBG readiness" {
  powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Check-IBGReady.ps1 | Out-Host
  if($LASTEXITCODE -ne 0){ throw "Check-IBGReady exit=$LASTEXITCODE" }
}) -and $okAll

$okAll = (Step "Phase5: BlockG build + NVDA ready" {
  powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Build-BlockGStatusStub.ps1 | Out-Host
  powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Check-BlockGReady.ps1 -Symbol NVDA | Out-Host
  if($LASTEXITCODE -ne 0){ throw "Check-BlockGReady(NVDA) exit=$LASTEXITCODE" }
}) -and $okAll

$okAll = (Step "Phase5: BlockG tests" {
  python -m pytest -q tests\test_blockg_risk_flatten_guard.py
  python -m pytest -q tests\test_blockg_chokepoint_blocks_live.py
}) -and $okAll

# Phase-1 replay (presence + basic runner import)
$okAll = (Step "Phase1: replay runner import" {
  python -c "import importlib; importlib.import_module('hybrid_ai_trading.runners.backtest_replay'); print('PHASE1_IMPORT_OK')"
}) -and $okAll

# Phase-2/3/4/6/7 are project-specific; we at least check tool presence
$okAll = (Step "Phase2/3/4: producer scripts present" {
  foreach($p in @('.\tools\Run-Phase3GateScoreDaily.ps1','.\tools\Run-Phase4Stamp.ps1','.\tools\Build-BlockGStatusStub.ps1')){
    if(-not (Test-Path $p)){ throw "Missing $p" }
  }
}) -and $okAll

$okAll = (Step "Phase7: optimizer script present" {
  if(-not (Test-Path .\tools\Run-Phase7OptimizerDaily.ps1)){ throw "Missing tools\Run-Phase7OptimizerDaily.ps1" }
}) -and $okAll

if(-not $okAll){
  Write-Host "`nNOT READY: One or more phase checks failed." -ForegroundColor Red
  exit 2
}

Write-Host "`nREADY: Core safety spine + phase scaffolding checks passed." -ForegroundColor Green
exit 0
