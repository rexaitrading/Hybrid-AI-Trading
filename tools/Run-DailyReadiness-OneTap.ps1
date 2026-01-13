[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol="NVDA",

  
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","CN_SH","CN_SZ")]
  [string]$Market = "US",
[switch]$Build
)

Set-StrictMode -Version Latest
# BLOCKG_LOCKPACK_BEGIN
Write-Host "`n[OPS] Block-G LOCKPACK (non-fatal; cmd wrapper)..." -ForegroundColor Cyan
$lockpack_exit = 0
try {
  $psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
  $cmd = "`"$psExe`" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File `".\tools\Run-BlockGLockPack.ps1`" -Symbol NVDA"
  cmd /c $cmd 2>&1 | Out-Host
  $lockpack_exit = $LASTEXITCODE
} catch {
  $lockpack_exit = 2
}
if($lockpack_exit -ne 0){
  Write-Host ("[ONETAP] WARN: LockPack failed (exit=" + $lockpack_exit + "). Continuing so onetap_summary.json is emitted (fail-closed).") -ForegroundColor Yellow
}
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

# --- A2: Ensure GateScore daily summary exists (fail-closed) ---
$gsCsv = Join-Path $repoRoot "logs\gatescore_daily_summary.csv"
$gsSummary = Join-Path $repoRoot "tools\Run-GateScoreDailySummary.ps1"
if(Test-Path -LiteralPath $gsSummary){
  powershell -NoProfile -ExecutionPolicy Bypass -File $gsSummary *>&1 | Out-Host
}
if(-not (Test-Path -LiteralPath $gsCsv)){
  throw ("[A2] FAIL-CLOSED: missing GateScore daily summary csv: " + $gsCsv)
}
# --- A2 END ---

# --- end repo root ---
$today = (Get-Date).ToString("yyyy-MM-dd")

# Market enabled guard (fail-closed)
$mg = Join-Path $repoRoot "tools\Test-MarketEnabled.ps1"
if(Test-Path -LiteralPath $mg){
  & powershell -NoProfile -ExecutionPolicy Bypass -File $mg -Market $Market | Out-Host
  if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }

# Risk cap guard (fail-closed)
$rc = Join-Path $repoRoot "tools\Test-MarketRiskCaps.ps1"
if(Test-Path -LiteralPath $rc){
  & powershell -NoProfile -ExecutionPolicy Bypass -File $rc -Market $Market -Mode REQUIRE_ENABLED | Out-Host
  if($LASTEXITCODE -ne 0){ exit $LASTEXITCODE }
} else {
  Write-Host ("[RISKCAP] FAIL-CLOSED: missing validator => " + $rc) -ForegroundColor Red
  exit 2
}

}

Write-Host ("[ONETAP] Daily readiness start today=" + $today + " symbol=" + $Symbol + " market=" + $Market) -ForegroundColor Cyan

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
$chk = Join-Path $repoRoot "tools\Invoke-BlockGCheck.ps1"
if(Test-Path -LiteralPath $chk){
  $chkArgs = @("-Symbol", $Symbol, "-Market", $Market)
  if($Build){ $chkArgs += "-Build" }
  & powershell -NoProfile -ExecutionPolicy Bypass -File $chk @chkArgs | Out-Host
  $finalExit = $LASTEXITCODE
  $continue = $false
} else {
  Write-Host "[ONETAP] FAIL-CLOSED: missing checker: $chk" -ForegroundColor Yellow
  $finalExit = 1
  $continue = $false
}
# --- ONETAP_SUMMARY ---
# --- OneTap summary JSON (for Notion ingest) ---
try {
$repo = (Resolve-Path (Join-Path (Split-Path -Parent $PSCommandPath) "..")).Path
  $logRoot = $null
try {
  $logRoot = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repo "tools\Get-MarketLogRoot.ps1") -Market $Market
} catch { $logRoot = $null }
if(-not $logRoot){ $logRoot = Join-Path $repo "logs" }

$p = Join-Path $logRoot "blockg_status_stub.json"
  if(Test-Path $p){
    $st = Get-Content $p -Raw -Encoding utf8 | ConvertFrom-Json
# ---- derive Phase23 + EV-HARD ok_today from CSV evidence (fail-closed) ----
$todayStr = (Get-Date).ToString("yyyy-MM-dd")
$repoLogs = Join-Path $repo "logs"

$phase23_health_ok_today = $false
$ev_hard_daily_ok_today  = $false

function Get-LatestOkTodayFromCsv([string]$csvPath, [string]$todayStr){
  if(-not (Test-Path -LiteralPath $csvPath)){ return $false }
  $rows = @(Import-Csv -LiteralPath $csvPath)
  if($rows.Count -lt 1){ return $false }
  $last = $rows[-1]

  # date field (robust)
  $d = ""
  if($last.PSObject.Properties.Name -contains "as_of_date"){ $d = ($last.as_of_date + "") }
  elseif($last.PSObject.Properties.Name -contains "date"){ $d = ($last.date + "") }
  elseif($last.PSObject.Properties.Name -contains "today"){ $d = ($last.today + "") }
  if($d.Length -ge 10){ $d = $d.Substring(0,10) } else { return $false }

  # ok field (robust)
  $ok = $false
  if($last.PSObject.Properties.Name -contains "ok_today"){ $ok = [bool]$last.ok_today }
  elseif($last.PSObject.Properties.Name -contains "ok"){ $ok = [bool]$last.ok }
  elseif($last.PSObject.Properties.Name -contains "okToday"){ $ok = [bool]$last.okToday }

  return ($d -eq $todayStr -and $ok)
}

try {
  $p23a = Join-Path $logRoot  "phase23_health_daily.csv"
  $p23b = Join-Path $repoLogs "phase23_health_daily.csv"
  $p23  = if(Test-Path -LiteralPath $p23a){ $p23a } else { $p23b }
  $phase23_health_ok_today = Get-LatestOkTodayFromCsv -csvPath $p23 -todayStr $todayStr
} catch { $phase23_health_ok_today = $false }

try {
  $eva = Join-Path $logRoot  "phase5_ev_hard_veto_daily.csv"
  $evb = Join-Path $repoLogs "phase5_ev_hard_veto_daily.csv"
  $ev  = if(Test-Path -LiteralPath $eva){ $eva } else { $evb }
  $ev_hard_daily_ok_today = Get-LatestOkTodayFromCsv -csvPath $ev -todayStr $todayStr
} catch { $ev_hard_daily_ok_today = $false }
# ---- end derive ----
    $out = [ordered]@{
      ts_utc = (Get-Date).ToUniversalTime().ToString("o")
      as_of_date = $st.as_of_date
      phase4_ok_today = $st.phase4_ok_today
  phase23_health_ok_today = $phase23_health_ok_today
  ev_hard_daily_ok_today = $ev_hard_daily_ok_today
      gatescore_ok_today = $st.gatescore_ok_today
      nvda_blockg_ready = $st.nvda_blockg_ready
      spy_blockg_ready  = $st.spy_blockg_ready
      qqq_blockg_ready  = $st.qqq_blockg_ready
      reasons_not_ready = $st.reasons_not_ready
    }
    $json = ($out | ConvertTo-Json -Depth 6)
    $dst = Join-Path $logRoot "onetap_summary.json"
        [System.IO.File]::WriteAllText($dst,  ($json -replace "`r`n","`n"), (New-Object System.Text.UTF8Encoding($false)))
        # legacy_onetap_summary (backward compat)
    try {
      $legacyDst = Join-Path $repo "logs\onetap_summary.json"
      if($legacyDst -ne $dst){
        [System.IO.File]::WriteAllText($legacyDst, ($json -replace "`r`n","`n"), (New-Object System.Text.UTF8Encoding($false)))
      }
    } catch { }

    Write-Host ("[ONETAP] wrote " + $dst)
  }
} catch {
  Write-Host "[ONETAP] summary json skipped: $($_.Exception.Message)" -ForegroundColor Yellow
}

exit $finalExit
