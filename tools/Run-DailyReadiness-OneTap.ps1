[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol="NVDA",

  [switch]$Build
)

Set-StrictMode -Version Latest
# BLOCKG_LOCKPACK_BEGIN
Write-Host "
[OPS] Block-G LOCKPACK..." -ForegroundColor Cyan
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\Run-BlockGLockPack.ps1 -Symbol NVDA | Out-Host
if($LASTEXITCODE -ne 0){ throw "[OPS] Block-G LOCKPACK failed (drift detected)" }
# BLOCKG_LOCKPACK_END
$ErrorActionPreference="Stop"

# --- repo root: walk up from this script until .git is found (fail-closed) ---
$repoRoot = $PSScriptRoot
while($repoRoot -and -not (Test-Path (Join-Path $repoRoot ".git"))){
  $parent = Split-Path -Parent $repoRoot
  if($parent -eq $repoRoot){ break }
  $repoRoot = $parent
}
if(-not (Test-Path (Join-Path $repoRoot ".git"))){
  throw "NOT IN REPO ROOT (could not find .git from $PSScriptRoot)"
}
# --- end repo root ---
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
# $finalExit already captured earlier
  $continue = $false
}
# 2) EV-hard daily (writes/updates logs\phase5_ev_hard_veto_daily.csv)
$evd = Join-Path $repoRoot "tools\Run-EvHardVetoDaily.ps1"
if(Test-Path $evd){
  & powershell -NoProfile -ExecutionPolicy Bypass -File $evd | Out-Host
} else {
  Write-Host "[ONETAP] WARN missing EV-hard daily runner: $evd" -ForegroundColor Yellow
}
# 3) GateScore summary build
$gs = Join-Path $repoRoot "tools\Build-GateScorePnlSummary.ps1"
if(Test-Path $gs){
  & powershell -NoProfile -ExecutionPolicy Bypass -File $gs -Symbol $Symbol | Out-Host
} else {
  throw "Missing GateScore summary builder: $gs"
}

# 4) Block-G status stub (handled by Check-BlockGReady -Build)
# 5) Check readiness
$chk = Join-Path $repoRoot "tools\Check-BlockGReady.ps1"
if(Test-Path -LiteralPath $chk){
  $chkArgs = @("-Symbol", $Symbol)   if($Build){ $chkArgs += "-Build" }   & powershell -NoProfile -ExecutionPolicy Bypass -File $chk @chkArgs | Out-Host
  $finalExit = $LASTEXITCODE
# $finalExit already captured earlier
  $continue = $false
} else {
  Write-Host "[ONETAP] FAIL-CLOSED: missing checker: $chk" -ForegroundColor Yellow
  $finalExit = 1
  $continue = $false
}
# --- ONETAP_SUMMARY ---
# --- OneTap summary JSON (for Notion ingest) ---
try {
  $repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
  $p = Join-Path $repo "logs\blockg_status_stub.json"
  if(Test-Path $p){
    $st = Get-Content $p -Raw -Encoding utf8 | ConvertFrom-Json
    $out = [ordered]@{
      ts_utc = (Get-Date).ToUniversalTime().ToString("o")
      as_of_date = $st.as_of_date
      phase4_ok_today = $st.phase4_ok_today
      phase23_health_ok_today = $st.phase23_health_ok_today
      ev_hard_daily_ok_today = $st.ev_hard_daily_ok_today
      gatescore_ok_today = $st.gatescore_ok_today
      nvda_blockg_ready = $st.nvda_blockg_ready
      spy_blockg_ready  = $st.spy_blockg_ready
      qqq_blockg_ready  = $st.qqq_blockg_ready
      reasons_not_ready = $st.reasons_not_ready
    }
    $json = ($out | ConvertTo-Json -Depth 6)
    $dst = Join-Path $repo "logs\onetap_summary.json"
    [System.IO.File]::WriteAllText($dst, ($json -replace "`r`n","`n"), (New-Object System.Text.UTF8Encoding($false)))
    Write-Host "[ONETAP] wrote logs\onetap_summary.json"
  }
} catch {
  Write-Host "[ONETAP] summary json skipped: $($_.Exception.Message)" -ForegroundColor Yellow
}

exit $finalExit
