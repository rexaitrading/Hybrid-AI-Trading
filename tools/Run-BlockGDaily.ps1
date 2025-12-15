Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Step([string]$Name, [scriptblock]$Action) {
  Write-Host ("`n[BLOCKG-DAILY] {0}" -f $Name) -ForegroundColor Cyan
  & $Action
  Write-Host ("[BLOCKG-DAILY] OK: {0}" -f $Name) -ForegroundColor Green
}

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$logs = Join-Path $repoRoot "logs"
$phase23 = Join-Path $logs "phase23_health_daily.csv"
$evhard  = Join-Path $logs "phase5_ev_hard_veto_daily.csv"
$gs      = Join-Path $logs "gatescore_daily_summary.csv"
$phase4  = Join-Path $logs "phase4_validation_passed.json"
$contract= Join-Path $logs "blockg_status_stub.json"

function Assert-Exists([string]$p) {
  if (-not (Test-Path $p)) { throw "[BLOCKG-DAILY] Missing expected output: $p" }
}

Write-Host "[BLOCKG-DAILY] RepoRoot=$repoRoot" -ForegroundColor Yellow
Write-Host "[BLOCKG-DAILY] Logs=$logs" -ForegroundColor Yellow

# 1) Phase-2/3 health daily
Step "Phase23 health daily -> logs\phase23_health_daily.csv" {
  powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Build-Phase23HealthDaily.ps1
}
Assert-Exists $phase23

# 2) EV-hard veto daily
Step "EV-hard veto daily -> logs\phase5_ev_hard_veto_daily.csv" {
  powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Export-Phase5EvHardVetoDaily.ps1
}
Assert-Exists $evhard


# 2.5) GateScore NVDA events (input for daily summary)
Step "GateScore NVDA events -> logs\nvda_gatescore_events.jsonl" {
  powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Write-NvdaGateScoreEventsFromTrades.ps1
}

# 2.6) Phase-3 GateScore REAL producer (must generate nvda_gatescore_events.jsonl or nvda_gatescore_samples.csv)
Step "Phase-3 GateScore REAL producer -> logs\\nvda_gatescore_events.jsonl / nvda_gatescore_samples.csv" {
  if (Test-Path .\tools\Run-Phase3GateScoreDaily.ps1) {
    powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Run-Phase3GateScoreDaily.ps1
  } elseif (Test-Path .\tools\Run-GateScoreDailySuite.ps1) {
    powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Run-GateScoreDailySuite.ps1
  } else {
    Write-Host "[GATESCORE] WARN: no Phase-3 GateScore runner found; remain fail-closed." -ForegroundColor Yellow
  }
}

# Validate GateScore inputs exist (fail-closed; do not throw)
$gsInputs = @(
  (Join-Path $logs "nvda_gatescore_events.jsonl"),
  (Join-Path $logs "nvda_gatescore_samples.csv"),
  (Join-Path $logs "gatescore_events.jsonl"),
  (Join-Path $logs "gatescore_samples.csv")
)
$hasGs = $false
foreach($p in $gsInputs){ if(Test-Path $p){ $hasGs = $true; break } }
if (-not $hasGs) { Write-Host "[GATESCORE] NO REAL INPUT produced; daily summary will remain header-only (NO-GO)." -ForegroundColor Yellow }

# 2.55) GateScore NVDA samples (REAL producer target)
Step "GateScore NVDA samples -> logs\nvda_gatescore_samples.csv" {
  powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Write-NvdaGateScoreSamplesFromReplay.ps1
}
# 3) GateScore daily summary
Step "GateScore daily summary -> logs\gatescore_daily_summary.csv" {
  powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Build-GateScoreDailySummary.ps1
}
Assert-Exists $gs

# 4) Phase-4 validation stamp
Step "Phase-4 validation stamp -> logs\phase4_validation_passed.json" {
  powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Run-Phase4Validation.ps1
}
Assert-Exists $phase4

# 5) Build contract JSON
Step "Build BlockG contract -> logs\blockg_status_stub.json" {
  powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Build-BlockGStatusStub.ps1
}
Assert-Exists $contract

# 6) Check readiness (single source of truth)
Step "Check-BlockGReady (NVDA)" {
  powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Check-BlockGReady.ps1 -Symbol NVDA
  if ($LASTEXITCODE -ne 0) { Write-Host "[BLOCKG-DAILY] NO-GO: NVDA not ready (exit=$LASTEXITCODE)" -ForegroundColor Yellow }
}

Write-Host "`n[BLOCKG-DAILY] DONE" -ForegroundColor Green

