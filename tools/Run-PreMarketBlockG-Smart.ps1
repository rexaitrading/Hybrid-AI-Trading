[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol="NVDA"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$root = (Resolve-Path ".").Path
Set-Location $root

$today = (Get-Date).ToString("yyyy-MM-dd")
$dow   = (Get-Date).DayOfWeek.ToString()
$weekend = ($dow -in @("Saturday","Sunday"))

Write-Host ("[PRE-SMART] RepoRoot={0} Today={1} {2} Symbol={3}" -f $root,$today,$dow,$Symbol) -ForegroundColor Cyan

# 1) Quick diagnostic (never throws)
& ".\tools\Check-PreMarketInputs.ps1" -Symbol $Symbol
$rcInputs = $LASTEXITCODE
Write-Host ("[PRE-SMART] inputs_rc={0}" -f $rcInputs) -ForegroundColor Yellow

if($weekend -and $rcInputs -eq 2){
  Write-Host "[PRE-SMART] Weekend + stale inputs => expected FAIL-CLOSED. Skipping heavy pre-market runner." -ForegroundColor Yellow
  exit 2
}

# 2) Full strict runner (authoritative for arming live)
& ".\tools\Run-PreMarketBlockG.ps1" -Symbol $Symbol
$rc = $LASTEXITCODE

Write-Host ("[PRE-SMART] strict_runner_rc={0}" -f $rc) -ForegroundColor Yellow
exit $rc