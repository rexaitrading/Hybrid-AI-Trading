[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$toolsDir = $PSScriptRoot
$repoRoot = (Get-Item $toolsDir).Parent.FullName

Write-Host "[Probe-Kraken] Repo: $repoRoot" -ForegroundColor Cyan
Set-Location $repoRoot

# Activate venv if present
$activate = Join-Path $repoRoot '.venv\Scripts\Activate.ps1'
if (Test-Path $activate) {
    Write-Host "[Probe-Kraken] Activating venv via $activate" -ForegroundColor Cyan
    & $activate
}

# Set PYTHONPATH via existing helper
$setPy = Join-Path $toolsDir 'Set-PythonPath.ps1'
if (Test-Path $setPy) {
    Write-Host "[Probe-Kraken] Setting PYTHONPATH via $setPy" -ForegroundColor Cyan
    & $setPy
}

$pyProbe = Join-Path $toolsDir 'Kraken-QoS-Probe.py'
if (-not (Test-Path $pyProbe)) {
    throw "[Probe-Kraken] Missing Kraken QoS probe script at $pyProbe"
}

Write-Host "[Probe-Kraken] Running $pyProbe ..." -ForegroundColor Cyan
python $pyProbe
$code = $LASTEXITCODE
Write-Host "[Probe-Kraken] Exit code: $code" -ForegroundColor Cyan
exit $code