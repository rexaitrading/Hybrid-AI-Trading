[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$bak = Join-Path $repoRoot 'tools\Export-Phase5EvHardVetoDailySnapshot_20251204_165001.bak.ps1'
if (-not (Test-Path $bak)) { throw "Fallback snapshot script not found: $bak" }

Write-Host "[EV-HARD] Running fallback snapshot script..." -ForegroundColor Cyan
Write-Host "[EV-HARD] $bak"

& $bak
$code = $LASTEXITCODE
if ($code -ne 0) { throw "Fallback snapshot script failed with exit code $code" }

Write-Host "[EV-HARD] OK" -ForegroundColor Green