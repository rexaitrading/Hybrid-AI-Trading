[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol = "NVDA"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$tools = Split-Path -Parent $PSCommandPath
$repo  = Split-Path -Parent $tools
Set-Location -LiteralPath $repo

$logs = Join-Path $repo "logs"
if(-not (Test-Path -LiteralPath $logs)){ New-Item -ItemType Directory -Path $logs -Force | Out-Null }

function Require-Tool([string]$rel){
  $p = Join-Path $repo $rel
  if(-not (Test-Path -LiteralPath $p)){ throw "Missing tool: $rel" }
  return $p
}

function Step([string]$name, [scriptblock]$fn){
  Write-Host "`n[PRE] $name" -ForegroundColor Cyan
  & $fn
  if($LASTEXITCODE -ne 0){ throw "Step failed: $name exit=$LASTEXITCODE" }
}

$tsUtc = (Get-Date).ToUniversalTime().ToString("o")
$today = (Get-Date).ToString("yyyy-MM-dd")

$result = [ordered]@{
  ts_utc = $tsUtc
  date = $today
  symbol = $Symbol
  ok = $false
  blockg_exit = $null
  notes = @()
}

try {
  Step "Intel Pipeline" {
    $t = Require-Tool "tools\Run-IntelPipeline.ps1"
    powershell -NoProfile -ExecutionPolicy Bypass -File $t | Out-Host
  }

  Step "Phase4 stamp presence check" {
    $p4 = Join-Path $logs "phase4_validation_passed.json"
    if(-not (Test-Path -LiteralPath $p4)){ throw "Missing Phase4 stamp: $p4" }
    Get-Content -LiteralPath $p4 -Raw -Encoding utf8 | Out-Host
  }

  Step "EV-HARD evidence raw" {
    $t = Require-Tool "tools\Build-EvHardEvidenceRaw.ps1"
    powershell -NoProfile -ExecutionPolicy Bypass -File $t | Out-Host
  }
  Step "EV-HARD snapshot" {
    $t = Require-Tool "tools\Build-EvHardSnapshot.ps1"
    powershell -NoProfile -ExecutionPolicy Bypass -File $t | Out-Host
  }
  Step "EV-HARD daily row" {
    $t = Require-Tool "tools\Run-EvHardVetoDaily.ps1"
    powershell -NoProfile -ExecutionPolicy Bypass -File $t | Out-Host
  }

  Step "GateScore PnL summary" {
    $t = Require-Tool "tools\Build-GateScorePnlSummary.ps1"
    powershell -NoProfile -ExecutionPolicy Bypass -File $t | Out-Host
  }

  Write-Host "`n[PRE] Block-G Build+Check (single authority)" -ForegroundColor Cyan
  $bg = Require-Tool "tools\Invoke-BlockGCheck.ps1"
  powershell -NoProfile -ExecutionPolicy Bypass -File $bg -Symbol $Symbol -Market $Market -Mode ALL_STRICT | Out-Host
  $result.blockg_exit = $LASTEXITCODE

  if($result.blockg_exit -eq 0){
    $result.ok = $true
    $result.notes += "BLOCKG_READY"
    Write-Host "`n=== PRE-MARKET READY: PASS ===" -ForegroundColor Green
  } elseif($result.blockg_exit -eq 10){
    $result.ok = $true
    $result.notes += "BLOCKG_CLOSED_DAY_DIAGNOSTIC_OK"
    Write-Host "`n=== PRE-MARKET READY: PASS (DIAGNOSTIC ONLY; MARKET CLOSED) ===" -ForegroundColor Yellow
  } else {
    $result.ok = $false
    $result.notes += ("BLOCKG_NOT_READY exit=" + $result.blockg_exit)
    Write-Host "`n=== PRE-MARKET READY: FAIL (fail-closed) ===" -ForegroundColor Red
  }

} catch {
  $result.ok = $false
  $result.notes += ("EXCEPTION: " + ($_ | Out-String).Trim())
  Write-Host "`n=== PRE-MARKET READY: FAIL (exception) ===" -ForegroundColor Red
}

$outPath = Join-Path $logs "premarket_ready.json"
$out = ($result | ConvertTo-Json -Depth 6)
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$out = ($out -replace "`r`n","`n")
if($out.Length -gt 0 -and $out[-1] -ne "`n"){ $out += "`n" }
[System.IO.File]::WriteAllText($outPath, $out, $utf8NoBom)
Write-Host "[PRE] wrote $outPath" -ForegroundColor Yellow

exit 0
