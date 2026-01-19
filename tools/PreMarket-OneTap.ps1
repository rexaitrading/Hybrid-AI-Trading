[CmdletBinding()]
param(
  [switch]$ProducersOnly
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

# --- Step 0.5: NVDA events producer (today) ---
$nvdaToday = Test-Path '.\logs\nvda_phase5_paperlive_results_today.jsonl'
$writerOk = Test-Path '.\tools\Write-NvdaGateScoreEventsFromPaperlive.ps1'
if ($nvdaToday -and $writerOk) {
  Write-Host "`n[PREMARKET] Step 0.5: Write-NvdaGateScoreEventsFromPaperlive.ps1 (today rewrite)" -ForegroundColor Yellow
  & powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Write-NvdaGateScoreEventsFromPaperlive.ps1 -InputPath ".\logs\nvda_phase5_paperlive_results_today.jsonl" -OutPath ".\logs\nvda_gatescore_events.jsonl" -Mode rewrite -MinEvents 10 | Out-Host
} else {
  Write-Host "[PREMARKET] WARN: NVDA today paperlive file missing (or writer missing). GateScore may remain stale -> fail-closed." -ForegroundColor Yellow
}
# --- Step 1: Build GateScore summaries (expects events already present) ---
if (Test-Path '.\tools\Run-BuildGateScoreSummaries.ps1') {
  Write-Host "`n[PREMARKET] Step 1: Run-BuildGateScoreSummaries.ps1" -ForegroundColor Yellow
  .\tools\Run-BuildGateScoreSummaries.ps1
  if ($LASTEXITCODE -ne 0) { Write-Host "[PREMARKET] WARN: GateScore summaries not ready (fail-closed will apply downstream)." -ForegroundColor Yellow }
}

# --- Step 2: EV-hard raw evidence ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ snapshot ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ compute input ÃƒÂ¢Ã¢â‚¬Â Ã¢â‚¬â„¢ daily export (fail-closed) ---
if (Test-Path '.\tools\Build-EvHardEvidenceRaw.ps1') {
  Write-Host "`n[PREMARKET] Step 2a: Build-EvHardEvidenceRaw.ps1" -ForegroundColor Yellow
  .\tools\Build-EvHardEvidenceRaw.ps1 | Out-Host
}
if (Test-Path '.\tools\Build-EvHardSnapshot.ps1') {
  Write-Host "`n[PREMARKET] Step 2b: Build-EvHardSnapshot.ps1" -ForegroundColor Yellow
  .\tools\Build-EvHardSnapshot.ps1 | Out-Host
}
if (Test-Path '.\tools\Compute-Phase5EvHardSnapshotInput.ps1') {
  Write-Host "`n[PREMARKET] Step 2c: Compute-Phase5EvHardSnapshotInput.ps1" -ForegroundColor Yellow
  .\tools\Compute-Phase5EvHardSnapshotInput.ps1 -EvidencePath ".\logs\ev_hard_snapshot.json" | Out-Host
}
if (Test-Path '.\tools\Export-Phase5EvHardVetoDailySnapshot.ps1') {
  Write-Host "`n[PREMARKET] Step 2d: Export-Phase5EvHardVetoDailySnapshot.ps1" -ForegroundColor Yellow
  .\tools\Export-Phase5EvHardVetoDailySnapshot.ps1 | Out-Host
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
