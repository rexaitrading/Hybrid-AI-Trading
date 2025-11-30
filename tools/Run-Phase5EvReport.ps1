param(
    [int] $DaysBack = 5
)

$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

# venv python
$PythonExe = ".\.venv\Scripts\python.exe"
Write-Host "`n[EV-REPORT] Using PythonExe = $PythonExe" -ForegroundColor Cyan

# Ensure src is on PYTHONPATH if needed
$srcPath = Join-Path $repoRoot "src"
$env:PYTHONPATH = $srcPath

Write-Host "[EV-REPORT] Running Phase-5 EV vs realized report for last $DaysBack day(s)..." -ForegroundColor Cyan

& $PythonExe "tools\phase5_ev_vs_realized_report.py" --days-back $DaysBack