[CmdletBinding()]
param(
  [ValidateSet("PREMARKET","WEEKEND","CI")]
  [string]$Mode = "PREMARKET",

  [ValidateSet("NVDA","ALL")]
  [string]$Symbols = "NVDA",

  [string]$AsOfDate = "",

  [switch]$EnableSpyQqq,

  [switch]$StrictPhase7,

  [switch]$SkipNotionExport
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

function Write-Utf8NoBom {
  param([string]$Path, [string]$Text)
  $enc = New-Object System.Text.UTF8Encoding($false)
  $Text = $Text -replace "`r`n","`n"
  if(-not $Text.EndsWith("`n")){ $Text += "`n" }
  [System.IO.File]::WriteAllText((Resolve-Path -LiteralPath $Path).Path, $Text, $enc)
}

function NowUtc { (Get-Date).ToUniversalTime().ToString("o") }
function TodayLocal { (Get-Date).ToString("yyyy-MM-dd") }
function IsWeekend {
  $d = (Get-Date).DayOfWeek
  return ($d -eq "Saturday" -or $d -eq "Sunday")
}

function Fail-Closed([string]$Reason, [hashtable]$Details = $null, [int]$Code = 2){
  $outDir = Join-Path $repoRoot "logs\ops"
  if(-not (Test-Path $outDir)){ New-Item -ItemType Directory -Force -Path $outDir | Out-Null }
  $p = Join-Path $outDir "final_lock_report.json"

  $payload = [ordered]@{
    ts_utc     = (NowUtc)
    mode       = $Mode
    ok         = $false
    reason     = $Reason
    as_of_date = $Global:FINAL_ASOF
    symbols    = $Symbols
    enable_spyqqq = [bool]$EnableSpyQqq
    strict_phase7 = [bool]$StrictPhase7
    details    = $Details
  } | ConvertTo-Json -Depth 12

  # Write as UTF-8 no BOM
  $enc = New-Object System.Text.UTF8Encoding($false)
  $payload = ($payload -replace "`r`n","`n").TrimEnd() + "`n"
  [System.IO.File]::WriteAllText($p, $payload, $enc)

  Write-Host ("[FINAL-LOCK] FAIL-CLOSED: {0}" -f $Reason) -ForegroundColor Yellow
  if($Details){ Write-Host ("DETAILS=" + ($Details | ConvertTo-Json -Depth 8)) -ForegroundColor Yellow }
  exit $Code
}

# Resolve as_of_date
$today = (TodayLocal)
$asof = ($AsOfDate + "").Trim()
if([string]::IsNullOrWhiteSpace($asof)){ $asof = $today }

# Weekend policy: if Mode=WEEKEND, allow carry-forward by letting BlockG builder decide effective-asof
if($Mode -eq "WEEKEND"){ $asof = $today } # builder will carry-forward; summary export uses supplied AsOfDate below

$Global:FINAL_ASOF = $asof

# Enforce mode sanity
if(($Mode -eq "PREMARKET") -and (IsWeekend)){
  Fail-Closed "premarket_on_weekend_use_mode_weekend" @{ today=$today }
}

# Optional opt-in for SPY/QQQ readiness computation
if($EnableSpyQqq){
  $env:HAT_BLOCKG_ENABLE_SPYQQQ = "1"
} else {
  Remove-Item Env:\HAT_BLOCKG_ENABLE_SPYQQQ -ErrorAction SilentlyContinue
}

# Always clear build cache so we get a fresh stub
Remove-Item Env:\HAT_BLOCKG_BUILT_ONCE -ErrorAction SilentlyContinue

# 1) IBG health (observe-only gate)
$ibgTool = Join-Path $toolsDir "Get-IBGHealth.ps1"
if(Test-Path -LiteralPath $ibgTool){
  $ibg = & $ibgTool
  if(-not $ibg.ok){
    Fail-Closed "ibg_not_healthy" @{ reasons=$ibg.reasons; status_path=$ibg.status_path } 3
  }
}

# 2) Block-G check (build + verify)
$chk = Join-Path $toolsDir "Check-BlockGReady.ps1"
if(-not (Test-Path -LiteralPath $chk)){ Fail-Closed "missing_Check-BlockGReady" @{ path=$chk } 2 }

$targetSym = $Symbols.ToUpper()
if($targetSym -ne "NVDA" -and $targetSym -ne "ALL"){ $targetSym = "NVDA" }

powershell -NoProfile -ExecutionPolicy Bypass -File $chk -Build -Symbol $targetSym | Out-Host
$rc = $LASTEXITCODE
if($rc -ne 0){
  Fail-Closed "blockg_not_ready" @{ rc=$rc; symbol=$targetSym } 2
}


# WEEKEND mode: use Block-G effective as_of_date (carry-forward) for Phase-6/7 steps
if($Mode -eq "WEEKEND"){
  try {
    $bgPath = Join-Path $repoRoot "logs\blockg_status_stub.json"
    if(Test-Path -LiteralPath $bgPath){
      $bg = Get-Content -LiteralPath $bgPath -Raw -Encoding utf8 | ConvertFrom-Json
      $eff = (($bg.as_of_date + "").Trim())
      if(-not [string]::IsNullOrWhiteSpace($eff)){
        $asof = $eff
        $Global:FINAL_ASOF = $asof
      }
    }
  } catch { }
}

# 3) Phase-6 readiness snapshot (must succeed)
$w6 = Join-Path $toolsDir "Write-Phase6ReadinessSnapshot.ps1"
if(-not (Test-Path -LiteralPath $w6)){ Fail-Closed "missing_Write-Phase6ReadinessSnapshot" @{ path=$w6 } 2 }
powershell -NoProfile -ExecutionPolicy Bypass -File $w6 | Out-Host
if($LASTEXITCODE -ne 0){
  Fail-Closed "phase6_readiness_snapshot_failed" @{ rc=$LASTEXITCODE } 2
}

# 4) Phase-6 daily summary export (json+csv) for as_of_date
if(-not $SkipNotionExport){
  $p6 = Join-Path $toolsDir "Run-Phase6DailyNotionExport.ps1"
  if(-not (Test-Path -LiteralPath $p6)){ Fail-Closed "missing_Run-Phase6DailyNotionExport" @{ path=$p6 } 2 }
  powershell -NoProfile -ExecutionPolicy Bypass -File $p6 -AsOfDate $asof | Out-Host
  if($LASTEXITCODE -ne 0){
    Fail-Closed "phase6_daily_export_failed" @{ rc=$LASTEXITCODE; as_of_date=$asof } 2
  }
}

# 5) Phase-7 preflight (offline always OK; strict optional)
$py = Join-Path $repoRoot ".venv\Scripts\python.exe"
if(-not (Test-Path -LiteralPath $py)){ $py = "python" }

if($StrictPhase7){
  # strict: require blockg for all symbols requested in preflight_gate
  Remove-Item Env:\HAT_PHASE7_REQUIRE_BLOCKG -ErrorAction SilentlyContinue
} else {
  $env:HAT_PHASE7_REQUIRE_BLOCKG = "0"
}

& $py -c ("from hybrid_ai_trading.phase7.preflight_gate import ensure_phase7_ready;" +
          "ensure_phase7_ready(required_symbols=('NVDA','SPY','QQQ'), as_of_date='" + $asof + "');" +
          "print('PHASE7_PREFLIGHT_OK')") | Out-Host
if($LASTEXITCODE -ne 0){
  Fail-Closed "phase7_preflight_failed" @{ rc=$LASTEXITCODE; as_of_date=$asof; strict=[bool]$StrictPhase7 } 2
}

Remove-Item Env:\HAT_PHASE7_REQUIRE_BLOCKG -ErrorAction SilentlyContinue

# Write success report
$outDir = Join-Path $repoRoot "logs\ops"
if(-not (Test-Path $outDir)){ New-Item -ItemType Directory -Force -Path $outDir | Out-Null }
$report = Join-Path $outDir "final_lock_report.json"

$okPayload = [ordered]@{
  ts_utc     = (NowUtc)
  mode       = $Mode
  ok         = $true
  reason     = "final_lock_ok"
  as_of_date = $asof
  symbols    = $targetSym
  enable_spyqqq = [bool]$EnableSpyQqq
  strict_phase7 = [bool]$StrictPhase7
} | ConvertTo-Json -Depth 8

$enc = New-Object System.Text.UTF8Encoding($false)
$okPayload = ($okPayload -replace "`r`n","`n").TrimEnd() + "`n"
[System.IO.File]::WriteAllText($report, $okPayload, $enc)

Write-Host "[FINAL-LOCK] OK" -ForegroundColor Cyan
exit 0
