[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# Resolve repo root from this script's location (tools\ -> parent)
$repoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $repoRoot

Write-Host "=== DAILY FLOW: STEP 1 - IB API health check ===" -ForegroundColor Cyan

# STEP 1: IB API health check
$ibOutput = & .\tools\Test-IBAPI.ps1 2>&1
$ibOutput | ForEach-Object { Write-Host "  $_" }

if (($ibOutput -join "`n") -like '*IB API: FAIL*') {
    Write-Host "=== DAILY FLOW HALT: IB API health check failed. Fix IBG / account before continuing. ===" -ForegroundColor Red
    return
}

Write-Host "=== DAILY FLOW: STEP 2 - PreMarket risk/QoS check ===" -ForegroundColor Cyan

# STEP 2: PreMarket risk/QoS check
$pmOutput = & .\tools\PreMarket-Check.ps1 2>&1
$pmOutput | ForEach-Object { Write-Host "  $_" }

# Robust HALT detection: check the joined text for HALT markers
$pmText = $pmOutput -join "`n"
if ($pmText -like '*Pre-market check: HALT*' -or
    $pmText -like '*Risk: HALT*' -or
    $pmText -like '*QoS:  HALT*') {

    Write-Host "=== DAILY FLOW HALT: PreMarket-Check reported HALT. Review risk/QoS before trading. ===" -ForegroundColor Red
    return
}

Write-Host "=== DAILY FLOW: STEP 3 - Run paper strategy (Run-PaperOnce.py) ===" -ForegroundColor Cyan

# STEP 3: Actual paper run (only reached if IB + risk gates are OK)
$py = '.venv\\Scripts\\python.exe'
if (-not (Test-Path $py)) {
    throw "Python venv not found at $py"
}

# Make sure IB host/port are set for this session (paper IBG on 4002)
$env:IB_HOST = '127.0.0.1'
$env:IB_PORT = '4002'

& $py tools\Run-PaperOnce.py
Write-Host "=== DAILY FLOW COMPLETE: Run-PaperOnce.py finished. ===" -ForegroundColor Green