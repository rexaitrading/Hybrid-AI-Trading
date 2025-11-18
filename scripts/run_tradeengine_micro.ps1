param(
    [switch]$Verbose
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Assume this script lives in scripts/, repo root is one level up
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$root      = Split-Path -Parent $scriptDir
Set-Location $root

$pmSmoke = Join-Path $root "tools\PreMarket-TradeEngineSmoke.ps1"
if (-not (Test-Path $pmSmoke)) {
    throw "PreMarket-TradeEngineSmoke.ps1 not found at $pmSmoke"
}

if ($Verbose) {
    & $pmSmoke -Verbose
} else {
    & $pmSmoke
}
