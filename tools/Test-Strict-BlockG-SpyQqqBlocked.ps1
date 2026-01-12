[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null

function Fail([string]$m){
  Write-Host ("[STRICT-BLOCKG] FAIL-CLOSED: " + $m) -ForegroundColor Red
  exit 2
}

$path = ".\logs\blockg_status_stub.json"
if(-not (Test-Path $path)){ Fail "Missing contract: $path" }

$j = Get-Content $path -Encoding utf8 | ConvertFrom-Json

if($j.spy_blockg_ready -ne $false){ Fail "spy_blockg_ready must be False in STRICT mode" }
if($j.qqq_blockg_ready -ne $false){ Fail "qqq_blockg_ready must be False in STRICT mode" }

# We require the strict-source reason to be present (prevents accidental loosening)
$rn = @()
try { $rn = @($j.reasons_not_ready) } catch { $rn = @() }
$rnText = ($rn | ForEach-Object { "$_" }) -join ";"
if($rnText -notmatch 'gatescore_metrics_source=paperlive_real_v1'){
  Fail "Expected reasons_not_ready to include gatescore_metrics_source=paperlive_real_v1; got: $rnText"
}

# Also prove checker FAILs for SPY/QQQ (deterministic)
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Invoke-BlockGCheck.ps1 -Symbol SPY *>$null
if($LASTEXITCODE -eq 0){ Fail "Check-BlockGReady unexpectedly returned 0 for SPY" }

powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Invoke-BlockGCheck.ps1 -Symbol QQQ *>$null
if($LASTEXITCODE -eq 0){ Fail "Check-BlockGReady unexpectedly returned 0 for QQQ" }

Write-Host "[STRICT-BLOCKG] OK: SPY/QQQ remain blocked (strict mode enforced)" -ForegroundColor Green
exit 0
