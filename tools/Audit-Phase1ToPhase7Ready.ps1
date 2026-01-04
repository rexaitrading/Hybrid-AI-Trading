[CmdletBinding()]
param(
  [switch]$RunPytests
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$tools = Split-Path -Parent $PSCommandPath
$repo  = Split-Path -Parent $tools
Set-Location -LiteralPath $repo

function OK($m){ Write-Host "[OK] $m" -ForegroundColor Green }
function NO($m){ Write-Host "[FAIL] $m" -ForegroundColor Red }
function WARN($m){ Write-Host "[WARN] $m" -ForegroundColor Yellow }

# --- Hard safety: force paper mode for all audit runs ---
$env:HAT_IS_PAPER = "1"

# --- A) Chokepoint audit: no live modules read *_events_real.jsonl ---
try {
  powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repo "tools\Audit-NoLiveReads-EventsReal.ps1") | Out-Host
  if($LASTEXITCODE -ne 0){ throw "Audit-NoLiveReads-EventsReal exit=$LASTEXITCODE" }
  OK "No live modules reference *_events_real.jsonl"
} catch {
  NO $_
  exit 2
}

# --- B) Required toolchain presence (Phases 1-7) ---
$must = @(
  "tools\Run-Phase1ToPhase7Daily.ps1",
  "tools\Run-Phase1ReplaySuite.ps1",
  "tools\Run-Phase2FromPhase1.ps1",
  "tools\Build-GateScorePnlSummary.ps1",
  "tools\Build-BlockGStatusStub.ps1",
  "tools\Check-BlockGDiagnosticOk.ps1",
  "tools\Build-EvHardEvidenceRaw.ps1",
  "tools\Build-EvHardSnapshot.ps1",
  "tools\Run-EvHardVetoDaily.ps1",
  "tools\Run-IntelPipeline.ps1"
)

$missing = @()
foreach($p in $must){
  $full = Join-Path $repo $p
  if(-not (Test-Path -LiteralPath $full)){ $missing += $p }
}
if($missing.Count -gt 0){
  NO ("Missing required scripts: " + ($missing -join ", "))
  exit 2
}
OK "Required Phase1→Phase7 + Intel scripts present"

# --- C) Python import sanity (RunContext + BlockG modules must import) ---
try {
  $env:PYTHONPATH = (Resolve-Path .\src).Path
  python -c "import hybrid_ai_trading; from hybrid_ai_trading.runtime.run_context import RunContext; from hybrid_ai_trading.execution import blockg_enforce; from hybrid_ai_trading.broker import ib_safe; print('IMPORT_OK')" | Out-Host
  OK "Core python imports OK (RunContext, blockg_enforce, ib_safe)"
} catch {
  NO "Python import sanity failed: $_"
  exit 2
}

# --- D) Optional pytest slice (fast) ---
if($RunPytests){
  try {
    pytest -q `
      tests/test_blockg_enforce.py `
      tests/test_blockg_broker_base_guard.py `
      tests/execution/test_blockg_order_manager_guard.py `
      tests/test_execution_engine_phase5_guard.py | Out-Host
    OK "Pytest slice OK"
  } catch {
    NO "Pytest slice failed: $_"
    exit 2
  }
} else {
  WARN "Pytests skipped (use -RunPytests to enable)"
}

# --- E) Block-G readiness (weekend expected fail) ---
try {
  powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repo "tools\Check-BlockGDiagnosticOk.ps1") -Symbol NVDA -Build | Out-Host
  $code = $LASTEXITCODE
  if($code -eq 0){
    WARN "Block-G READY (this should only happen on open market + all gates true)"
  } else {
    WARN "Block-G NOT READY (expected on market-closed days). exit=$code"
  }
  OK "Block-G check executed deterministically"
} catch {
  NO "Block-G check failed to run: $_"
  exit 2
}

OK "PHASE1→PHASE7 AUDIT COMPLETE"
exit 0
