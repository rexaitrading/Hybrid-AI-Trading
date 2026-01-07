[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol="NVDA"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

function Fail([string]$m){
  Write-Host ("[TEST-BLOCKG-BUILDER] FAIL-CLOSED: " + $m) -ForegroundColor Red
  exit 2
}

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Set-Location $repoRoot

$builder = ".\tools\Build-BlockGStatusStub.ps1"
$checker = ".\tools\Check-BlockGReady.ps1"
$outPath = ".\logs\blockg_status_stub.json"

if(-not (Test-Path $builder)){ Fail "Missing builder: $builder" }
if(-not (Test-Path $checker)){ Fail "Missing checker: $checker" }

powershell -NoProfile -ExecutionPolicy Bypass -File $builder -Symbol $Symbol *>&1 | Out-Host
if($LASTEXITCODE -ne 0){ Fail "Builder exited nonzero: $LASTEXITCODE" }

if(-not (Test-Path $outPath)){ Fail "Missing output contract: $outPath" }

$j = Get-Content $outPath -Encoding utf8 | ConvertFrom-Json

# Strict Option-B: SPY/QQQ must remain blocked
if($j.spy_blockg_ready -ne $false){ Fail "spy_blockg_ready must be False (strict Option-B)" }
if($j.qqq_blockg_ready -ne $false){ Fail "qqq_blockg_ready must be False (strict Option-B)" }

# Checker must fail for SPY/QQQ deterministically
powershell -NoProfile -ExecutionPolicy Bypass -File $checker -Symbol SPY *>$null
if($LASTEXITCODE -eq 0){ Fail "Check-BlockGReady unexpectedly returned 0 for SPY" }

powershell -NoProfile -ExecutionPolicy Bypass -File $checker -Symbol QQQ *>$null
if($LASTEXITCODE -eq 0){ Fail "Check-BlockGReady unexpectedly returned 0 for QQQ" }

Write-Host "[TEST-BLOCKG-BUILDER] OK: builder output + strict SPY/QQQ blocked policy holds" -ForegroundColor Green
exit 0
