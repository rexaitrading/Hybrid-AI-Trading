[CmdletBinding()]
param(
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","HK_SH","HK_SZ")]
  [string]$Market="US",
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol="ALL"
)

Set-StrictMode -Version Latest
chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding  = [System.Text.Encoding]::UTF8
$ErrorActionPreference="Stop"

# A3_PREMARKET_ENV_WIRE_BEGIN
$env:HAT_MARKET = ((($Market + "")).Trim().ToUpperInvariant())
if(-not $env:HAT_MARKET){ $env:HAT_MARKET = "US" }
$env:HAT_SYMBOL = ((($Symbol + "")).Trim().ToUpperInvariant())
if(-not $env:HAT_SYMBOL){ $env:HAT_SYMBOL = "ALL" }
# A3_PREMARKET_ENV_WIRE_END

# A3_PREMARKET_RUNCONTEXT_BEGIN
$rc = (& (Join-Path $PSScriptRoot "Resolve-RunContext.ps1") -Market $env:HAT_MARKET -Symbol $env:HAT_SYMBOL | Out-String | ConvertFrom-Json)
if(-not $rc -or -not $rc.as_of_date){ throw "[FAIL-CLOSED] Resolve-RunContext missing as_of_date" }
if(-not $rc.logs_dir){ throw "[FAIL-CLOSED] Resolve-RunContext missing logs_dir" }
$env:HAT_AS_OF_DATE = ([string]$rc.as_of_date)
# [A3] Back-compat: unify as-of-date env vars (single truth from RunContext)
$env:HAT_ASOF_DATE = ((($env:HAT_AS_OF_DATE + "")).Trim())
$env:HAT_LOGS_DIR   = ([string]$rc.logs_dir)
if($rc.PSObject.Properties.Name -contains "session_name"){ $env:HAT_SESSION_NAME = ([string]$rc.session_name) }
Write-Host ("[A3] rc market=" + $env:HAT_MARKET + " as_of=" + $env:HAT_AS_OF_DATE + " session=" + (($env:HAT_SESSION_NAME + "")).Trim() + " logs_dir=" + $env:HAT_LOGS_DIR) -ForegroundColor DarkGray
# A3_PREMARKET_RUNCONTEXT_END

# ---- Phase today-ness hard gates (fail-closed) ----
$phase4 = Join-Path $PSScriptRoot "Check-Phase4Today.ps1"
& $phase4
if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }

function Invoke-PaperliveToday([string]$sym){
  $map = @{
    "NVDA" = @(".\tools\Run-NvdaPaperliveToday.ps1", ".\tools\Expand-NvdaPaperliveToday.ps1", ".\tools\Export-NvdaPaperliveResultsToday.ps1")
    "SPY"  = @(".\tools\Run-SpyPaperliveToday.ps1",  ".\tools\Expand-SpyPaperliveToday.ps1")
    "QQQ"  = @(".\tools\Run-QqqPaperliveToday.ps1",  ".\tools\Expand-QqqPaperliveToday.ps1")
  }
  if(-not $map.ContainsKey($sym)){ return }
  foreach($p in @($map[$sym])){
    if(Test-Path -LiteralPath $p){
      Write-Host ("[PRE] Phase5 producer: {0} ({1})" -f $sym,$p) -ForegroundColor DarkCyan
      & $p | Out-Host
      if($LASTEXITCODE -ne 0){ throw ("[PRE] Phase5 producer failed: {0} rc={1}" -f $p,$LASTEXITCODE) }
    } else {
      Write-Host ("[PRE] WARN: producer not found: {0}" -f $p) -ForegroundColor Yellow
    }
  }
}

# ---- Phase5 paperlive TODAY producers (evidence build) ----
if($Symbol -eq "ALL"){
  foreach($s in @("NVDA","SPY","QQQ")){ Invoke-PaperliveToday $s }
} else {
  Invoke-PaperliveToday $Symbol
}
$phase5 = Join-Path $PSScriptRoot "Check-Phase5Today.ps1"
# ALL_MODE_PHASE_GATES
if($Symbol -eq "ALL"){
  foreach($s in @("NVDA","SPY","QQQ")){
    & $phase4
    if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }

    & $phase5 -Symbol $s -RequireRunContext
    if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }
  }
}else{
  & $phase4
  if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }

  & $phase5 -Symbol $Symbol -RequireRunContext
  if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }
}
#$root = (Resolve-Path ".").Path  # [A3] disabled (env-truth repo root already active)
# [A3] disabled Set-Location $root (env-truth repo root already active)
$today = (($env:HAT_AS_OF_DATE + "")).Trim()

$root = (Resolve-Path -LiteralPath ".").Path
Write-Host "[PRE] RepoRoot=$root Today=$today Symbol=$Symbol" -ForegroundColor Cyan

# --- 0) Phase23 health daily (must be today-stamped) ---
$phase23 = ".\tools\Run-Phase23HealthDaily.ps1"
if(Test-Path $phase23){
  & $phase23 -Market $env:HAT_MARKET -Symbol NVDA | Out-Host
  if($LASTEXITCODE -ne 0){ throw "[PRE] Run-Phase23HealthDaily failed rc=$LASTEXITCODE" }
} else {
  Write-Host "[PRE] WARN: tools\Run-Phase23HealthDaily.ps1 not found (phase23 likely stale -> fail-closed)" -ForegroundColor Yellow
}

# --- 1) Phase-4 validation (must be today-stamped) ---
& ".\tools\Run-Phase4Validation.ps1" -Market $env:HAT_MARKET -Symbol NVDA
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
# A3_GS_MARKET_WIRE_BEGIN
$m0 = (( $env:HAT_MARKET + "" )).Trim().ToUpperInvariant()
if(-not $m0){ $m0 = "US" }
$env:HAT_MARKET = $m0
# A3_GS_MARKET_WIRE_END
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
& ".\tools\Compute-Phase5EvHardSnapshotInput.ps1" -EvidencePath (`
  if($env:HAT_MARKET -and $env:HAT_MARKET -ne "US"){ ".\logs\$($env:HAT_MARKET)\ev_hard_snapshot.json" } else { ".\logs\ev_hard_snapshot.json" } `
)
# A3_EVIDENCEPATH_MARKET_END
& ".\tools\Export-Phase5EvHardVetoDailySnapshot.ps1"
& ".\tools\Run-EvHardVetoDaily.ps1"

# --- 7) Build Block-G status + check (authoritative) ---
& ".\tools\Build-BlockGStatusStub.ps1" -Market $Market -Symbol $Symbol
& ".\tools\Check-BlockGDiagnosticOk.ps1" -Symbol $Symbol

$rc = $LASTEXITCODE
Write-Host "[PRE] BlockG check rc=$rc" -ForegroundColor Yellow
exit $rc
