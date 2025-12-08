[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

Write-Host "`n[MICROSTRUCTURE-PROBE] === Phase-2 Microstructure Feature Probe ===" -ForegroundColor Cyan

$PythonExe = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    Write-Host "[MICROSTRUCTURE-PROBE] ERROR: Python executable not found at $PythonExe" -ForegroundColor Red
    exit 1
}

$scriptPath = Join-Path $toolsDir "microstructure_feature_probe.py"
if (-not (Test-Path $scriptPath)) {
    Write-Host "[MICROSTRUCTURE-PROBE] ERROR: microstructure_feature_probe.py not found at $scriptPath" -ForegroundColor Red
    exit 1
}

# Ensure src is on PYTHONPATH
$env:PYTHONPATH = Join-Path $repoRoot 'src'

& $PythonExe $scriptPath

Write-Host "`n[MICROSTRUCTURE-PROBE] === End Phase-2 Microstructure Feature Probe ===`n" -ForegroundColor Cyan