[CmdletBinding()]
param(
    [string]$DateTag = (Get-Date -Format 'yyyyMMdd')
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$scriptRoot = $PSScriptRoot
$repoRoot   = Split-Path -Parent $scriptRoot

Set-Location $repoRoot

Write-Host "=== Phase5 Multi-Strategy Runner (NVDA B+ + SPY ORB + QQQ ORB) ===" -ForegroundColor Cyan
Write-Host "Repo    : $repoRoot"
Write-Host "DateTag : $DateTag"
Write-Host ""

# 1) Load SPY ORB config into env (ORB_MINUTES, TP_R, etc.)
$loadOrb = Join-Path $repoRoot 'tools\Load-OrbConfig.ps1'
if (Test-Path $loadOrb) {
    & $loadOrb
} else {
    Write-Host "[WARN] Load-OrbConfig.ps1 not found, using defaults (ORB=5, TP=2.5)." -ForegroundColor Yellow
    $env:ORB_MINUTES = 5
    $env:TP_R        = 2.5
}

# 2) NVDA B+ pipeline$loadOrb = Join-Path $repoRoot 'tools\Load-OrbConfig.ps1'
if (Test-Path $loadOrb) {
    & $loadOrb
} else {
    Write-Host "[WARN] Load-OrbConfig.ps1 not found, using defaults (ORB=5, TP=2.5)." -ForegroundColor Yellow
    $env:ORB_MINUTES = 5
    $env:TP_R        = 2.5
}

# 2) NVDA B+ pipeline
Write-Host ""
Write-Host ">>> NVDA B+ pipeline" -ForegroundColor Magenta

$runNvdaReplay = Join-Path $repoRoot 'tools\Run-NvdaBplusReplay.ps1'
$updateNvda    = Join-Path $repoRoot 'tools\Update-NotionNvdaBplusReplay.ps1'

if (-not (Test-Path $runNvdaReplay)) {
    Write-Host "[WARN] Run-NvdaBplusReplay.ps1 not found." -ForegroundColor Yellow
} else {
    & $runNvdaReplay -DateTag $DateTag
}

if (-not (Test-Path $updateNvda)) {
    Write-Host "[WARN] Update-NotionNvdaBplusReplay.ps1 not found." -ForegroundColor Yellow
} else {
    & $updateNvda -DateTag $DateTag
}

# 3) SPY ORB pipeline
Write-Host ""
Write-Host ">>> SPY ORB pipeline" -ForegroundColor Magenta

$runSpyOrb = Join-Path $repoRoot 'tools\Run-SpyOrbReplay.ps1'
$updateSpy = Join-Path $repoRoot 'tools\Update-NotionSpyOrbReplay.ps1'

if (-not (Test-Path $runSpyOrb)) {
    Write-Host "[WARN] Run-SpyOrbReplay.ps1 not found." -ForegroundColor Yellow
} else {
    & $runSpyOrb -DateTag $DateTag -OrbMinutes ([int]$env:ORB_MINUTES) -TpR ([double]$env:TP_R)
}

if (-not (Test-Path $updateSpy)) {
    Write-Host "[WARN] Update-NotionSpyOrbReplay.ps1 not found." -ForegroundColor Yellow
} else {
    & $updateSpy -DateTag $DateTag
}

# 4) QQQ ORB pipeline
Write-Host ""
Write-Host ">>> QQQ ORB pipeline" -ForegroundColor Magenta

$runQqqOrb = Join-Path $repoRoot 'tools\Run-QqqOrbReplay.ps1'
$updateQqq = Join-Path $repoRoot 'tools\Update-NotionQqqOrbReplay.ps1'

if (-not (Test-Path $runQqqOrb)) {
    Write-Host "[WARN] Run-QqqOrbReplay.ps1 not found." -ForegroundColor Yellow
} else {
    & $runQqqOrb -DateTag $DateTag -OrbMinutes ([int]$env:ORB_MINUTES) -TpR ([double]$env:TP_R)
}

if (-not (Test-Path $updateQqq)) {
    Write-Host "[WARN] Update-NotionQqqOrbReplay.ps1 not found." -ForegroundColor Yellow
} else {
    & $updateQqq -DateTag $DateTag
}

Write-Host ""
Write-Host "[DONE] Phase5 Multi-Strategy run for DateTag=$DateTag complete." -ForegroundColor Green