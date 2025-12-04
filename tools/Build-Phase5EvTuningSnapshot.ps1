$ErrorActionPreference = "Stop"

# scriptDir = tools/, repoRoot = parent (repo root)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot  = Split-Path -Parent $scriptDir
Set-Location $repoRoot

$PythonExe = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    Write-Host "[EV-TUNING] Python venv not found at $PythonExe" -ForegroundColor Red
    exit 1
}

# Ensure src/ is on PYTHONPATH
$env:PYTHONPATH = Join-Path $repoRoot "src"

Write-Host "[EV-TUNING] Building Phase-5 EV tuning snapshot..." -ForegroundColor Cyan
& $PythonExe tools\phase5_build_ev_tuning_snapshot.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "[EV-TUNING] Snapshot build FAILED" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "[EV-TUNING] Snapshot build PASSED" -ForegroundColor Green