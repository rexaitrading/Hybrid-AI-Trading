[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

Write-Host "`n[MICROSTRUCTURE] === Phase-2 Microstructure EV/GateScore Smoke ===" -ForegroundColor Cyan

$PythonExe = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    Write-Host "[MICROSTRUCTURE] ERROR: Python executable not found at $PythonExe" -ForegroundColor Red
    exit 1
}

$scriptPath = Join-Path $toolsDir "microstructure_ev_smoke.py"
if (-not (Test-Path $scriptPath)) {
    Write-Host "[MICROSTRUCTURE] ERROR: microstructure_ev_smoke.py not found at $scriptPath" -ForegroundColor Red
    exit 1
}

& $PythonExe $scriptPath

Write-Host "`n[MICROSTRUCTURE] === End Microstructure EV/GateScore Smoke ===`n" -ForegroundColor Cyan