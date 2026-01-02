[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol="NVDA"
)

Set-StrictMode -Version Latest
chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding  = [System.Text.Encoding]::UTF8
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
if($rcInputs -eq 0){
  Write-Host ("[PRE-SMART] inputs_rc={0} (quick inputs OK)" -f $rcInputs) -ForegroundColor Green
} elseif($rcInputs -eq 2){
  Write-Host ("[PRE-SMART] inputs_rc={0} (quick inputs warn; strict runner will decide)" -f $rcInputs) -ForegroundColor DarkYellow
} else {
  Write-Host ("[PRE-SMART] inputs_rc={0} (quick inputs warn; strict runner will decide)" -f $rcInputs) -ForegroundColor DarkYellow
}

if($weekend -and $rcInputs -eq 2){
  Write-Host "[PRE-SMART] Weekend + stale inputs (inputs_rc=2) => exiting 2 (skip strict runner)." -ForegroundColor Yellow
  exit 2
}

# 2) Full strict runner (authoritative for arming live)
& ".\tools\Run-PreMarketBlockG.ps1" -Symbol $Symbol
$rc = $LASTEXITCODE

Write-Host ("[PRE-SMART] strict_runner_rc={0}" -f $rc) -ForegroundColor Yellow
exit $rc
