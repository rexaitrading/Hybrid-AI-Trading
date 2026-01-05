[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol="NVDA"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location -LiteralPath $repoRoot
[System.Environment]::CurrentDirectory = (Get-Location).Path

$ss = Join-Path $toolsDir "Run-Phase5SafetySnapshot.ps1"
$ck = Join-Path $toolsDir "Check-BlockGReady.ps1"
if(-not (Test-Path -LiteralPath $ss)){ throw "Missing: $ss" }
if(-not (Test-Path -LiteralPath $ck)){ throw "Missing: $ck" }

Write-Host "=== PH5 PREFLIGHT: SafetySnapshot ===" -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File $ss | Out-Host
if($LASTEXITCODE -ne 0){
  Write-Host ("[PH5-PREFLIGHT] FAIL step=snapshot rc=" + $LASTEXITCODE) -ForegroundColor Yellow
  exit $LASTEXITCODE
}

Write-Host ("=== PH5 PREFLIGHT: BlockGReady Symbol=" + $Symbol + " ===") -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File $ck -Symbol $Symbol -Build | Out-Host
$rc = $LASTEXITCODE

if($rc -ne 0){
  Write-Host ("[PH5-PREFLIGHT] FAIL step=blockg rc=" + $rc) -ForegroundColor Red
  exit $rc
}

Write-Host "[PH5-PREFLIGHT] OK (LIVE eligible for this Symbol under Block-G)" -ForegroundColor Green
exit 0