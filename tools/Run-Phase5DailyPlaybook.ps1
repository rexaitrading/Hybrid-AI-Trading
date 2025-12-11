[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

Write-Host "`n[PHASE5-PLAYBOOK] Phase-5 Daily Playbook RUN" -ForegroundColor Cyan
Write-Host "[PHASE5-PLAYBOOK] RepoRoot = $repoRoot" -ForegroundColor DarkCyan

# 0) Safety snapshot (Block-G + RunContext + CSV + dashboard)
$runSnapshot = Join-Path $repoRoot "tools\Run-Phase5SafetySnapshot.ps1"
if (-not (Test-Path $runSnapshot)) {
    Write-Host "[PHASE5-PLAYBOOK] ERROR: Run-Phase5SafetySnapshot.ps1 not found at $runSnapshot" -ForegroundColor Red
    exit 1
}
Write-Host "`n[PHASE5-PLAYBOOK] Step 0: Run-Phase5SafetySnapshot.ps1" -ForegroundColor Yellow
& $runSnapshot
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# 1) Phase-2→5 validation slice
$phase2to5 = Join-Path $repoRoot "tools\Run-Phase2ToPhase5Validation.ps1"
if (Test-Path $phase2to5) {
    Write-Host "`n[PHASE5-PLAYBOOK] Step 1: Run-Phase2ToPhase5Validation.ps1" -ForegroundColor Yellow
    & $phase2to5
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "[PHASE5-PLAYBOOK] WARN: Run-Phase2ToPhase5Validation.ps1 not found; skipping Phase-2→5 slice." -ForegroundColor Yellow
}

# 2) GateScore daily pipeline
$phase3Daily = Join-Path $repoRoot "tools\Run-Phase3GateScoreDaily.ps1"
if (Test-Path $phase3Daily) {
    Write-Host "`n[PHASE5-PLAYBOOK] Step 2: Run-Phase3GateScoreDaily.ps1" -ForegroundColor Yellow
    & $phase3Daily
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "[PHASE5-PLAYBOOK] WARN: Run-Phase3GateScoreDaily.ps1 not found; skipping GateScore daily." -ForegroundColor Yellow
}

# 3) NVDA Block-G readiness checklist (no live orders, just readiness)
$blockgReadiness = Join-Path $repoRoot "tools\Run-BlockGReadiness.ps1"
if (Test-Path $blockgReadiness) {
    Write-Host "`n[PHASE5-PLAYBOOK] Step 3: Run-BlockGReadiness.ps1" -ForegroundColor Yellow
    & $blockgReadiness
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "[PHASE5-PLAYBOOK] WARN: Run-BlockGReadiness.ps1 not found; skipping Block-G readiness checklist." -ForegroundColor Yellow
}

# 4) Final safety dashboard
$showSafety = Join-Path $repoRoot "tools\Show-Phase5SafetyState.ps1"
if (Test-Path $showSafety) {
    Write-Host "`n[PHASE5-PLAYBOOK] Step 4: Show-Phase5SafetyState.ps1" -ForegroundColor Yellow
    & $showSafety
}

Write-Host "`n[PHASE5-PLAYBOOK] Phase-5 Daily Playbook RUN complete." -ForegroundColor Cyan
exit 0