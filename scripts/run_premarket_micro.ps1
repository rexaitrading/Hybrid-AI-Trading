param(
    [switch]$Verbose
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$root      = Split-Path -Parent $scriptDir
Set-Location $root

$tradeScript  = Join-Path $root "scripts\run_tradeengine_micro.ps1"
$replayScript = Join-Path $root "scripts\run_replay_micro.ps1"

if (-not (Test-Path $tradeScript))  { throw "run_tradeengine_micro.ps1 not found at $tradeScript" }
if (-not (Test-Path $replayScript)) { throw "run_replay_micro.ps1 not found at $replayScript" }

Write-Host "[HybridAITrading] PreMarket MICRO: TradeEngine micro-suite..." -ForegroundColor Cyan
if ($Verbose) {
    & $tradeScript -Verbose
} else {
    & $tradeScript
}

Write-Host "[HybridAITrading] PreMarket MICRO: Replay micro-suite..." -ForegroundColor Cyan
if ($Verbose) {
    & $replayScript -Verbose
} else {
    & $replayScript
}

Write-Host "[HybridAITrading] PreMarket MICRO: ALL GREEN (TradeEngine + Replay)" -ForegroundColor Green
