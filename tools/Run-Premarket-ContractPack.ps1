[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol="NVDA",

  [string]$AsOfDate=""  # optional: YYYY-MM-DD
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$today = if($AsOfDate -and $AsOfDate.Trim()){ $AsOfDate.Trim() } else { (Get-Date).ToString("yyyy-MM-dd") }

function Step([string]$name, [scriptblock]$sb){
  "`n====================" | Out-Host
  "STEP: $name" | Out-Host
  "====================" | Out-Host
  & $sb
}

# 1) Phase23 daily
Step "PH23 daily health" {
  if(Test-Path .\tools\Run-Phase23HealthDaily.ps1){
    powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Run-Phase23HealthDaily.ps1 *>&1 | Out-Host
    "EXIT_PH23=$LASTEXITCODE" | Out-Host
  } else {
    throw "Missing tools\Run-Phase23HealthDaily.ps1"
  }
}

# 2) Phase4 validation stamp
Step "PH4 validation" {
  if(Test-Path .\tools\Run-Phase4Validation.ps1){
    powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Run-Phase4Validation.ps1 *>&1 | Out-Host
    "EXIT_PH4=$LASTEXITCODE" | Out-Host
  } else {
    throw "Missing tools\Run-Phase4Validation.ps1"
  }
}

# 3) EV-hard snapshot chain
Step "PH5 EV-hard snapshot" {
  foreach($p in @(".\tools\Build-EvHardEvidenceRaw.ps1",".\tools\Build-EvHardSnapshot.ps1",".\tools\Write-EvHardVetoSnapshot.ps1",".\tools\Run-EvHardVetoDaily.ps1")){
    if(-not (Test-Path $p)){ throw "Missing: $p" }
  }
  powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Build-EvHardEvidenceRaw.ps1 *>&1 | Out-Host
  powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Build-EvHardSnapshot.ps1 *>&1 | Out-Host
  powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Write-EvHardVetoSnapshot.ps1 *>&1 | Out-Host
  powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Run-EvHardVetoDaily.ps1 *>&1 | Out-Host
  "EXIT_EVH=$LASTEXITCODE" | Out-Host
}

# 4) GateScore pnl summary (contract reads this)
Step "PH3 GateScore PnL summary" {
  if(Test-Path .\tools\Build-GateScorePnlSummary.ps1){
    powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Build-GateScorePnlSummary.ps1 *>&1 | Out-Host
    "EXIT_GS_SUMMARY=$LASTEXITCODE" | Out-Host
  } else {
    throw "Missing tools\Build-GateScorePnlSummary.ps1"
  }
}

# 5) BlockG build + check (PS is semantic owner)
Step "PH5 BlockG build+check" {
  powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Build-BlockGStatusStub.ps1 -Symbol $Symbol *>&1 | Out-Host
  powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Check-BlockGReady.ps1 -Symbol $Symbol *>&1 | Out-Host
  "EXIT_BLOCKG=$LASTEXITCODE" | Out-Host
  if($LASTEXITCODE -ne 0){ exit 2 }
}

Write-Host "`n[OK] Premarket ContractPack complete" -ForegroundColor Green
exit 0
