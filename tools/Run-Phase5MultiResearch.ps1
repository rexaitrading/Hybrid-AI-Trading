[CmdletBinding()]
param(
    [string]$DateTag = (Get-Date -Format 'yyyyMMdd')
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$scriptRoot = $PSScriptRoot
$repoRoot   = Split-Path -Parent $scriptRoot
Set-Location $repoRoot

Write-Host "=== Run-Phase5MultiResearch.ps1 ===" -ForegroundColor Cyan
Write-Host "Repo    : $repoRoot"
Write-Host "DateTag : $DateTag"
Write-Host ""

# Run NVDA B+ research pipeline
Write-Host "[BLOCK] NVDA B+ Research" -ForegroundColor Cyan
& .\tools\Run-NvdaOrbResearch.ps1 -DateTag $DateTag
if ($LASTEXITCODE -ne 0) {
    throw "Run-NvdaOrbResearch.ps1 failed (exit=$LASTEXITCODE)"
}

# Run SPY ORB research pipeline
Write-Host "[BLOCK] SPY ORB Research" -ForegroundColor Cyan
& .\tools\Run-SpyOrbResearch.ps1 -DateTag $DateTag
if ($LASTEXITCODE -ne 0) {
    throw "Run-SpyOrbResearch.ps1 failed (exit=$LASTEXITCODE)"
}

# Run QQQ ORB research pipeline
Write-Host "[BLOCK] QQQ ORB Research" -ForegroundColor Cyan
& .\tools\Run-QqqOrbResearch.ps1 -DateTag $DateTag
if ($LASTEXITCODE -ne 0) {
    throw "Run-QqqOrbResearch.ps1 failed (exit=$LASTEXITCODE)"
}

Write-Host ""
Write-Host "[DONE] Run-Phase5MultiResearch.ps1 completed for DateTag=$DateTag" -ForegroundColor Green