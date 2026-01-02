[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "ALL",
  [int]$MinEvents = 10
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

# Prefer canonical location if present
$candidates = @(
  (Join-Path $repoRoot "tools\Build-GateScoreEvents-Today.ps1"),
  (Join-Path $repoRoot "tools\Build-GateScoreEvents.ps1"),
  (Join-Path $repoRoot "tools\Run-GateScoreEvents.ps1")
) | Select-Object -Unique

$target = $null
foreach($c in $candidates){
  if(Test-Path -LiteralPath $c){
    if((Resolve-Path $c).Path -ne (Resolve-Path $PSCommandPath).Path){
      $target = $c
      break
    }
  }
}

if(-not $target){
  Write-Host "[GS-EVENTS] NOT FOUND: no canonical GateScore events builder script present in tools/. (fail-closed)" -ForegroundColor Red
  exit 2
}

powershell -NoProfile -ExecutionPolicy Bypass -File $target -Symbol $Symbol -MinEvents $MinEvents | Out-Host
exit $LASTEXITCODE
