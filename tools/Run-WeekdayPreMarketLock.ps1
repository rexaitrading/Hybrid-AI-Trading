[CmdletBinding()]
param(
  [ValidateSet("NVDA","ALL")]
  [string]$Symbols="NVDA",
  [switch]$EnableSpyQqq,
  [switch]$StrictPhase7
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

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
if(-not (Test-Path $final)){ Fail "missing Run-FinalLock.ps1" }

if($EnableSpyQqq){
  powershell -NoProfile -ExecutionPolicy Bypass -File $final -Mode PREMARKET -Symbols $Symbols -EnableSpyQqq -StrictPhase7:$StrictPhase7 | Out-Host
} else {
  powershell -NoProfile -ExecutionPolicy Bypass -File $final -Mode PREMARKET -Symbols $Symbols -StrictPhase7:$StrictPhase7 | Out-Host
}
if($LASTEXITCODE -ne 0){ Fail "FinalLock premarket failed rc=$LASTEXITCODE" }

Write-Host "[WEEKDAY-LOCK] OK" -ForegroundColor Cyan
exit 0
