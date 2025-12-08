[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

# Script lives under repoRoot\tools -> go one level up to repo root
$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

Write-Host "`n[PIPELINE] NVDA Phase-5 paper pipeline (no-IBG runner)" -ForegroundColor Cyan

$env:PYTHONPATH = Join-Path $repoRoot 'src'
$PythonExe      = ".\.venv\Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    Write-Host "[ERROR] Python executable not found at $PythonExe" -ForegroundColor Red
    return
}

Write-Host "RepoRoot  = $repoRoot"
Write-Host "PythonExe = $PythonExe"
Write-Host "PYTHONPATH= $env:PYTHONPATH"

Write-Host "`n[STEP 1] Run paper_live_without_ibg_nvda_phase5.py" -ForegroundColor Cyan
& $PythonExe .\tools\paper_live_without_ibg_nvda_phase5.py
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    Write-Host "[STEP 1] NVDA pipeline exited with code $exitCode" -ForegroundColor Red
    return
}

Write-Host "[STEP 1] NVDA Phase-5 paper runner completed successfully." -ForegroundColor Green

# [STEP 2] Convert NVDA Phase-5 paper results to nvda_phase5_paper_for_notion.csv
try {
    Write-Host "[STEP 2] Converting NVDA Phase-5 paper results to nvda_phase5_paper_for_notion.csv..." -ForegroundColor Cyan
    & $PythonExe .\tools\nvda_phase5_paper_to_csv.py
    Write-Host "[STEP 2] NVDA Phase-5 Notion CSV conversion completed." -ForegroundColor Green
}
catch {
    Write-Host "[STEP 2][WARN] NVDA Phase-5 Notion CSV conversion failed: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host "`n[PIPELINE] NVDA Phase-5 paper pipeline complete." -ForegroundColor Green