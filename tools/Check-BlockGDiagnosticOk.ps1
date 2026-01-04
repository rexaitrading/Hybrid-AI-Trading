[CmdletBinding()]
param([ValidateSet("NVDA","SPY","QQQ")] [string]$Symbol="NVDA")

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$checker  = Join-Path $toolsDir "Check-BlockGReady.ps1"

powershell -NoProfile -ExecutionPolicy Bypass -File $checker -Symbol $Symbol | Out-Host
$code = $LASTEXITCODE

if($code -eq 0){
  Write-Host "[BLOCKG-DIAG] OK (LIVE eligible)" -ForegroundColor Green
  exit 0
}
if($code -eq 10){
  Write-Host "[BLOCKG-DIAG] OK (CLOSED-DAY diagnostic; LIVE disallowed)" -ForegroundColor Yellow
  exit 0
}

Write-Host "[BLOCKG-DIAG] FAIL (code=$code)" -ForegroundColor Red
exit $code
