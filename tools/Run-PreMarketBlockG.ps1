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


# --- 0) PRODUCE TODAY INPUTS (fail-closed) ---
# EV evidence raw -> required by Build-EvHardSnapshot strict-today
$evEvidence = ".\tools\Build-EvHardEvidenceRaw.ps1"
if(Test-Path $evEvidence){
  & $evEvidence
  if($LASTEXITCODE -ne 0){ throw "[PRE] Build-EvHardEvidenceRaw failed rc=$LASTEXITCODE" }
} else {
  Write-Host "[PRE] WARN: tools\Build-EvHardEvidenceRaw.ps1 not found (EV-hard will likely fail-closed)" -ForegroundColor Yellow
}

# GateScore daily summary -> required by BlockG strict-today GateScore freshness
$gsPnl = ".\tools\Build-GateScorePnlSummary.ps1"
$gsDaily = ".\tools\Build-GateScoreDailySummary.ps1"
if(Test-Path $gsPnl){
  & $gsPnl
  if($LASTEXITCODE -ne 0){ throw "[PRE] Build-GateScorePnlSummary failed rc=$LASTEXITCODE" }
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
# 1) EV-hard strict-today pipeline (fail-closed)
& ".\tools\Build-EvHardSnapshot.ps1"
& ".\tools\Compute-Phase5EvHardSnapshotInput.ps1" -EvidencePath ".\logs\ev_hard_snapshot.json"
& ".\tools\Export-Phase5EvHardVetoDailySnapshot.ps1"
& ".\tools\Run-EvHardVetoDaily.ps1"

# 2) Phase-4 validation
& ".\tools\Run-Phase4Validation.ps1"
if($LASTEXITCODE -ne 0){ throw "[PRE] Phase4 validation failed rc=$LASTEXITCODE" }

# 3) Phase-3 GateScore
& ".\tools\Run-Phase3GateScoreDaily.ps1" -Symbol $Symbol
$gsRc = $LASTEXITCODE
if($gsRc -ne 0 -and $gsRc -ne 2){ throw "[PRE] Phase3 GateScore failed rc=$gsRc" }

# 4) Build Block-G status + check
& ".\tools\Build-BlockGStatusStub.ps1"
& ".\tools\Check-BlockGReady.ps1" -Symbol $Symbol

$rc = $LASTEXITCODE
Write-Host "[PRE] BlockG check rc=$rc" -ForegroundColor Yellow
exit $rc
