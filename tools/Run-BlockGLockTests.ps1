[CmdletBinding()]
param([ValidateSet("NVDA","SPY","QQQ")] [string]$Symbol="NVDA")

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

Write-Host "`n[BLOCKG-LOCK] 1) closed-day semantics (ready=10 diag=0)..." -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Test-BlockGWeekendSemantics.ps1 -Symbol $Symbol | Out-Host
if($LASTEXITCODE -ne 0){ throw "[BLOCKG-LOCK] Weekend semantics test failed" }

Write-Host "`n[BLOCKG-LOCK] 2) no-bypass..." -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Test-BlockGNoBypass.ps1 | Out-Host
if($LASTEXITCODE -ne 0){ throw "[BLOCKG-LOCK] No-bypass test failed" }

Write-Host "`n[BLOCKG-LOCK] PASS" -ForegroundColor Green
exit 0
