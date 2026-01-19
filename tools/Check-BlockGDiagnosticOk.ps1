[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol = "NVDA"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null

$toolsDir = Split-Path -Parent $PSCommandPath
$checker  = Join-Path $toolsDir "Check-BlockGReady.ps1"
if(-not (Test-Path -LiteralPath $checker)){ throw "Missing: $checker" }

& powershell -NoProfile -ExecutionPolicy Bypass -File $checker -Symbol $Symbol -Market $env:HAT_MARKET | Out-Host
$code = $LASTEXITCODE

if($code -eq 0){
  Write-Host "[BLOCKG-DIAG] OK (LIVE eligible)" -ForegroundColor Green
  $global:LASTEXITCODE = 0
  return 0
}
if($code -eq 10){
  Write-Host "[BLOCKG-DIAG] OK (CLOSED-DAY diagnostic; LIVE disallowed)" -ForegroundColor Yellow
  $global:LASTEXITCODE = 0
  return 0
}

Write-Host ("[BLOCKG-DIAG] FAIL (code=" + $code + ")") -ForegroundColor Red
$global:LASTEXITCODE = $code
return $code
