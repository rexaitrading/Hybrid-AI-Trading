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
  $finalExit = $LASTEXITCODE
  goto ONETAP_SUMMARY
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
  $finalExit = $LASTEXITCODE
  goto ONETAP_SUMMARY
}
throw "Missing checker: $chk"
:ONETAP_SUMMARY
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

# --- OneTap FINAL_EXIT capture + summary JSON (Notion ingest) ---
$finalExit = $LASTEXITCODE
Write-Host ("[ONETAP] FINAL_EXIT={0}" -f $finalExit)

try {
  $repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
  $p = Join-Path $repo "logs\blockg_status_stub.json"
  if(Test-Path $p){
    $st = Get-Content $p -Raw -Encoding utf8 | ConvertFrom-Json
    $out = [ordered]@{
      ts_utc = (Get-Date).ToUniversalTime().ToString("o")
      as_of_date = $st.as_of_date
      symbol = "NVDA"
      phase4_ok_today = $st.phase4_ok_today
      phase23_health_ok_today = $st.phase23_health_ok_today
      ev_hard_daily_ok_today = $st.ev_hard_daily_ok_today
      gatescore_ok_today = $st.gatescore_ok_today
      gatescore_samples = $st.gatescore_samples
      gatescore_pnl_samples = $st.gatescore_pnl_samples
      gatescore_mean_edge_ratio = $st.gatescore_mean_edge_ratio
      gatescore_mean_micro_score = $st.gatescore_mean_micro_score
      nvda_blockg_ready = $st.nvda_blockg_ready
      spy_blockg_ready  = $st.spy_blockg_ready
      qqq_blockg_ready  = $st.qqq_blockg_ready
      reasons_not_ready = $st.reasons_not_ready
      final_exit = $finalExit
    }
    $json = ($out | ConvertTo-Json -Depth 8)
    $dst = Join-Path $repo "logs\onetap_summary.json"
    [System.IO.File]::WriteAllText($dst, ($json -replace "`r`n","`n"), (New-Object System.Text.UTF8Encoding($false)))
    Write-Host "[ONETAP] wrote logs\onetap_summary.json"
  }
} catch {
  Write-Host "[ONETAP] summary json FAILED: $($_.Exception.Message)" -ForegroundColor Yellow
}

exit $finalExit
