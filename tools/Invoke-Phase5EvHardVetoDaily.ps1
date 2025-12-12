[CmdletBinding()]
param(
    [string]$Day = $(Get-Date -Format "yyyy-MM-dd")
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "[PHASE5-EV-HARD] Exporting daily snapshot for $Day ..." -ForegroundColor Cyan

$exportScript = Join-Path $repoRoot 'tools\Export-Phase5EvHardVetoDailySnapshot.ps1'

if (-not (Test-Path $exportScript)) {
    Write-Host "[PHASE5-EV-HARD] ERROR: Export script not found at $exportScript" -ForegroundColor Red
    exit 1
}

& $exportScript -Day $Day

Write-Host "[PHASE5-EV-HARD] Done." -ForegroundColor Cyan
