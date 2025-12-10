[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $PSCommandPath
$repoRoot  = Split-Path -Parent $scriptDir

if (-not (Test-Path $repoRoot)) {
    throw "[PHASE3] Repo root not found from script path: $repoRoot"
}

Push-Location $repoRoot
try {
    Write-Host "`n[PHASE3] GateScore daily pipeline starting..." -ForegroundColor Cyan
    Write-Host "[PHASE3] RepoRoot = $repoRoot" -ForegroundColor DarkCyan

    # Step 1: Run GateScore daily suite / smoke
    if (Test-Path '.\tools\Run-GateScoreDailySuite.ps1') {
        Write-Host "`n[PHASE3] Running Run-GateScoreDailySuite.ps1..." -ForegroundColor Yellow
        .\tools\Run-GateScoreDailySuite.ps1
    } elseif (Test-Path '.\tools\Run-GateScoreSmoke.ps1') {
        Write-Host "`n[PHASE3] Running Run-GateScoreSmoke.ps1..." -ForegroundColor Yellow
        .\tools\Run-GateScoreSmoke.ps1
    } else {
        Write-Host "[WARN] No GateScore daily/smoke script found." -ForegroundColor Yellow
    }

    # Step 2: Refresh GateScore daily summary CSV
    if (Test-Path '.\tools\Build-GateScoreDailySummary.ps1') {
        Write-Host "`n[PHASE3] Building GateScore daily summary..." -ForegroundColor Yellow
        .\tools\Build-GateScoreDailySummary.ps1
    } else {
        Write-Host "[WARN] Build-GateScoreDailySummary.ps1 not found; skipping summary build." -ForegroundColor Yellow
    }

    # Step 3: Export GateScore + PnL to Notion
    if (Test-Path '.\tools\Run-ExportNvdaGateScoreForNotion.ps1') {
        Write-Host "`n[PHASE3] Exporting GateScore vs PnL for NVDA to Notion..." -ForegroundColor Yellow
        .\tools\Run-ExportNvdaGateScoreForNotion.ps1
    } else {
        Write-Host "[WARN] Run-ExportNvdaGateScoreForNotion.ps1 not found; skipping Notion export." -ForegroundColor Yellow
    }

    Write-Host "`n[PHASE3] GateScore daily pipeline complete." -ForegroundColor Cyan
}
finally {
    Pop-Location
}