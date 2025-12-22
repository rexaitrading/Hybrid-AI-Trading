[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol="NVDA"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$root = (Resolve-Path ".").Path
Set-Location $root
$today = (Get-Date).ToString("yyyy-MM-dd")

Write-Host "[PRE] RepoRoot=$root Today=$today Symbol=$Symbol" -ForegroundColor Cyan

# --- 0) Phase23 health daily (must be today-stamped) ---
$phase23 = ".\tools\Run-Phase23HealthDaily.ps1"
if(Test-Path $phase23){
  & $phase23 | Out-Host
  if($LASTEXITCODE -ne 0){ throw "[PRE] Run-Phase23HealthDaily failed rc=$LASTEXITCODE" }
} else {
  Write-Host "[PRE] WARN: tools\Run-Phase23HealthDaily.ps1 not found (phase23 likely stale -> fail-closed)" -ForegroundColor Yellow
}

# --- 1) Phase-4 validation (must be today-stamped) ---
& ".\tools\Run-Phase4Validation.ps1"
if($LASTEXITCODE -ne 0){ throw "[PRE] Phase4 validation failed rc=$LASTEXITCODE" }

# --- RunContext (single source of truth for mode/state) ---
if(Test-Path ".\tools\Build-RunContextStub.ps1"){
  & ".\tools\Build-RunContextStub.ps1" -Symbol $Symbol | Out-Host
} else {
  Write-Host "[PRE] WARN: tools\Build-RunContextStub.ps1 not found" -ForegroundColor Yellow
}


# --- 2) GateScore events producers (best-effort; strict gating enforced downstream) ---
try {
  if(Test-Path ".\tools\Write-NvdaGateScoreEventsFromPaperlive.ps1"){
    & ".\tools\Write-NvdaGateScoreEventsFromPaperlive.ps1" -Mode rewrite -MinEvents 10 | Out-Host
  } else {
    Write-Host "[PRE] WARN: NVDA GateScore events producer not found" -ForegroundColor Yellow
  }
} catch {
  Write-Host "[PRE] WARN: NVDA GateScore events producer failed: $($_.Exception.Message)" -ForegroundColor Yellow
}

try {
  if(Test-Path ".\tools\Write-SpyGateScoreEventsFromPaperlive.ps1"){
    & ".\tools\Write-SpyGateScoreEventsFromPaperlive.ps1" -Mode rewrite -MinEvents 50 | Out-Host
  } else {
    Write-Host "[PRE] WARN: SPY GateScore events producer not found" -ForegroundColor Yellow
  }
} catch {
  Write-Host "[PRE] WARN: SPY GateScore events producer failed: $($_.Exception.Message)" -ForegroundColor Yellow
}

# QQQ currently stubbed (dev readiness)
try {
  if(Test-Path ".\tools\Write-SpyQqqGateScoreEventsStub.ps1"){
    & ".\tools\Write-SpyQqqGateScoreEventsStub.ps1" -Symbol QQQ -N 50 | Out-Host
  } else {
    Write-Host "[PRE] WARN: QQQ GateScore stub not found" -ForegroundColor Yellow
  }
} catch {
  Write-Host "[PRE] WARN: QQQ GateScore stub failed: $($_.Exception.Message)" -ForegroundColor Yellow
}

# --- 3) GateScore summaries (STRICT-TODAY: no stale carry) ---
$gsPnl = ".\tools\Build-GateScorePnlSummary.ps1"
$gsDaily = ".\tools\Build-GateScoreDailySummary.ps1"

if(Test-Path $gsPnl){
  & $gsPnl -StrictToday
  # allow fail-closed rc=2 (no today events) so Block-G can report reasons deterministically
  if($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne 2){ throw "[PRE] Build-GateScorePnlSummary failed rc=$LASTEXITCODE" }
} else {
  Write-Host "[PRE] WARN: tools\Build-GateScorePnlSummary.ps1 not found" -ForegroundColor Yellow
}

if(Test-Path $gsDaily){
  & $gsDaily
  # allow fail-closed rc=2 (no rows today) to flow into BlockG later; still deterministic
  if($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne 2){ throw "[PRE] Build-GateScoreDailySummary failed rc=$LASTEXITCODE" }
} else {
  Write-Host "[PRE] WARN: tools\Build-GateScoreDailySummary.ps1 not found" -ForegroundColor Yellow
}

# --- 4) Phase-3 GateScore daily_build (quality eval) ---
& ".\tools\Run-Phase3GateScoreDaily.ps1" -Symbol $Symbol
$gsRc = $LASTEXITCODE
if($gsRc -ne 0 -and $gsRc -ne 2){ throw "[PRE] Phase3 GateScore failed rc=$gsRc" }

# --- 5) EV evidence raw (descriptive; used by EV-hard snapshot) ---
$evEvidence = ".\tools\Build-EvHardEvidenceRaw.ps1"
if(Test-Path $evEvidence){
  & $evEvidence | Out-Host
  if($LASTEXITCODE -ne 0){ throw "[PRE] Build-EvHardEvidenceRaw failed rc=$LASTEXITCODE" }
} else {
  Write-Host "[PRE] WARN: tools\Build-EvHardEvidenceRaw.ps1 not found (EV-hard will likely fail-closed)" -ForegroundColor Yellow
}

# --- 6) EV-hard strict-today pipeline (fail-closed) ---
& ".\tools\Build-EvHardSnapshot.ps1"
& ".\tools\Compute-Phase5EvHardSnapshotInput.ps1" -EvidencePath ".\logs\ev_hard_snapshot.json"
& ".\tools\Export-Phase5EvHardVetoDailySnapshot.ps1"
& ".\tools\Run-EvHardVetoDaily.ps1"

# --- 7) Build Block-G status + check (authoritative) ---
& ".\tools\Build-BlockGStatusStub.ps1"
& ".\tools\Check-BlockGReady.ps1" -Symbol $Symbol

$rc = $LASTEXITCODE
Write-Host "[PRE] BlockG check rc=$rc" -ForegroundColor Yellow
exit $rc
