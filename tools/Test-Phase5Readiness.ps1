param()

$ErrorActionPreference = "Stop"

# Resolve repo root from this script location (tools\ -> repo)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot  = Split-Path -Parent $scriptDir

Set-Location $repoRoot

Write-Host "[PHASE5_TEST] Repo root: $repoRoot" -ForegroundColor Cyan

# Ensure PYTHONPATH includes src so tools.<module> imports work
$srcPath = Join-Path $repoRoot "src"
$env:PYTHONPATH = $srcPath

$PythonExe = ".\.venv\Scripts\python.exe"
Write-Host "[PHASE5_TEST] PythonExe: $PythonExe" -ForegroundColor Cyan
Write-Host "[PHASE5_TEST] PYTHONPATH: $env:PYTHONPATH" -ForegroundColor Cyan

if (-not (Test-Path $PythonExe)) {
    Write-Host "[PHASE5_TEST][FATAL] Python exe not found at $PythonExe" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path "tools\test_phase5_live_runners.py")) {
    Write-Host "[PHASE5_TEST][FATAL] tools\test_phase5_live_runners.py is missing." -ForegroundColor Red
    exit 1
}

Write-Host "[PHASE5_TEST] Running Phase-5 live-runner micro-suite..." -ForegroundColor Cyan

& $PythonExe "tools\test_phase5_live_runners.py"
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    Write-Host "[PHASE5_TEST] FAILED with exit code $exitCode" -ForegroundColor Red
    exit $exitCode
}

Write-Host "[PHASE5_TEST] SUCCESS - NVDA / SPY / QQQ Phase-5 live runners import + dry run OK." -ForegroundColor Green