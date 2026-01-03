[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol="NVDA"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$today = (Get-Date).ToString("yyyy-MM-dd")

Write-Host "[ONETAP] Daily readiness start today=$today symbol=$Symbol" -ForegroundColor Cyan

# 1) Phase-4 validation (existing artifact builder may be different; adjust later if needed)
$phase4 = Join-Path $repoRoot "tools\Build-Phase4ValidationPassed.ps1"
if(Test-Path $phase4){
  & powershell -NoProfile -ExecutionPolicy Bypass -File $phase4 | Out-Host
} else {
  Write-Host "[ONETAP] WARN missing Phase4 builder: $phase4" -ForegroundColor Yellow
}

# 2) EV-hard snapshot
$ev = Join-Path $repoRoot "tools\Build-EvHardSnapshot.ps1"
if(Test-Path $ev){
  & powershell -NoProfile -ExecutionPolicy Bypass -File $ev | Out-Host
} else {
  Write-Host "[ONETAP] WARN missing EV-hard snapshot builder: $ev" -ForegroundColor Yellow
}

# 3) GateScore summary build
$gs = Join-Path $repoRoot "tools\Build-GateScorePnlSummary.ps1"
if(Test-Path $gs){
  & powershell -NoProfile -ExecutionPolicy Bypass -File $gs -Symbol $Symbol | Out-Host
} else {
  throw "Missing GateScore summary builder: $gs"
}

# 4) Block-G status stub
$bg = Join-Path $repoRoot "tools\Build-BlockGStatusStub.ps1"
if(Test-Path $bg){
  & powershell -NoProfile -ExecutionPolicy Bypass -File $bg | Out-Host
} else {
  throw "Missing BlockG builder: $bg"
}

# 5) Check readiness
$chk = Join-Path $repoRoot "tools\Check-BlockGReady.ps1"
if(Test-Path $chk){
  & powershell -NoProfile -ExecutionPolicy Bypass -File $chk -Symbol $Symbol | Out-Host
  exit $LASTEXITCODE
}
throw "Missing checker: $chk"