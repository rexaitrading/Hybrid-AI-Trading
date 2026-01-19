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
    .\tools\Write-EvHardStatus.ps1 -Market $mk -Symbol $Symbol | Out-Host
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