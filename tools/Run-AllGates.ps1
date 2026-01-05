[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol = "NVDA"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

function Fail([string]$Msg){
  Write-Host ("[ALL-GATES] FAIL-CLOSED: " + $Msg) -ForegroundColor Red
  exit 2
}

$bars = (Get-ChildItem -LiteralPath .\logs\bars -File -Filter ("$Symbol" + "_*_1m.csv") |
  Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
if(-not $bars){ Fail "No bars file found under logs/bars" }

Write-Host ("[ALL-GATES] USING_BARS=" + $bars) -ForegroundColor Cyan

powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Test-BarCompleteness.ps1 -Symbol $Symbol -BarsPath $bars -Window RTH | Out-Host
if($LASTEXITCODE -ne 0){ Fail "Gate P1-A failed" }

powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Test-SessionBoundaries.ps1 -Symbol $Symbol -BarsPath $bars | Out-Host
if($LASTEXITCODE -ne 0){ Fail "Gate P1-B failed" }

powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Normalize-SessionTags.ps1 -BarsPath $bars | Out-Host
if($LASTEXITCODE -ne 0){ Fail "Gate P1-C failed" }

powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Run-BlockGLockPack.ps1 -Symbol $Symbol | Out-Host
if($LASTEXITCODE -ne 0){ Fail "Gate P5-A failed" }

pytest -q tests/test_execution_engine_phase5_guard.py
if($LASTEXITCODE -ne 0){ Fail "Gate P5-B failed" }

Write-Host "[ALL-GATES] PASS (Phase-1 + Phase-5 safety green)" -ForegroundColor Green
exit 0
