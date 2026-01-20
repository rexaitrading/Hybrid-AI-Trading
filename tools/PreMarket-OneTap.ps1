[CmdletBinding()]
param(
  [switch]$ProducersOnly
  ,[ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "ALL"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

Write-Host "`n[PREMARKET] OneTap (REAL) - producers + daily contracts (FAIL-CLOSED)" -ForegroundColor Cyan
Write-Host "[PREMARKET] RepoRoot = $repoRoot" -ForegroundColor DarkCyan

# Ensure PYTHONPATH for python modules
$env:PYTHONPATH = Join-Path $repoRoot 'src'

# --- Step 0: Phase-2ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢5 validation (optional) ---
if (Test-Path '.\tools\Run-Phase2ToPhase5Validation.ps1') {
  Write-Host "`n[PREMARKET] Step 0: Run-Phase2ToPhase5Validation.ps1" -ForegroundColor Yellow
  .\tools\Run-Phase2ToPhase5Validation.ps1
  if ($LASTEXITCODE -ne 0) { Write-Host "[PREMARKET] ERROR: Phase2ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢5 validation failed." -ForegroundColor Red; exit $LASTEXITCODE }
}

# --- Step 0.5: NVDA events producer (per-market, fail-closed) ---
$mk = (($env:HAT_MARKET + "")).Trim()
if(-not $mk){ $mk = "US" }

# STEP_0_25_INTEL_PULSE_PERMARKET
# --- Step 0.25: Intel minimal pulse (per-market, deterministic) ---
if (Test-Path '.\tools\Run-IntelPipeline-Minimal.ps1') {
  Write-Host "`n[PREMARKET] Step 0.25: Run-IntelPipeline-Minimal.ps1 (market=$mk)" -ForegroundColor Yellow
  $oldHatMarket = ($env:HAT_MARKET + "")
  try {
    $env:HAT_MARKET = $mk
    .\tools\Run-IntelPipeline-Minimal.ps1 | Out-Host
    if($LASTEXITCODE -ne 0){ Write-Host "[PREMARKET] WARN: intel minimal pulse returned nonzero (fail-closed downstream may apply)." -ForegroundColor Yellow }
  } finally {
    if($oldHatMarket -ne $null){ $env:HAT_MARKET = $oldHatMarket } else { Remove-Item Env:\HAT_MARKET -ErrorAction SilentlyContinue }
  }
} else {
  Write-Host "[PREMARKET] WARN: Run-IntelPipeline-Minimal.ps1 missing -> per-market risk_pulse may be stale; Block-G may fall back to global." -ForegroundColor Yellow
}


$writerOk = Test-Path '.\tools\Write-GateScoreEvents-PerMarket.ps1'
if ($writerOk) {
  Write-Host "`n[PREMARKET] Step 0.5: Write-GateScoreEvents-PerMarket.ps1 (NVDA rewrite, market=$mk)" -ForegroundColor Yellow
  & powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Write-GateScoreEvents-PerMarket.ps1 -Market $mk -Symbol "NVDA" -Mode "rewrite" -MinEvents 10 | Out-Host
} else {
  Write-Host "[PREMARKET] WARN: per-market GateScore writer missing. GateScore may remain stale -> fail-closed." -ForegroundColor Yellow
}
# --- Step 1: Build GateScore summaries (expects events already present) ---
if (Test-Path '.\tools\Run-BuildGateScoreSummaries.ps1') {
  Write-Host "`n[PREMARKET] Step 1: Run-BuildGateScoreSummaries.ps1" -ForegroundColor Yellow
  .\tools\Run-BuildGateScoreSummaries.ps1
  if ($LASTEXITCODE -ne 0) { Write-Host "[PREMARKET] WARN: GateScore summaries not ready (fail-closed will apply downstream)." -ForegroundColor Yellow }
}

# --- Step 1.5: Phase23 + Phase4 stamps (per-market, fail-closed for LIVE; diagnostics for PAPER/PAPERLIVE) ---
$psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
$mk = (($env:HAT_MARKET + "")).Trim().ToUpperInvariant()
if(-not $mk){ $mk = "US" }

# Ensure HAT_LOGS_DIR is correct for this market (prevents cross-market bleed)
$oldHatLogsDir = ($env:HAT_LOGS_DIR + "")
try {
  $g = Join-Path $repoRoot "tools\Get-MarketLogRoot.ps1"
  if(-not (Test-Path -LiteralPath $g)){ throw "[FAIL-CLOSED] missing tools\Get-MarketLogRoot.ps1" }
  $ld = (& $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $g -Market $mk 2>$null | Out-String).Trim()
  if(-not $ld){ throw "[FAIL-CLOSED] Get-MarketLogRoot empty for market=" + $mk }
  $env:HAT_LOGS_DIR = $ld
  New-Item -ItemType Directory -Force -Path $ld | Out-Null

  # Phase23 heartbeat (writes logs\<Market>\phase23_health_daily.csv)
  if (Test-Path '.\tools\Run-Phase23HealthDaily.ps1') {
    Write-Host "`n[PREMARKET] Step 1.5a: Run-Phase23HealthDaily.ps1 (market=$mk logsDir=$ld)" -ForegroundColor Yellow
    .\tools\Run-Phase23HealthDaily.ps1 -Market $mk -Symbol $Symbol | Out-Host

  if (Test-Path '.\tools\Write-Phase23Status.ps1') {
    Write-Host "`n[PREMARKET] Step 1.5a2: Write-Phase23Status.ps1 (market=$mk symbol=$Symbol)" -ForegroundColor Yellow
    .\tools\Write-Phase23Status.ps1 -Market $mk -Symbol $Symbol | Out-Host
  } else {
    Write-Host "[PREMARKET] WARN: Write-Phase23Status.ps1 missing -> phase23_status.json may remain stale (fail-closed downstream)" -ForegroundColor DarkYellow
  }
  } else {
    Write-Host "[PREMARKET] WARN: Run-Phase23HealthDaily.ps1 missing -> Phase23 may remain stale (fail-closed downstream)." -ForegroundColor Yellow
  }

  # Phase4 stamp (fast compile sweep + canonical per-market phase4_validation_passed.json)
  if (Test-Path '.\tools\Run-Phase4Stamp.ps1') {
    Write-Host "`n[PREMARKET] Step 1.5b: Run-Phase4Stamp.ps1 (market=$mk symbol=$Symbol)" -ForegroundColor Yellow
    .\tools\Run-Phase4Stamp.ps1 -Market $mk -Symbol $Symbol | Out-Host
  } else {
    Write-Host "[PREMARKET] WARN: Run-Phase4Stamp.ps1 missing -> Phase4 may remain stale (fail-closed downstream)." -ForegroundColor Yellow
  }

  # Phase4 status JSON (reads per-market phase4_validation_passed.json)
  if (Test-Path '.\tools\Write-Phase4Status.ps1') {
    Write-Host "`n[PREMARKET] Step 1.5c: Write-Phase4Status.ps1 (market=$mk logsDir=$ld)" -ForegroundColor Yellow
    .\tools\Write-Phase4Status.ps1 -Market $mk | Out-Host
  } else {
    Write-Host "[PREMARKET] WARN: Write-Phase4Status.ps1 missing -> Phase4 status may remain stale (fail-closed downstream)." -ForegroundColor Yellow
  }

} finally {
  if($oldHatLogsDir -ne $null){ $env:HAT_LOGS_DIR = $oldHatLogsDir } else { Remove-Item Env:\HAT_LOGS_DIR -ErrorAction SilentlyContinue }
}
# --- Step 1.6: A2 artifacts (per-market): DependencyRisk + RiskGuard + RegimeActions + MarketDNA ---
$psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
$mk = (($env:HAT_MARKET + "")).Trim().ToUpperInvariant()
if(-not $mk){ $mk = "US" }

$oldHatLogsDir = ($env:HAT_LOGS_DIR + "")
try {
  $g = Join-Path $repoRoot "tools\Get-MarketLogRoot.ps1"
  if(-not (Test-Path -LiteralPath $g)){ throw "[FAIL-CLOSED] missing tools\Get-MarketLogRoot.ps1" }
  $ld = (& $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $g -Market $mk 2>$null | Out-String).Trim()
  if(-not $ld){ throw "[FAIL-CLOSED] Get-MarketLogRoot empty for market=" + $mk }
  $env:HAT_LOGS_DIR = $ld
  New-Item -ItemType Directory -Force -Path $ld | Out-Null

  if(Test-Path '.\tools\Build-DependencyRisk.ps1'){
    Write-Host "`n[PREMARKET] Step 1.6a: Build-DependencyRisk.ps1 (market=$mk)" -ForegroundColor Yellow
    .\tools\Build-DependencyRisk.ps1 -Market $mk | Out-Host
  }

  if(Test-Path '.\tools\Build-RiskGuardStatus.ps1'){
    Write-Host "`n[PREMARKET] Step 1.6b: Build-RiskGuardStatus.ps1 (market=$mk)" -ForegroundColor Yellow
    .\tools\Build-RiskGuardStatus.ps1 -Market $mk | Out-Host
  }

  if(Test-Path '.\tools\Build-RegimeActions.ps1'){
    Write-Host "`n[PREMARKET] Step 1.6c: Build-RegimeActions.ps1 (market=$mk)" -ForegroundColor Yellow
    # ADAPTER_SYMBOL_ALL_REGIMEACTIONS_DEF
    $symRA = $Symbol
    if((($symRA + "")).Trim().ToUpperInvariant() -eq "ALL"){ $symRA = "NVDA" }
    # ADAPTER_SYMBOL_ALL_MARKETSELECTOR_DEF
    $symMS = $Symbol
    if((($symMS + "")).Trim().ToUpperInvariant() -eq "ALL"){ $symMS = "NVDA" }
    .\tools\Build-RegimeActions.ps1 -Market $mk -Symbol $symRA | Out-Host

   if(Test-Path '.\tools\Build-MarketSelector.ps1'){
     Write-Host "`n[PREMARKET] Step 1.6e: Build-MarketSelector.ps1 (market=$mk)" -ForegroundColor Yellow
    # STEP_1_6E0_MARKET_ENABLEMENT_BEFORE_SELECTOR
    if(Test-Path '.\tools\Write-MarketEnablement.ps1'){
      Write-Host "`n[PREMARKET] Step 1.6e0: Write-MarketEnablement.ps1 (market=$mk)" -ForegroundColor Yellow
      .\tools\Write-MarketEnablement.ps1 -Market $mk | Out-Host
    }

     .\tools\Build-MarketSelector.ps1 -Market $mk -Symbol $symMS | Out-Host
   } else {
     Write-Host "[PREMARKET] WARN: Build-MarketSelector.ps1 missing -> selector receipt absent (audit-only)" -ForegroundColor Yellow
   }

  } else {
    Write-Host "[PREMARKET] WARN: Build-RegimeActions.ps1 missing -> regime_actions.json stays missing (fail-closed)" -ForegroundColor Yellow
  }

  if(Test-Path '.\tools\Build-MarketDNA.ps1'){
    Write-Host "`n[PREMARKET] Step 1.6d: Build-MarketDNA.ps1 (market=$mk)" -ForegroundColor Yellow
    .\tools\Build-MarketDNA.ps1 -Market $mk | Out-Host
  }

  # STEP_1_6F_EDGE_VALIDITY
  if(Test-Path '.\tools\Build-EdgeValidity.ps1'){
    Write-Host "`n[PREMARKET] Step 1.6f: Build-EdgeValidity.ps1 (market=$mk)" -ForegroundColor Yellow
    .\tools\Build-EdgeValidity.ps1 -Market $mk | Out-Host
  } else {
    Write-Host "[PREMARKET] WARN: Build-EdgeValidity.ps1 missing -> edge_validity.json may stay stale (fail-closed)." -ForegroundColor Yellow
  }


  # STEP_1_6G_MARKET_ENABLEMENT (REMOVED)
  # NOTE: enablement receipt is refreshed at Step 1.6e0 before selector; no duplicate write here.


} finally {
  if($oldHatLogsDir -ne $null){ $env:HAT_LOGS_DIR = $oldHatLogsDir } else { Remove-Item Env:\HAT_LOGS_DIR -ErrorAction SilentlyContinue }
}


  # STEP_1_6H_MARKET_MODULE_POLICY
  if(Test-Path '.\tools\Write-MarketModulePolicy.ps1'){
    Write-Host "`n[PREMARKET] Step 1.6h: Write-MarketModulePolicy.ps1 (market=$mk)" -ForegroundColor Yellow
    .\tools\Write-MarketModulePolicy.ps1 -Market $mk | Out-Host
  } else {
    Write-Host "[PREMARKET] WARN: Write-MarketModulePolicy.ps1 missing -> policy receipt absent (audit-only)." -ForegroundColor Yellow
  }

# --- Step 1.7: Crisis + Crashmode receipts (per-market, NOOP; no flatten action) ---
$psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
$mk = (($env:HAT_MARKET + "")).Trim().ToUpperInvariant()
if(-not $mk){ $mk = "US" }

$oldHatLogsDir = ($env:HAT_LOGS_DIR + "")
try {
  $g = Join-Path $repoRoot "tools\Get-MarketLogRoot.ps1"
  if(-not (Test-Path -LiteralPath $g)){ throw "[FAIL-CLOSED] missing tools\Get-MarketLogRoot.ps1" }
  $ld = (& $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $g -Market $mk 2>$null | Out-String).Trim()
  if(-not $ld){ throw "[FAIL-CLOSED] Get-MarketLogRoot empty for market=" + $mk }
  $env:HAT_LOGS_DIR = $ld
  New-Item -ItemType Directory -Force -Path $ld | Out-Null

  # (A) NOOP crashmode flatten status (receipt only; no flatten executed)
  $cmPath = Join-Path $ld "crashmode_flatten_status.json"
  $tsUtc = (Get-Date).ToUniversalTime().ToString("o")

  $asof = ""
  try {
    $rcRaw = (& (Join-Path $repoRoot "tools\Resolve-RunContext.ps1") -Market $mk -Symbol $Symbol | Out-String).Trim()
    $ix0=$rcRaw.IndexOf("{"); $ix1=$rcRaw.LastIndexOf("}")
    if($ix0 -ge 0 -and $ix1 -gt $ix0){
      $rc = ($rcRaw.Substring($ix0, ($ix1-$ix0+1)) | ConvertFrom-Json)
      $asof = ([string]$rc.as_of_date).Trim()
      if($asof.Length -gt 10){ $asof = $asof.Substring(0,10) }
    }
  } catch { $asof = "" }
  if(-not $asof){ $asof = (Get-Date).ToString("yyyy-MM-dd") }

  $cm = [ordered]@{
    kind="crashmode_flatten_status"
    ts_utc=$tsUtc
    as_of_date=$asof
    ok=$true
    ok_today=$true
    exit_code=0
    reason="nonlive_noop_no_crisis"
    note="Receipt only. No flatten executed."
  }
  [System.IO.File]::WriteAllText($cmPath, (($cm | ConvertTo-Json -Depth 6) + "`n"), (New-Object System.Text.UTF8Encoding($false)))
  Write-Host ("[CRASHMODE] wrote " + $cmPath + " ok=true (NOOP)") -ForegroundColor Yellow

  # (B) Crisis regime status (market-aware; uses its own policy)
  if(Test-Path '.\tools\Write-CrisisRegimeStatus.ps1'){
    Write-Host "`n[PREMARKET] Step 1.7b: Write-CrisisRegimeStatus.ps1 (market=$mk symbol=$Symbol)" -ForegroundColor Yellow
    .\tools\Write-CrisisRegimeStatus.ps1 -Market $mk -Symbol $Symbol | Out-Host
  } else {
    Write-Host "[PREMARKET] WARN: Write-CrisisRegimeStatus.ps1 missing -> crisis_ok_today may stay false" -ForegroundColor Yellow
  }

} finally {
  if($oldHatLogsDir -ne $null){ $env:HAT_LOGS_DIR = $oldHatLogsDir } else { Remove-Item Env:\HAT_LOGS_DIR -ErrorAction SilentlyContinue }
}
# --- Step 2: EV-hard raw evidence -> snapshot -> compute input -> daily export -> A2 status (per-market, fail-closed) ---
# FS-truth: always derive HAT_LOGS_DIR from Get-MarketLogRoot for current HAT_MARKET (prevents cross-market bleed)
$psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
$mk = (($env:HAT_MARKET + "")).Trim().ToUpperInvariant()
if(-not $mk){ $mk = "US" }

$oldHatLogsDir = ($env:HAT_LOGS_DIR + "")
try {
  $g = Join-Path $repoRoot "tools\Get-MarketLogRoot.ps1"
  if(-not (Test-Path -LiteralPath $g)){ throw "[FAIL-CLOSED] missing tools\Get-MarketLogRoot.ps1" }
  $ld = (& $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $g -Market $mk 2>$null | Out-String).Trim()
  if(-not $ld){ throw "[FAIL-CLOSED] Get-MarketLogRoot empty for market=" + $mk }
  $env:HAT_LOGS_DIR = $ld
  New-Item -ItemType Directory -Force -Path $ld | Out-Null

  $evSnap = Join-Path $ld "ev_hard_snapshot.json"

  if (Test-Path '.\tools\Build-EvHardEvidenceRaw.ps1') {
    Write-Host "`n[PREMARKET] Step 2a: Build-EvHardEvidenceRaw.ps1 (market=$mk logsDir=$ld)" -ForegroundColor Yellow
    .\tools\Build-EvHardEvidenceRaw.ps1 | Out-Host
  }
  if (Test-Path '.\tools\Build-EvHardSnapshot.ps1') {
    Write-Host "`n[PREMARKET] Step 2b: Build-EvHardSnapshot.ps1 (market=$mk logsDir=$ld)" -ForegroundColor Yellow
    .\tools\Build-EvHardSnapshot.ps1 | Out-Host
  }
  if (Test-Path '.\tools\Compute-Phase5EvHardSnapshotInput.ps1') {
    Write-Host "`n[PREMARKET] Step 2c: Compute-Phase5EvHardSnapshotInput.ps1 (EvidencePath=$evSnap)" -ForegroundColor Yellow
    .\tools\Compute-Phase5EvHardSnapshotInput.ps1 -EvidencePath $evSnap | Out-Host
  }
  if (Test-Path '.\tools\Export-Phase5EvHardVetoDailySnapshot.ps1') {
    Write-Host "`n[PREMARKET] Step 2d: Export-Phase5EvHardVetoDailySnapshot.ps1 (market=$mk logsDir=$ld)" -ForegroundColor Yellow
    .\tools\Export-Phase5EvHardVetoDailySnapshot.ps1 | Out-Host
  }

  # --- Step 2e: [A2] refresh ev_hard_status.json (per-market) ---
  if (Test-Path '.\tools\Write-EvHardStatus.ps1') {
    Write-Host "`n[PREMARKET] Step 2e: Write-EvHardStatus.ps1 (market=$mk symbol=$Symbol)" -ForegroundColor Yellow
    # ADAPTER_SYMBOL_ALL_EVHSTATUS_DEF
    $symEHS = $Symbol
    if((($symEHS + "")).Trim().ToUpperInvariant() -eq "ALL"){ $symEHS = "NVDA" }
    .\tools\Write-EvHardStatus.ps1 -Market $mk -Symbol $symEHS | Out-Host
  } else {
    Write-Host "[PREMARKET] WARN: Write-EvHardStatus.ps1 missing -> ev_hard_status.json may stay stale (fail-closed downstream)." -ForegroundColor Yellow
  }

} finally {
  if($oldHatLogsDir -ne $null){ $env:HAT_LOGS_DIR = $oldHatLogsDir } else { Remove-Item Env:\HAT_LOGS_DIR -ErrorAction SilentlyContinue }
}
# --- Step 3: Build Block-G contract (single source) ---
if (-not (Test-Path '.\tools\Build-BlockGStatusStub.ps1')) {
  Write-Host "[PREMARKET] ERROR: Build-BlockGStatusStub.ps1 missing -> cannot proceed." -ForegroundColor Red
  exit 1
}
Write-Host "`n[PREMARKET] Step 3: Build-BlockGStatusStub.ps1" -ForegroundColor Yellow
.\tools\Build-BlockGStatusStub.ps1 -Market $env:HAT_MARKET -Symbol $Symbol | Out-Host

# --- Step 4: Optional ProducersOnly quick exit ---
if ($ProducersOnly) {
  Write-Host "`n[PREMARKET] ProducersOnly=TRUE => producers complete; no arming attempted." -ForegroundColor Cyan
  exit 0
}

# --- Step 5: DO NOT ARM LIVE HERE ---
Write-Host "`n[PREMARKET] NOTE: PreMarket-OneTap does not arm live/paper orders." -ForegroundColor DarkYellow
Write-Host "[PREMARKET] Use tools\Run-PreMarketOneTapGatedNvda.ps1 (Block-G gated wrapper) for any arming." -ForegroundColor DarkYellow
exit 0
