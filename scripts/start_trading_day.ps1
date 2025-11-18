param(
    [switch]$Verbose
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$root      = Split-Path -Parent $scriptDir
Set-Location $root

Write-Host "[HybridAITrading] START TRADING DAY (MICRO MODE)..." -ForegroundColor Cyan

# 1) Run pre-market micro gate (TradeEngine + Replay)
$pmMicro = Join-Path $root "scripts\run_premarket_micro.ps1"
if (-not (Test-Path $pmMicro)) {
    throw "run_premarket_micro.ps1 not found at $pmMicro"
}

if ($Verbose) {
    & $pmMicro -Verbose
} else {
    & $pmMicro
}

# 2) Launch IB Gateway via helper if available
$ibgLauncher = Join-Path $root "scripts\ibg_auto_launch.ps1"
if (Test-Path $ibgLauncher) {
    Write-Host "[HybridAITrading] Launching IBG via ibg_auto_launch.ps1..." -ForegroundColor Cyan
    & $ibgLauncher
} else {
    Write-Host "[HybridAITrading] ibg_auto_launch.ps1 not found; launch IBG manually." -ForegroundColor Yellow
}

# 3) Run Provider QoS Gate (optional but recommended)
$qosGate = Join-Path $root "tools\Run-ProviderQoSGate.ps1"
if (Test-Path $qosGate) {
    & $qosGate
} else {
    Write-Host "[HybridAITrading] Run-ProviderQoSGate.ps1 not found; QoS not checked." -ForegroundColor Yellow
}

Write-Host "[HybridAITrading] START TRADING DAY micro-mode sequence complete." -ForegroundColor Green
