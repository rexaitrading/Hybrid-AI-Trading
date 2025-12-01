[CmdletBinding()]
param(
    [switch]$SkipCsv
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

# Script lives under repoRoot\tools -> go one level up to repo root
$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

Write-Host "`n[PIPELINE] NVDA Phase-5 paper pipeline (live runner + CSV)" -ForegroundColor Cyan

# Python + PYTHONPATH
$env:PYTHONPATH = Join-Path $repoRoot 'src'
$PythonExe = '.\.venv\Scripts\python.exe'

if (-not (Test-Path $PythonExe)) {
    Write-Host "[ERROR] Python executable not found at $PythonExe" -ForegroundColor Red
    return
}

Write-Host "RepoRoot  = $repoRoot"
Write-Host "PythonExe = $PythonExe"
Write-Host "PYTHONPATH= $env:PYTHONPATH"

# --- Step 1: run NVDA Phase-5 live runner (IB paper) ------------------------
Write-Host "`n[STEP 1] Run nvda_phase5_live_runner.py (IB paper)" -ForegroundColor Cyan

& $PythonExe .\src\hybrid_ai_trading\runners\nvda_phase5_live_runner.py
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    Write-Host "[STEP 1] nvda_phase5_live_runner.py exited with code $exitCode" -ForegroundColor Red
    Write-Host "[PIPELINE] Aborting before CSV rebuild." -ForegroundColor Yellow
    return
}

Write-Host "[STEP 1] nvda_phase5_live_runner.py completed successfully." -ForegroundColor Green

# --- Step 1.5: backfill PnL stub into nvda_phase5_paperlive_results.jsonl -----
Write-Host "`n[STEP 1.5] Backfill NVDA Phase-5 live PnL stub (realized_pnl=0.0) into nvda_phase5_paperlive_results.jsonl" -ForegroundColor Cyan
.\tools\Backfill-NvdaPhase5LivePnlStub.ps1

# --- Step 2: rebuild CSV ------------------------------------------------------

# --- Step 2: rebuild NVDA Phase-5 paper CSV for Notion ----------------------
if (-not $SkipCsv) {
    Write-Host "`n[STEP 2] Rebuild NVDA Phase-5 paper CSV for Notion" -ForegroundColor Cyan

    & $PythonExe .\tools\nvda_phase5_paper_to_csv.py
    $exitCode = $LASTEXITCODE

    if ($exitCode -ne 0) {
        Write-Host "[STEP 2] nvda_phase5_paper_to_csv.py exited with code $exitCode" -ForegroundColor Red
        Write-Host "[PIPELINE] CSV step failed; check logs\nvda_phase5_paper_for_notion.csv manually." -ForegroundColor Yellow
        return
    }

    Write-Host "[STEP 2] nvda_phase5_paper_to_csv.py completed successfully." -ForegroundColor Green
} else {
    Write-Host "[STEP 2] SkipCsv switch set -> CSV rebuild skipped." -ForegroundColor Yellow
}

Write-Host "`n[PIPELINE] NVDA Phase-5 paper pipeline complete." -ForegroundColor Green