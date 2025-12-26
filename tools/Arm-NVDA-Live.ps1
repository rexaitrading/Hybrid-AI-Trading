[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

function Write-Utf8NoBom {
  param([string]$Path, [string]$Text)
  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  $Text = $Text -replace "`r`n", "`n"
  if ($Text.Length -gt 0 -and $Text[-1] -ne "`n") { $Text += "`n" }
  [System.IO.File]::WriteAllText($Path, $Text, $utf8NoBom)
}

function Fail([string]$Msg) {
  Write-Host "[ARM] FAIL-CLOSED: $Msg" -ForegroundColor Red
  exit 2
}

$today = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd")
$logsDir = Join-Path $repoRoot "logs"
New-Item -ItemType Directory -Force -Path $logsDir | Out-Null
$stampPath = Join-Path $logsDir "nvda_live_ready_stamp.json"

Write-Host "[ARM] Step 1/4 Phase4 stamp" -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $toolsDir "Run-Phase4Stamp.ps1") | Out-Host
if ($LASTEXITCODE -ne 0) { Fail "Phase4 failed exit=$LASTEXITCODE" }

Write-Host "[ARM] Step 2/4 GateScore daily build (today-only)" -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $toolsDir "Run-GateScoreDailyBuild.ps1") | Out-Host
if ($LASTEXITCODE -ne 0) { Fail "GateScore daily build failed exit=$LASTEXITCODE" }

Write-Host "[ARM] Step 3/4 Build BlockG status" -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $toolsDir "Build-BlockGStatusStub.ps1") -Symbol ALL | Out-Host
if ($LASTEXITCODE -ne 0) { Fail "Build-BlockGStatusStub failed exit=$LASTEXITCODE" }

Write-Host "[ARM] Step 4/4 Check BlockG readiness (NVDA)" -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $toolsDir "Check-BlockGReady.ps1") -Symbol NVDA | Out-Host
if ($LASTEXITCODE -ne 0) { Fail "Check-BlockGReady NVDA failed exit=$LASTEXITCODE" }

# Best-effort: attach BlockG snapshot info
$blockgPath = Join-Path $logsDir "blockg_status_stub.json"
$blockg = $null
try { if(Test-Path $blockgPath){ $blockg = Get-Content $blockgPath -Raw -Encoding utf8 | ConvertFrom-Json } } catch { $blockg = $null }


# Compute BlockG stamp fields (PowerShell-safe; no if-expression)
$blockgAsOf = ""
$blockgReasons = @()
try {
  if ($blockg -ne $null) {
    try { $blockgAsOf = [string]$blockg.gatescore_as_of_date } catch { $blockgAsOf = "" }
    try { $blockgReasons = @($blockg.reasons_not_ready) } catch { $blockgReasons = @() }
  }
} catch { $blockgAsOf = ""; $blockgReasons = @() }

$payload = [ordered]@{
  ts_utc = (Get-Date).ToUniversalTime().ToString("o")
  as_of_date = $today
  nvda_live_ready = $true
  blockg_as_of_date = $blockgAsOf
  phase4_ok_today = $true
  ev_hard_daily_ok_today = $true
  gatescore_ok_today = $true
  blockg_reasons_not_ready = $blockgReasons
}

Write-Utf8NoBom -Path $stampPath -Text ($payload | ConvertTo-Json -Depth 6)
Write-Host "[ARM] SUCCESS: NVDA LIVE READY stamp written: $stampPath" -ForegroundColor Green
exit 0
