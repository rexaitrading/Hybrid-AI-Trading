param(
    [switch]$Verbose
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Resolve repo root from this script path
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $here
Set-Location $root

Write-Host "[HybridAITrading] PreMarket-TradeEngineSmoke starting..." -ForegroundColor Cyan

# Ensure .venv Python is on PATH if python is missing
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    $venvPy = Join-Path $root ".venv\Scripts\python.exe"
    if (-not (Test-Path $venvPy)) {
        throw "python not on PATH and .venv not found at $venvPy"
    }
    $env:PATH = (Split-Path $venvPy) + ";" + $env:PATH
}

$runner = Join-Path $here "Run-TradeEngineMicroSuite.ps1"
if (-not (Test-Path $runner)) {
    throw "Run-TradeEngineMicroSuite.ps1 not found at $runner"
}

try {
    if ($Verbose) {
        & $runner -VerboseOutput
    } else {
        & $runner
    }
    Write-Host "[HybridAITrading] PreMarket-TradeEngineSmoke: ALL GREEN" -ForegroundColor Green
}
catch {
    Write-Host "[HybridAITrading] PreMarket-TradeEngineSmoke: FAILED  $($_.Exception.Message)" -ForegroundColor Red
    throw
}
