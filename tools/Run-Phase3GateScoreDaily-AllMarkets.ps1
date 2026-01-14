[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol="NVDA",
  [ValidateSet("rewrite","append","prune")]
  [string]$Mode="rewrite",
  [int]$MinEvents=10
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

function Resolve-RepoRoot(){
  $toolsDir = Split-Path -Parent $PSCommandPath
  $rr = Split-Path -Parent $toolsDir
  try { return (Resolve-Path -LiteralPath $rr -ErrorAction Stop).Path } catch { return $rr }
}

$repoRoot = Resolve-RepoRoot
$psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"

$writer = Join-Path $repoRoot "tools\Write-GateScoreEvents-PerMarket.ps1"
if(-not (Test-Path -LiteralPath $writer)){ throw "Missing writer: $writer" }

$markets = @("US","JP","HK","SG","IN","KR","TW","CN_SH","CN_SZ")

$errs = @()
foreach($m in $markets){
  Write-Host ("[PH3-ALL] Market=" + $m + " Symbol=" + $Symbol + " Mode=" + $Mode + " MinEvents=" + $MinEvents) -ForegroundColor Cyan
  & $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $writer -Market $m -Symbol $Symbol -Mode $Mode -MinEvents $MinEvents *>&1 | Out-Host
  $rc = $LASTEXITCODE
  if($rc -ne 0){
    $errs += ("{0}:{1}" -f $m,$rc)
    Write-Host ("[PH3-ALL] WARN market=" + $m + " rc=" + $rc) -ForegroundColor Yellow
  }
}

if($errs.Count -gt 0){
  Write-Host ("[PH3-ALL] Completed with non-zero markets: " + ($errs -join ", ")) -ForegroundColor Yellow
  exit 2
}

Write-Host "[PH3-ALL] Completed OK for all markets" -ForegroundColor Green
exit 0
