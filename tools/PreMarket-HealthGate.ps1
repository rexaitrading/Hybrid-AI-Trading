[CmdletBinding()]
param(
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

# When this script runs from tools\, PSScriptRoot == ...\HybridAITrading\tools
$toolsDir = $PSScriptRoot
$repoRoot = (Get-Item $toolsDir).Parent.FullName

Write-Host "[HealthGate] toolsDir = $toolsDir" -ForegroundColor Cyan
Write-Host "[HealthGate] repoRoot = $repoRoot" -ForegroundColor Cyan

Set-Location $repoRoot

# =====================================================================
# 1) Crypto rail: Coinbase + Kraken + router QoS gate
# =====================================================================
Write-Host "=== Crypto rail pre-check: Coinbase ===" -ForegroundColor Cyan

$coinbaseProbe = Join-Path $toolsDir 'PreMarket-CoinbaseProbe.ps1'
if (-not (Test-Path $coinbaseProbe)) {
    throw "[HealthGate] Missing Coinbase probe script at $coinbaseProbe"
}

if (-not $DryRun) {
    & $coinbaseProbe
    $exit = $LASTEXITCODE
} else {
    Write-Host "[HealthGate] DryRun: skipping actual Coinbase probe." -ForegroundColor Yellow
    $exit = 0
}

if ($exit -ne 0) {
    Write-Host ">>> Crypto rail pre-check (Coinbase) FAILED  aborting pre-market sequence." -ForegroundColor Red
    exit 1
}

Write-Host "=== Coinbase rail OK ===" -ForegroundColor Green

Write-Host "=== Crypto rail pre-check: Kraken ===" -ForegroundColor Cyan

$krakenProbe = Join-Path $toolsDir 'Probe-Kraken.ps1'
if (-not (Test-Path $krakenProbe)) {
    throw "[HealthGate] Missing Kraken probe script at $krakenProbe"
}

if (-not $DryRun) {
    & $krakenProbe
    $exit = $LASTEXITCODE
} else {
    Write-Host "[HealthGate] DryRun: skipping Kraken probe." -ForegroundColor Yellow
    $exit = 0
}

if ($exit -ne 0) {
    Write-Host ">>> Crypto rail pre-check (Kraken) FAILED  aborting pre-market sequence." -ForegroundColor Red
    exit 1
}

Write-Host "=== Kraken rail OK (QoS logged) ===" -ForegroundColor Green

Write-Host "=== Crypto QoS gate (router decision) ===" -ForegroundColor Cyan

$pyGate = Join-Path $toolsDir 'Crypto-QoSGate.py'
if (-not (Test-Path $pyGate)) {
    throw "[HealthGate] Missing Crypto QoS gate Python script at $pyGate"
}

# Ensure venv + PYTHONPATH for the gate
$activate = Join-Path $repoRoot '.venv\Scripts\Activate.ps1'
if (Test-Path $activate) {
    Write-Host "[HealthGate] Activating venv via $activate" -ForegroundColor Cyan
    & $activate
}

$setPy = Join-Path $toolsDir 'Set-PythonPath.ps1'
if (Test-Path $setPy) {
    Write-Host "[HealthGate] Setting PYTHONPATH via $setPy" -ForegroundColor Cyan
    & $setPy
}

if (-not $DryRun) {
    python $pyGate
    $exit = $LASTEXITCODE
} else {
    Write-Host "[HealthGate] DryRun: skipping Crypto QoS gate." -ForegroundColor Yellow
    $exit = 0
}

if ($exit -ne 0) {
    Write-Host ">>> Crypto QoS gate FAILED  aborting pre-market sequence." -ForegroundColor Red
    exit 1
}

Write-Host "=== Crypto rail: Coinbase + Kraken QoS + router OK ===" -ForegroundColor Green

# =====================================================================
# 2) IB Gateway pre-check (Paper by default)
# =====================================================================
Write-Host "=== IB Gateway pre-check (Paper) ===" -ForegroundColor Cyan

$ibgProbe = Join-Path $toolsDir 'Probe-IBGateway.ps1'
if (-not (Test-Path $ibgProbe)) {
    throw "[HealthGate] Missing IB Gateway probe script at $ibgProbe"
}

if (-not $DryRun) {
    # Adjust -Mode or -ExpectedRoot here if you want Live / different path
    & $ibgProbe -Mode Paper
    $exit = $LASTEXITCODE
} else {
    Write-Host "[HealthGate] DryRun: skipping IB Gateway probe." -ForegroundColor Yellow
    $exit = 0
}

if ($exit -ne 0) {
    Write-Host ">>> IB Gateway pre-check FAILED  aborting pre-market sequence." -ForegroundColor Red
    exit 1
}

Write-Host "=== IB Gateway (Paper) OK ===" -ForegroundColor Green

# =====================================================================
# 3) RiskSmoke pre-check (risk tests)
# =====================================================================
Write-Host "=== RiskSmoke pre-check ===" -ForegroundColor Cyan

$riskSmoke = Join-Path $toolsDir 'PreMarket-RiskSmoke.ps1'
if (-not (Test-Path $riskSmoke)) {
    throw "[HealthGate] Missing RiskSmoke script at $riskSmoke"
}

if (-not $DryRun) {
    & $riskSmoke
    $exit = $LASTEXITCODE
} else {
    Write-Host "[HealthGate] DryRun: skipping RiskSmoke tests." -ForegroundColor Yellow
    $exit = 0
}

if ($exit -ne 0) {
    Write-Host ">>> RiskSmoke pre-check FAILED  aborting pre-market sequence." -ForegroundColor Red
    exit 1
}

Write-Host "=== RiskSmoke OK ===" -ForegroundColor Green

Write-Host "=== Pre-market HealthGate: ALL CORE RAILS GREEN (Crypto + IBG + Risk) ===" -ForegroundColor Green