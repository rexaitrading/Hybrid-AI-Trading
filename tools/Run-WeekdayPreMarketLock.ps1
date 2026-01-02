[CmdletBinding()]
param(
  [ValidateSet("NVDA","ALL")]
  [string]$Symbols="NVDA",
  [switch]$EnableSpyQqq,
  [switch]$EnableSpyOnly,
  [switch]$StrictPhase7
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

# --- PAPER OPS ENV (fail-closed; does NOT affect live runners) ---
$env:HAT_IS_PAPER = "1"
# Ensure Block-G rebuild is not skipped in this process when -Build is requested downstream
Remove-Item Env:HAT_BLOCKG_BUILT_ONCE -ErrorAction SilentlyContinue
$env:HAT_BLOCKG_BUILT_ONCE = "0"
# Optionally enable SPY/QQQ readiness checks when requested
if($EnableSpyQqq){
  $env:HAT_BLOCKG_ENABLE_SPYQQQ = "1"
  Remove-Item Env:HAT_BLOCKG_ENABLE_SPYONLY -ErrorAction SilentlyContinue
} elseif($EnableSpyOnly){
  $env:HAT_BLOCKG_ENABLE_SPYONLY = "1"
  Remove-Item Env:HAT_BLOCKG_ENABLE_SPYQQQ -ErrorAction SilentlyContinue
} else {
  Remove-Item Env:HAT_BLOCKG_ENABLE_SPYQQQ -ErrorAction SilentlyContinue
  Remove-Item Env:HAT_BLOCKG_ENABLE_SPYONLY -ErrorAction SilentlyContinue
}
# --- end PAPER OPS ENV ---


$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir

function Fail([string]$Msg){
  Write-Host "[WEEKDAY-LOCK] FAIL-CLOSED: $Msg" -ForegroundColor Yellow
  exit 2
}

# Must be weekday
$d=(Get-Date).DayOfWeek
if($d -eq "Saturday" -or $d -eq "Sunday"){ Fail "weekend_use_Run-FinalLock_-Mode_WEEKEND" }

# 1) Block-G / execution safety tests FIRST (fast)
$bgTests = Join-Path $toolsDir "Run-BlockGTestsFirst.ps1"
if(Test-Path $bgTests){
  powershell -NoProfile -ExecutionPolicy Bypass -File $bgTests | Out-Host
  if($LASTEXITCODE -ne 0){ Fail "Run-BlockGTestsFirst failed rc=$LASTEXITCODE" }
}

# 2) Phase-4 validation slice
$p4 = Join-Path $toolsDir "Run-Phase4Validation.ps1"
if(Test-Path $p4){
  powershell -NoProfile -ExecutionPolicy Bypass -File $p4 | Out-Host
  if($LASTEXITCODE -ne 0){ Fail "Run-Phase4Validation failed rc=$LASTEXITCODE" }
}

# 3) Phase-5 risk slice
$p5 = Join-Path $toolsDir "Run-Phase5Tests.ps1"
if(Test-Path $p5){
  powershell -NoProfile -ExecutionPolicy Bypass -File $p5 | Out-Host
  if($LASTEXITCODE -ne 0){ Fail "Run-Phase5Tests failed rc=$LASTEXITCODE" }
}

# 4) Final lock (premarket)
$final = Join-Path $toolsDir "Run-FinalLock.ps1"
if(-not (Test-Path -LiteralPath $final)){ Fail "missing Run-FinalLock.ps1" }

# Invoke directly so switches stay typed (no splat/shift bugs)
if($EnableSpyQqq){
  if($StrictPhase7){
    & $final -Mode PREMARKET -Symbols $Symbols -EnableSpyQqq -StrictPhase7 | Out-Host
  } else {
    & $final -Mode PREMARKET -Symbols $Symbols -EnableSpyQqq | Out-Host
  }
} else {
  if($StrictPhase7){
    & $final -Mode PREMARKET -Symbols $Symbols -StrictPhase7 | Out-Host
  } else {
    & $final -Mode PREMARKET -Symbols $Symbols | Out-Host
  }
}
if($LASTEXITCODE -ne 0){ Fail "FinalLock premarket failed rc=$LASTEXITCODE" }

Write-Host "[WEEKDAY-LOCK] OK" -ForegroundColor Cyan
exit 0
