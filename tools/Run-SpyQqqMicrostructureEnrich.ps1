[CmdletBinding()]
param(
    [switch] $SkipPipelines  # allow quick re-enrich without re-running paper pipelines
)

$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

Write-Host "`n[SPY/QQQ-MICRO] === SPY/QQQ microstructure enrichment ===" -ForegroundColor Cyan

if (-not $SkipPipelines) {
    if (Test-Path .\tools\Invoke-SpyPhase5PaperPipeline.ps1) {
        Write-Host "[SPY/QQQ-MICRO] Running SPY Phase-5 paper pipeline..." -ForegroundColor Yellow
        .\tools\Invoke-SpyPhase5PaperPipeline.ps1
    } else {
        Write-Host "[SPY/QQQ-MICRO] SKIP: Invoke-SpyPhase5PaperPipeline.ps1 not found." -ForegroundColor DarkYellow
    }

    if (Test-Path .\tools\Invoke-QqqPhase5PaperPipeline.ps1) {
        Write-Host "[SPY/QQQ-MICRO] Running QQQ Phase-5 paper pipeline..." -ForegroundColor Yellow
        .\tools\Invoke-QqqPhase5PaperPipeline.ps1
    } else {
        Write-Host "[SPY/QQQ-MICRO] SKIP: Invoke-QqqPhase5PaperPipeline.ps1 not found." -ForegroundColor DarkYellow
    }
}

$PythonExe = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    Write-Host "[SPY/QQQ-MICRO] ERROR: Python executable not found at $PythonExe" -ForegroundColor Red
    exit 1
}

$scriptPath = Join-Path $toolsDir "spy_qqq_microstructure_enrich.py"
if (-not (Test-Path $scriptPath)) {
    Write-Host "[SPY/QQQ-MICRO] ERROR: spy_qqq_microstructure_enrich.py not found at $scriptPath" -ForegroundColor Red
    exit 1
}

$env:PYTHONPATH = Join-Path $repoRoot 'src'

& $PythonExe $scriptPath

Write-Host "`n[SPY/QQQ-MICRO] === End SPY/QQQ microstructure enrichment ===`n" -ForegroundColor Cyan