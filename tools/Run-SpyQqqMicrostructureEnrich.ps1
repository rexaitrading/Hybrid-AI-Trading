[CmdletBinding()]
param(
    [ValidateSet("SPY", "QQQ", "BOTH")]
    [string] $Symbol = "BOTH",

    [switch] $DryRun
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# Script lives under repoRoot\tools -> go one level up to repo root
$scriptDir = Split-Path -Parent $PSCommandPath
$repoRoot  = Split-Path -Parent $scriptDir
Set-Location $repoRoot

Write-Host "`n[PHASE2] SPY/QQQ microstructure enrichment wrapper" -ForegroundColor Cyan
Write-Host "RepoRoot  = $repoRoot"
Write-Host "Symbol    = $Symbol"
Write-Host "DryRun    = $DryRun" -ForegroundColor Gray

# Python + PYTHONPATH
$env:PYTHONPATH = Join-Path $repoRoot "src"
$PythonExe      = ".\.venv\Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    Write-Host "[ERROR] Python executable not found at $PythonExe" -ForegroundColor Red
    exit 1
}

$relScript  = "tools\\spy_qqq_microstructure_enrich.py"
$fullScript = Join-Path $repoRoot $relScript

if (-not (Test-Path $fullScript)) {
    Write-Host "[ERROR] Microstructure script not found at $fullScript" -ForegroundColor Red
    exit 1
}

# Build argument list
$argsList = @($relScript, "--symbol", $Symbol)
if ($DryRun) {
    $argsList += "--dry-run"
}

Write-Host "`n[PHASE2] Running: $PythonExe $($argsList -join ' ')" -ForegroundColor Cyan

& $PythonExe @argsList
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    Write-Host "[PHASE2] Microstructure enrichment FAILED with exit code $exitCode" -ForegroundColor Red
    exit $exitCode
}

Write-Host "[PHASE2] Microstructure enrichment completed successfully." -ForegroundColor Green