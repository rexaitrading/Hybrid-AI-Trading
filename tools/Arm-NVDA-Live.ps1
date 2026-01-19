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

# A4/Policy: NVDA LIVE READY must only be asserted when BlockG returns rc==0
$nvdaLiveReady = $false


Write-Host "[ARM] Step 1/4 Phase4 stamp" -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $toolsDir "Run-Phase4Stamp.ps1") | Out-Host
if ($LASTEXITCODE -ne 0) { Fail "Phase4 failed exit=$LASTEXITCODE" }

Write-Host "[ARM] Step 2/4 GateScore daily build (today-only)" -ForegroundColor Cyan
# --- A2: GateScore summary BEFORE build (fail-closed) ---
$gsCsv = Join-Path $repoRoot "logs\gatescore_daily_summary.csv"
$gsSummary = Join-Path $toolsDir "Run-GateScoreDailySummary.ps1"
if(Test-Path -LiteralPath $gsSummary){
  powershell -NoProfile -ExecutionPolicy Bypass -File $gsSummary *>&1 | Out-Host
}
if(-not (Test-Path -LiteralPath $gsCsv)){
  Fail ("GateScore daily summary missing BEFORE build: " + $gsCsv)
}
# --- A2 END ---
powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $toolsDir "Run-GateScoreDailyBuild.ps1") | Out-Host
if ($LASTEXITCODE -ne 0) { Fail "GateScore daily build failed exit=$LASTEXITCODE" }
# --- A2: Ensure GateScore daily summary CSV exists (fail-closed) ---
$gsCsv = Join-Path $repoRoot "logs\gatescore_daily_summary.csv"
$gsSummary = Join-Path $toolsDir "Run-GateScoreDailySummary.ps1"
if(Test-Path -LiteralPath $gsSummary){
  powershell -NoProfile -ExecutionPolicy Bypass -File $gsSummary *>&1 | Out-Host
}
if(-not (Test-Path -LiteralPath $gsCsv)){
  Fail ("GateScore daily summary missing: " + $gsCsv)
}
# --- A2 END ---

Write-Host "[ARM] Step 3/4 Build BlockG status" -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $toolsDir "Build-BlockGStatusStub.ps1") -Market $m -Symbol ALL | Out-Host
if ($LASTEXITCODE -ne 0) { Fail "Build-BlockGStatusStub failed exit=$LASTEXITCODE" }

Write-Host "[ARM] Step 4/4 Check BlockG readiness (NVDA)" -ForegroundColor Cyan
# A4_ARM_DIRECT_CHECK_BLOCKGREADY_BEGIN
# Contract: Arm-NVDA-Live.ps1 MUST directly EXECUTE Check-BlockGReady.ps1 (LockPack Step-3).
try {
  $ready = Join-Path $PSScriptRoot "Check-BlockGReady.ps1"
  if(-not (Test-Path -LiteralPath $ready)){ throw "[FAIL-CLOSED] Missing: $ready" }

  # Resolve Market/Symbol for the gate (prefer explicit vars; fallback env; fail-closed default).
  $m = $null; $s = $null
  try { if(Get-Variable -Name "Market" -Scope Local -ErrorAction SilentlyContinue){ $m = ($Market + "") } } catch { }
  try { if(Get-Variable -Name "Symbol" -Scope Local -ErrorAction SilentlyContinue){ $s = ($Symbol + "") } } catch { }
  if(-not $m){ $m = (($env:HAT_MARKET + "")).Trim() }
  if(-not $s){ $s = (($env:HAT_SYMBOL + "")).Trim() }
  if(-not $m){ $m = "US" }
  if(-not $s){ $s = "NVDA" }
  $m = $m.ToUpperInvariant().Trim()
  $s = $s.ToUpperInvariant().Trim()

  Write-Host ("[ARM] Check-BlockGReady (direct) market=" + $m + " symbol=" + $s) -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $toolsDir "Check-BlockGReady.ps1") -Market $m -Symbol $s | Out-Host
  $code = [int]$LASTEXITCODE
  if($code -ne 0){
    Write-Host ("[ARM] FAIL-CLOSED: Check-BlockGReady exit=" + $code) -ForegroundColor Red
    exit $code
  }
  Write-Host "[ARM] OK: Check-BlockGReady passed" -ForegroundColor Green
} catch {
  Write-Host ("[ARM] FAIL-CLOSED: Check-BlockGReady exception: " + $_.Exception.Message) -ForegroundColor Red
  exit 2
}
# A4_ARM_DIRECT_CHECK_BLOCKGREADY_END

powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $toolsDir "Invoke-BlockGCheck.ps1") -Symbol NVDA -Mode ALL_STRICT | Out-Host
$rc = $LASTEXITCODE
if ($rc -ne 0) { Fail ("BlockG readiness failed exit=" + $rc) }
$nvdaLiveReady = $true
$rc = $LASTEXITCODE
if ($rc -eq 0) {
  $nvdaLiveReady = $true
} elseif ($rc -eq 10) {
  Fail "BlockG CLOSED DAY diagnostic (exit=10): LIVE arming disallowed"
} else {
  Fail ("BlockG readiness failed exit=" + $rc)
}


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

# STAMP_GUARD_BEGIN
if(-not $nvdaLiveReady){
  Fail "Refusing to write NVDA LIVE READY stamp: nvdaLiveReady=false"
}
# STAMP_GUARD_END
$payload = [ordered]@{
  ts_utc = (Get-Date).ToUniversalTime().ToString("o")
  as_of_date = $today
  nvda_live_ready = $nvdaLiveReady
  blockg_as_of_date = $blockgAsOf
  phase4_ok_today = $true
  ev_hard_daily_ok_today = $true
  gatescore_ok_today = $true
  blockg_reasons_not_ready = $blockgReasons
}

Write-Utf8NoBom -Path $stampPath -Text ($payload | ConvertTo-Json -Depth 6)
Write-Host "[ARM] SUCCESS: NVDA LIVE READY stamp written: $stampPath" -ForegroundColor Green
exit 0
