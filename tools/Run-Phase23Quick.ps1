[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

Write-Host "[PHASE23] Phase-2/3 quick diagnostics RUN" -ForegroundColor Cyan
Write-Host "[PHASE23] RepoRoot = $repoRoot" -ForegroundColor DarkCyan

# Step 1: Phase-2 micro snapshot (SPY/QQQ micro + cost)
$phase2Snap = Join-Path $repoRoot "tools\Run-Phase2MicroSnapshot.ps1"
if (Test-Path $phase2Snap) {
    Write-Host "`n[PHASE23] Step 1: Run-Phase2MicroSnapshot.ps1" -ForegroundColor Yellow
    & $phase2Snap
    $code = $LASTEXITCODE
    Write-Host "[PHASE23] Run-Phase2MicroSnapshot.ps1 exit code = $code" -ForegroundColor DarkCyan
} else {
    Write-Host "[PHASE23] WARN: Run-Phase2MicroSnapshot.ps1 not found at $phase2Snap" -ForegroundColor Yellow
}

# Step 2: GateScore daily pipeline (NVDA)
$phase3Daily = Join-Path $repoRoot "tools\Run-Phase3GateScoreDaily.ps1"
if (Test-Path $phase3Daily) {
    Write-Host "`n[PHASE23] Step 2: Run-Phase3GateScoreDaily.ps1" -ForegroundColor Yellow
    & $phase3Daily
    $code = $LASTEXITCODE
    Write-Host "[PHASE23] Run-Phase3GateScoreDaily.ps1 exit code = $code" -ForegroundColor DarkCyan
} else {
    Write-Host "[PHASE23] WARN: Run-Phase3GateScoreDaily.ps1 not found at $phase3Daily" -ForegroundColor Yellow
}

Write-Host "`n[PHASE23] Phase-2/3 quick diagnostics complete (snapshot stub)." -ForegroundColor Green
exit 0