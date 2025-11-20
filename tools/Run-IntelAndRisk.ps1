[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# Resolve repo root from this script's location (tools\ -> parent)
$repoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $repoRoot

Write-Host "=== INTEL+RISK FLOW: STEP 1 - Run intel pipeline (news/YouTube) ===" -ForegroundColor Cyan

# STEP 1: Existing intel pipeline (news + YouTube + news_gate join)
if (-not (Test-Path '.\tools\Run-IntelPipeline.ps1')) {
    throw "tools\Run-IntelPipeline.ps1 not found in $repoRoot"
}

$intelOutput = & .\tools\Run-IntelPipeline.ps1 2>&1
$intelOutput | ForEach-Object { Write-Host "  $_" }

Write-Host "=== INTEL+RISK FLOW: STEP 2 - RiskPulse/QoS builders (placeholder) ===" -ForegroundColor Cyan

# STEP 2: Future RiskPulse/QoS builders go here
# TODO (Phase 2/3):
#   - Build .intel\risk_pulse.jsonl from replay/paper logs
#   - Build .intel\provider_qos.jsonl from provider QoS stats
# Example placeholders (commented out):
# if (Test-Path '.\tools\Build-RiskPulse.ps1') {
#     & .\tools\Build-RiskPulse.ps1
# }
# if (Test-Path '.\tools\Build-ProviderQoS.ps1') {
#     & .\tools\Build-ProviderQoS.ps1
# }

Write-Host "=== INTEL+RISK FLOW: STEP 3 - PreMarket risk/QoS check (after intel) ===" -ForegroundColor Cyan

# STEP 3: Re-run PreMarket-Check to see updated RiskPulse/QoS gate
if (-not (Test-Path '.\tools\PreMarket-Check.ps1')) {
    throw "tools\PreMarket-Check.ps1 not found in $repoRoot"
}

$pmOutput = & .\tools\PreMarket-Check.ps1 2>&1
$pmOutput | ForEach-Object { Write-Host "  $_" }

$pmText = $pmOutput -join "`n"
if ($pmText -like '*Pre-market check: HALT*' -or
    $pmText -like '*Risk: HALT*' -or
    $pmText -like '*QoS:  HALT*') {

    Write-Host "=== INTEL+RISK FLOW RESULT: HALT (see above intel/risk report). ===" -ForegroundColor Red
} else {
    Write-Host "=== INTEL+RISK FLOW RESULT: OK (PreMarket-Check reports no HALT). ===" -ForegroundColor Green
}