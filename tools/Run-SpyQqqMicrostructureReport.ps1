[CmdletBinding()]
param(
    [switch] $SkipEnrich  # if set, reuse existing *_micro CSVs
)

$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

Write-Host "`n[MICRO-REPORT] === Run SPY/QQQ microstructure EV/PnL report ===" -ForegroundColor Cyan

# 1) Optionally refresh the *_micro CSVs
if (-not $SkipEnrich) {
    $enrichPs = Join-Path $toolsDir "Run-SpyQqqMicrostructureEnrich.ps1"
    if (Test-Path $enrichPs) {
        Write-Host "[MICRO-REPORT] Refreshing SPY/QQQ microstructure-enriched CSVs..." -ForegroundColor Yellow
        & $enrichPs
    } else {
        Write-Host "[MICRO-REPORT] SKIP: Run-SpyQqqMicrostructureEnrich.ps1 not found at $enrichPs" -ForegroundColor DarkYellow
    }
}

# 2) Run the Python report script
$PythonExe = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    Write-Host "[MICRO-REPORT] ERROR: Python executable not found at $PythonExe" -ForegroundColor Red
    exit 1
}

$scriptPath = Join-Path $toolsDir "spy_qqq_microstructure_report.py"
if (-not (Test-Path $scriptPath)) {
    Write-Host "[MICRO-REPORT] ERROR: spy_qqq_microstructure_report.py not found at $scriptPath" -ForegroundColor Red
    exit 1
}

$env:PYTHONPATH = Join-Path $repoRoot 'src'

& $PythonExe $scriptPath

Write-Host "`n[MICRO-REPORT] === End SPY/QQQ microstructure EV/PnL report ===`n" -ForegroundColor Cyan