[CmdletBinding()]
param([ValidateSet("NVDA","SPY","QQQ")] [string]$Symbol="NVDA")

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

Write-Host "`n[BLOCKG-LOCKPACK] 1) closed-day semantics (ready=10 diag=0)..." -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Test-BlockGWeekendSemantics.ps1 -Symbol $Symbol | Out-Host
if($LASTEXITCODE -ne 0){ throw "[BLOCKG-LOCKPACK] Weekend semantics failed" }

Write-Host "`n[BLOCKG-LOCKPACK] 2) no-bypass (READY execution allowlist)..." -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Test-BlockGNoBypass.ps1 | Out-Host
if($LASTEXITCODE -ne 0){ throw "[BLOCKG-LOCKPACK] No-bypass failed" }

Write-Host "`n[BLOCKG-LOCKPACK] 3) READY executor list (must be Arm-NVDA-Live only)..." -ForegroundColor Cyan
$hits = @(Select-String -Path .\tools\*.ps1 -Pattern 'powershell\s+-NoProfile.*Check-BlockGReady\.ps1|&\s*"\.\\tools\\Check-BlockGReady\.ps1"|&\s*\.\\tools\\Check-BlockGReady\.ps1' -ErrorAction SilentlyContinue)
$paths = @($hits | ForEach-Object { [string]$_.Path } | Sort-Object -Unique)
if($paths.Count -ne 1 -or ($paths[0] -notmatch '\\tools\\Arm-NVDA-Live\.ps1$')){
  throw ("[BLOCKG-LOCKPACK] READY executor list violation:`n" + ($paths -join "`n"))
}
Write-Host ("[BLOCKG-LOCKPACK] READY executor OK: " + $paths[0]) -ForegroundColor Green

Write-Host "`n[BLOCKG-LOCKPACK] 4) Python import sanity (no runtime orders)..." -ForegroundColor Cyan
python -c "import hybrid_ai_trading.brokers.ib_adapter as a; import hybrid_ai_trading.execution.execution_engine_phase5_guard as g; print('PY_IMPORT_OK')" | Out-Host

Write-Host "`n[BLOCKG-LOCKPACK] PASS" -ForegroundColor Green
exit 0
