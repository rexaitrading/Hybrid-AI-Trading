[CmdletBinding()]
param(
  [Parameter(Mandatory=$false)]
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "NVDA"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# BLOCKG_SINGLE_SEMANTICS_OWNER
# Phase-4 readiness delegates to Check-BlockGReady.ps1 (single semantic owner).
$toolsDir = Split-Path -Parent $PSCommandPath
$checker  = Join-Path $toolsDir "Check-BlockGReady.ps1"

if (-not (Test-Path -LiteralPath $checker)) {
  Write-Host "[PHASE4] ERROR: missing Check-BlockGReady.ps1" -ForegroundColor Yellow
  exit 1
}

& $checker -Symbol $Symbol -Build -Market $env:HAT_MARKET
exit $LASTEXITCODE
