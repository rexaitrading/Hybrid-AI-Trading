[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

Write-Host "`n[PHASE5-SAFETY] Phase-5 Safety Snapshot RUN" -ForegroundColor Cyan
Write-Host "[PHASE5-SAFETY] RepoRoot = $repoRoot" -ForegroundColor DarkCyan

# 1) Build Block-G status stub (Phase-23 + EV-hard + GateScore)
if (Test-Path '.\tools\Build-BlockGStatusStub.ps1') {
    Write-Host "`n[PHASE5-SAFETY] Step 1: Build-BlockGStatusStub.ps1" -ForegroundColor Yellow
    .\tools\Build-BlockGStatusStub.ps1
} else {
    Write-Host "[PHASE5-SAFETY] ERROR: tools\Build-BlockGStatusStub.ps1 not found." -ForegroundColor Red
    exit 1
}

# 2) Build Phase-5 RunContext stub from Block-G contract
if (Test-Path '.\tools\Build-RunContextStub.ps1') {
    Write-Host "`n[PHASE5-SAFETY] Step 2: Build-RunContextStub.ps1" -ForegroundColor Yellow
    .\tools\Build-RunContextStub.ps1
} else {
    Write-Host "[PHASE5-SAFETY] ERROR: tools\Build-RunContextStub.ps1 not found." -ForegroundColor Red
    exit 1
}

# 3) Export RunContext to CSV (for Notion / reporting)
if (Test-Path '.\tools\Export-Phase5SafetyRunContextCsv.ps1') {
    Write-Host "`n[PHASE5-SAFETY] Step 3: Export-Phase5SafetyRunContextCsv.ps1" -ForegroundColor Yellow
    .\tools\Export-Phase5SafetyRunContextCsv.ps1
} else {
    Write-Host "[PHASE5-SAFETY] WARN: tools\Export-Phase5SafetyRunContextCsv.ps1 not found; skipping CSV export." -ForegroundColor Yellow
}

# 4) Show Phase-5 Safety State dashboard
if (Test-Path '.\tools\Show-Phase5SafetyState.ps1') {
    Write-Host "`n[PHASE5-SAFETY] Step 4: Show-Phase5SafetyState.ps1" -ForegroundColor Yellow
    .\tools\Show-Phase5SafetyState.ps1
    $exitCode = $LASTEXITCODE
} else {
    Write-Host "[PHASE5-SAFETY] WARN: tools\Show-Phase5SafetyState.ps1 not found; skipping dashboard." -ForegroundColor Yellow
    $exitCode = 0
}

Write-Host "`n[PHASE5-SAFETY] Phase-5 Safety Snapshot RUN complete." -ForegroundColor Cyan
exit $exitCode