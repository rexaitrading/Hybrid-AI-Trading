[CmdletBinding()]
param(
    [string]$ConfigPath = 'config\phase5_orb_spy.json'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$scriptRoot = $PSScriptRoot
$repoRoot   = Split-Path -Parent $scriptRoot

Set-Location $repoRoot

$cfgPath = Join-Path $repoRoot $ConfigPath
if (-not (Test-Path $cfgPath)) {
    throw "ORB config missing: $cfgPath"
}

$orbCfg = Get-Content $cfgPath -Raw | ConvertFrom-Json

$env:ORB_MINUTES = $orbCfg.orb_minutes
$env:TP_R        = $orbCfg.tp_r
$env:ORB_REGIME  = $orbCfg.regime
$env:ORB_SOURCE  = $orbCfg.source_tag

Write-Host "[PHASE5-ORB] Loaded $cfgPath" -ForegroundColor Cyan
Write-Host "  ORB minutes : $($env:ORB_MINUTES)"
Write-Host "  TP (R)      : $($env:TP_R)"
Write-Host "  Regime      : $($env:ORB_REGIME)"
Write-Host "  Source      : $($env:ORB_SOURCE)"