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
$phase4 = Join-Path $repoRoot "tools\Run-Phase4Validation.ps1"
if(Test-Path $phase4){
  & powershell -NoProfile -ExecutionPolicy Bypass -File $phase4 | Out-Host
} else {
  Write-Host "[ONETAP] WARN missing Phase4 builder: $phase4" -ForegroundColor Yellow
}

# 1B) Phase-23 health daily
$p23 = Join-Path $repoRoot "tools\Run-Phase23HealthDaily.ps1"
if(Test-Path $p23){
  & powershell -NoProfile -ExecutionPolicy Bypass -File $p23 | Out-Host
} else {
  Write-Host "[ONETAP] WARN missing Phase23 health runner: $p23" -ForegroundColor Yellow
}
if ($LASTEXITCODE -ne 0) {
  Write-Host "[ONETAP] FAIL-CLOSED: Phase4 failed exit=$LASTEXITCODE" -ForegroundColor Red
  exit $LASTEXITCODE
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