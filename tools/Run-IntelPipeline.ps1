[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# Script lives under repoRoot\tools -> go one level up to repo root
$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

Write-Host "`n[INTEL] Run-IntelPipeline (pre-market wrapper)" -ForegroundColor Cyan
Write-Host "RepoRoot  = $repoRoot"

# Python + PYTHONPATH
$env:PYTHONPATH = Join-Path $repoRoot "src"
$PythonExe = ".\.venv\Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
  Write-Host "[INTEL] Missing python venv at $PythonExe -> fail-closed" -ForegroundColor Red
  return
}

# ---------------------------------------------------------------------
# STEP 1) GateScore daily summarization (REAL data; fail-closed)
# ---------------------------------------------------------------------
$gsScript = ".\tools\gatescore\summarize_gatescore_daily.py"
Write-Host "`n[STEP 1] GateScore daily summarization" -ForegroundColor Cyan
if (Test-Path $gsScript) {
  & $PythonExe $gsScript
} else {
  Write-Host "[STEP 1] Missing $gsScript -> skipped (fail-closed)" -ForegroundColor Yellow
}

# ---------------------------------------------------------------------
# STEP 2) Build Block-G contract (fail-closed)
# ---------------------------------------------------------------------
$builder = ".\tools\Build-BlockGStatusStub.ps1"
Write-Host "`n[STEP 2] Build Block-G status stub" -ForegroundColor Cyan
if (Test-Path $builder) {
  powershell -NoProfile -ExecutionPolicy Bypass -File $builder
} else {
  Write-Host "[STEP 2] Missing $builder -> skipped (fail-closed)" -ForegroundColor Yellow
}

# ---------------------------------------------------------------------
# STEP 3) Optional: Check readiness (informational only)
# ---------------------------------------------------------------------
$checker = ".\tools\Check-BlockGReady.ps1"
Write-Host "`n[STEP 3] Check-BlockGReady NVDA (informational)" -ForegroundColor Cyan
if (Test-Path $checker) {
  powershell -NoProfile -ExecutionPolicy Bypass -File $checker -Symbol NVDA
  Write-Host ("[STEP 3] ExitCode={0}" -f $LASTEXITCODE) -ForegroundColor Gray
} else {
  Write-Host "[STEP 3] Missing $checker -> skipped" -ForegroundColor Yellow
}

Write-Host "`n[INTEL] Done." -ForegroundColor Green
return