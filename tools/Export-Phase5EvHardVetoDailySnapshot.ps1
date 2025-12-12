[CmdletBinding()]
param(
    [string]$Day = $(Get-Date -Format "yyyy-MM-dd")
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$impl = Join-Path $repoRoot 'tools\Export-Phase5EvHardVetoDailySnapshot_20251204_165001.bak.ps1'
if (-not (Test-Path $impl)) { throw "EV-hard snapshot impl missing: $impl" }

Write-Host "[EV-HARD] Export daily snapshot (Day=$Day)" -ForegroundColor Cyan
Write-Host "[EV-HARD] Impl = $impl"

& $impl -Day $Day
$code = $LASTEXITCODE
if ($code -ne 0) { throw "EV-hard snapshot impl failed with exit code $code" }

Write-Host "[EV-HARD] OK" -ForegroundColor Green
