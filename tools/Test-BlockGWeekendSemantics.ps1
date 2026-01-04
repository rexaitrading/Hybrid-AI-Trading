[CmdletBinding()]
param([ValidateSet("NVDA","SPY","QQQ")] [string]$Symbol="NVDA")

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$ready = Join-Path $toolsDir "Check-BlockGReady.ps1"
$diag  = Join-Path $toolsDir "Check-BlockGDiagnosticOk.ps1"

# 1) Live gate must be fail-closed on weekends/closed days (exit 10)
powershell -NoProfile -ExecutionPolicy Bypass -File $ready -Symbol $Symbol | Out-Host
$codeReady = $LASTEXITCODE

# 2) Diagnostic gate must succeed on weekends/closed days (exit 0)
powershell -NoProfile -ExecutionPolicy Bypass -File $diag -Symbol $Symbol | Out-Host
$codeDiag = $LASTEXITCODE

# Weekend/closed-day expected behavior:
# - Ready returns 10 (diagnostic ok but live disallowed)
# - Diag returns 0
if($codeReady -ne 10){ throw "[TEST] Expected Check-BlockGReady exit=10 on closed day, got=$codeReady" }
if($codeDiag -ne 0){ throw "[TEST] Expected Check-BlockGDiagnosticOk exit=0 on closed day, got=$codeDiag" }

Write-Host "[TEST] BlockG closed-day semantics OK (ready=10 diag=0)" -ForegroundColor Green
exit 0
