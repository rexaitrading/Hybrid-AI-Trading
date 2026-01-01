[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

function Write-Utf8NoBom {
  param([string]$Path,[string]$Text)
  $enc = New-Object System.Text.UTF8Encoding($false)
  $Text = $Text -replace "`r`n","`n"
  if($Text.Length -gt 0 -and $Text[-1] -ne "`n"){ $Text += "`n" }
  [System.IO.File]::WriteAllText($Path,$Text,$enc)
}

$repoRoot = (Resolve-Path ".").Path
$logsDir  = Join-Path $repoRoot "logs"
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null

$rcPath   = Join-Path $logsDir "daily_ops_onetap_rc.txt"
$errPath  = Join-Path $logsDir "daily_ops_onetap_err.txt"
$okJson   = Join-Path $logsDir "daily_ops_onetap_last_ok.json"

# ---- Softfail policy table (paper-locked ops) ----
# StepName => allowed non-zero rc codes that downgrade to warning + continue.
$SOFTFAIL = @{
  "ExportNvdaPaperliveResultsToday" = @(2)
  "NvdaGateScoreEvents"            = @(4)
  "GateScoreDailyBuild"            = @(2,4)
  "BlockGReady(NVDA)"              = @(2)
  "Phase6OneTap+Notion"            = @(2)  # Not ready is non-fatal in paper-locked DailyOps
}

function Invoke-Step {
  param(
    [Parameter(Mandatory=$true)][string]$StepName,
    [Parameter(Mandatory=$true)][string]$Path,
    [string[]]$Args=@()
  )
  Write-Host ("[DAILY-OPS] -> {0}" -f $StepName)
  $p = $Path
  if(-not [System.IO.Path]::IsPathRooted($p)){ $p = Join-Path $repoRoot $p }
  if(-not (Test-Path -LiteralPath $p)){ throw "Missing script: $p" }
  & powershell -NoProfile -ExecutionPolicy Bypass -File $p @Args
  $rc = $LASTEXITCODE
  if($rc -eq 0){ return 0 }
  $allow = @()
  if($SOFTFAIL.ContainsKey($StepName)){ $allow = @($SOFTFAIL[$StepName]) }
  if($allow -contains $rc){
    Write-Host ("[DAILY-OPS] {0}: SOFTFAIL rc={1} -- continuing (paper locked; live remains fail-closed)" -f $StepName,$rc) -ForegroundColor Yellow
    return $rc
  }
  throw ("DAILY_OPS_FAIL: {0} rc={1} file={2}" -f $StepName,$rc,$p)
}
# ---- end softfail policy table ----


# ---- HARD SAFETY: paper only ----
$env:HAT_IS_PAPER="1"
$env:HAT_LIVE_DISABLED="1"
Remove-Item Env:HAT_CONFIRM_LIVE -ErrorAction SilentlyContinue

# ---- ENV CLEAN (must never inherit old experiments) ----
Remove-Item Env:HAT_LOGS_DIR -ErrorAction SilentlyContinue
Remove-Item Env:HAT_BLOCKG_STATUS_PATH -ErrorAction SilentlyContinue
Remove-Item Env:HAT_BLOCKG_BUILT_ONCE -ErrorAction SilentlyContinue
Remove-Item Env:HAT_BLOCKG_QUIET -ErrorAction SilentlyContinue

# Repo-local pytest basetemp to avoid pytest-of-* lock spam
$pytestTmp = Join-Path $logsDir "_pytest_tmp"
New-Item -ItemType Directory -Force -Path $pytestTmp | Out-Null

# ---- MAIN ----
$asOf = (Get-Date).ToString("yyyy-MM-dd")
try {
  # 0) Pytest first (can clobber logs; must run before evidence build)
  try{
    $env:PYTEST_ADDOPTS = "--basetemp `"$pytestTmp`""
    Invoke-Step -Path ".\tools\pytest.ps1" -Args @("-q") -StepName "Pytest(anti-hijack)"
  } finally {
    Remove-Item Env:PYTEST_ADDOPTS -ErrorAction SilentlyContinue
  }

  # 1) Evidence rebuild
  Invoke-Step -Path ".\tools\Run-Phase23HealthDaily.ps1" -StepName "Phase23HealthDaily"
  Invoke-Step -Path ".\tools\Export-Phase5EvHardVetoDailySnapshot.ps1" -StepName "EvHardDailySnapshot"
  Invoke-Step -Path ".\tools\Run-EvHardVetoDaily.ps1" -StepName "EvHardVetoDaily"

  # Phase4 + stamp (force basetemp again to avoid temp lock spam)
  try{
    $env:PYTEST_ADDOPTS = "--basetemp `"$pytestTmp`""
    Invoke-Step -Path ".\tools\Run-Phase4Validation.ps1" -StepName "Phase4Validation"
    Invoke-Step -Path ".\tools\Run-Phase4Stamp.ps1" -StepName "Phase4Stamp"
  Invoke-Step -Path ".\tools\Build-EvHardEvidenceRaw.ps1" -StepName "EvHardEvidenceRaw"  } finally {
    Remove-Item Env:PYTEST_ADDOPTS -ErrorAction SilentlyContinue
  }

    # 1.5) Rebuild NVDA GateScore events (today-only; may be absent on non-trading / not-running days)
    # 1.45) Export NVDA today results from canonical trades.jsonl (fail-closed if none)
  Write-Host "[DAILY-OPS] -> ExportNvdaPaperliveResultsToday(from trades.jsonl)"
  $pExp = Join-Path $repoRoot ".\tools\Export-NvdaPaperliveResultsToday.ps1"
  & powershell -NoProfile -ExecutionPolicy Bypass -File $pExp
  $rcExp = $LASTEXITCODE
  if($rcExp -eq 0){
    # ok
  } elseif($rcExp -eq 2){
    Write-Host "[DAILY-OPS] ExportNvdaPaperliveResultsToday: NO_TODAY_ROWS (rc=2) -- continuing (paper locked)" -ForegroundColor Yellow
  } else {
    throw ("DAILY_OPS_FAIL: ExportNvdaPaperliveResultsToday rc={0} file={1}" -f $rcExp,$pExp)
  }
Write-Host "[DAILY-OPS] -> NvdaGateScoreEvents(today-only)"
  $pEv = Join-Path $repoRoot ".\tools\Write-NvdaGateScoreEventsFromPaperlive.ps1"
  & powershell -NoProfile -ExecutionPolicy Bypass -File $pEv -Mode rewrite -MinEvents 10 -OutPath (Join-Path $logsDir "nvda_gatescore_events.jsonl")
  $rcEv = $LASTEXITCODE
  if($rcEv -eq 0){
    # ok
  } elseif($rcEv -eq 4){
    Write-Host "[DAILY-OPS] NvdaGateScoreEvents: NO_TODAY_ROWS (rc=4) -- continuing (paper locked)" -ForegroundColor Yellow
  } else {
    throw ("DAILY_OPS_FAIL: NvdaGateScoreEvents rc={0} file={1}" -f $rcEv,$pEv)
  }
Invoke-Step -Path ".\tools\Run-GateScoreDailySummary.ps1" -Args @("-Quiet") -StepName "GateScoreDailySummary"
  Write-Host "[DAILY-OPS] -> GateScoreDailyBuild"
  # GateScoreDailyBuild: paper-locked DailyOps is NVDA-only (portfolio mode elsewhere)
  $env:HAT_GS_REQUIRED_SYMBOLS = "NVDA"
  $pGs = Join-Path $repoRoot ".\tools\Run-GateScoreDailyBuild.ps1"
  & powershell -NoProfile -ExecutionPolicy Bypass -File $pGs
  Remove-Item Env:HAT_GS_REQUIRED_SYMBOLS -ErrorAction SilentlyContinue
  $rcGs = $LASTEXITCODE
  if($rcGs -eq 0){
    # ok
  } elseif($rcGs -eq 2 -or $rcGs -eq 4){
    Write-Host "[DAILY-OPS] GateScoreDailyBuild: NO_TODAY_ROWS (rc=$rcGs) -- continuing (paper locked; live remains fail-closed)" -ForegroundColor Yellow
  } else {
    throw ("DAILY_OPS_FAIL: GateScoreDailyBuild rc={0} file={1}" -f $rcGs,$pGs)
  }

  # 2) Build BlockG stub to canonical logs/ no matter what the builder does internally
  $env:HAT_BLOCKG_STATUS_PATH = (Join-Path $logsDir "blockg_status_stub.json")
  # 2) GateScore stamp (deterministic contract inputs; fail-closed)
  Invoke-Step -StepName "GateScoreStamp" -Path ".\tools\Build-GateScoreStamp.ps1"

  Invoke-Step -Path ".\tools\Build-BlockGStatusStub.ps1" -StepName "BuildBlockGStatusStub"

  # 3) Final contract check (must be after evidence build)
    # 3) Final contract check (must be after evidence build)
  Write-Host ("[DAILY-OPS] -> {0}" -f "BlockGReady(NVDA)")
  $pChk = Join-Path $repoRoot ".\tools\Check-BlockGReady.ps1"
  & powershell -NoProfile -ExecutionPolicy Bypass -File $pChk -Symbol "NVDA"
  $rcBlockG = $LASTEXITCODE

  if($rcBlockG -eq 0){
    # ok, continue
  } elseif($rcBlockG -eq 2){
    # FAIL-CLOSED but NON-FATAL for paper-locked daily ops (we still want intel + notion exports)
    Write-Host "[DAILY-OPS] BlockGReady(NVDA) = NOT READY (rc=2) -- continuing (paper locked)" -ForegroundColor Yellow
  } else {
    throw ("DAILY_OPS_FAIL: {0} rc={1} file={2}" -f "BlockGReady(NVDA)", $rcBlockG, $pChk)
  }

  # 4) Intel + Phase6
  Invoke-Step -StepName "IntelPipeline" -Path ".\tools\Run-IntelPipeline.ps1"
  Invoke-Step -StepName "Phase6OneTap+Notion" -Path ".\tools\Run-Phase6OneTap-Notion.ps1"

  # Success
  $ok = [ordered]@{ as_of_date=$asOf; ok=$true; mode="paper_locked"; ts_utc=(Get-Date).ToUniversalTime().ToString("o") } | ConvertTo-Json -Depth 5
  Write-Utf8NoBom -Path $okJson -Text $ok
  Write-Utf8NoBom -Path $rcPath -Text "0"
  if(Test-Path $errPath){ Remove-Item -LiteralPath $errPath -Force -ErrorAction SilentlyContinue }
  exit 0
}
catch {
  $msg = ($_ | Out-String).Trim()
  Write-Utf8NoBom -Path $errPath -Text $msg
  Write-Utf8NoBom -Path $rcPath -Text "2"
  Write-Host ("[DAILY-OPS] FAIL as_of={0} err={1}" -f $asOf,$msg) -ForegroundColor Red
  exit 2
}
finally {
  Remove-Item Env:HAT_BLOCKG_STATUS_PATH -ErrorAction SilentlyContinue
}
