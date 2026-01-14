[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol="NVDA",

  
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","HK_SH","HK_SZ","CN_SH","CN_SZ")]
  [string]$Market = "US",
[switch]$Build
)

# [A3] RunContext single-truth as_of_date (fail-closed)
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
$mkt = ""
if($PSBoundParameters.ContainsKey("Market")){ $mkt = ([string]$Market).ToUpperInvariant().Trim() }
elseif($env:HAT_MARKET){ $mkt = ([string]$env:HAT_MARKET).ToUpperInvariant().Trim() }
if(-not $mkt){ throw "[A3] Market unresolved for RunContext (pass -Market or set HAT_MARKET) (fail-closed)" }
$rc = & $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Resolve-RunContext.ps1") -Market $mkt -Symbol NVDA | ConvertFrom-Json

# [A3] CRITICAL: bind downstream Market to resolved mkt (env:HAT_MARKET honored when -Market not passed)
$Market = $mkt

if(-not $rc -or -not $rc.as_of_date){ throw "[A3] Resolve-RunContext missing as_of_date (fail-closed)" }
$asOfDate = ([string]$rc.as_of_date).Trim()


Set-StrictMode -Version Latest
# BLOCKG_LOCKPACK_BEGIN
Write-Host "`n[OPS] Block-G LOCKPACK (non-fatal; cmd wrapper)..." -ForegroundColor Cyan
$lockpack_exit = 0
  # ---- CRISIS PRODUCER (A2-adjacent; LIVE fail-closed) ----
  try {
    & .\tools\Write-CrisisRegimeStatus.ps1 -Market $Market -Symbol $Symbol *>&1 | Out-Host
  } catch {
    Write-Host ("[CRISIS] producer failed: " + $_.Exception.Message) -ForegroundColor Yellow
  }
  # ---- END CRISIS PRODUCER ----

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

# [A3] Compatibility: scripts below use $repo; bind it to $repoRoot
$repo = $repoRoot

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
$today = ""
# --- A3: today = RunContext.as_of_date (single truth; market-aware) ---
try {
  $rcRaw = powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Resolve-RunContext.ps1") -Market $Market -Symbol $Symbol 2>$null | Out-String
  $rcRaw = ($rcRaw + "").Trim()
  if($rcRaw){
    $rcObj = $rcRaw | ConvertFrom-Json
    if($rcObj.PSObject.Properties.Name -contains "as_of_date" -and (($rcObj.as_of_date + "") -ne "")){
      $today = [string]$rcObj.as_of_date
    }
  }
} catch { }
# --- A3 END ---
if(-not $today){ $today = (Get-Date).ToString("yyyy-MM-dd") }


# --- Phase-3 producer: per-market GateScore events (fail-closed; proxy US allowed for plumbing in PAPER only) ---
$gsPm = Join-Path $repoRoot "tools\Write-GateScoreEvents-PerMarket.ps1"
if(Test-Path -LiteralPath $gsPm){
  & powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $gsPm -Market $Market -Symbol $Symbol -Mode rewrite -MinEvents 10 *>&1 | Out-Host
} else {
  Write-Host ("[ONETAP] WARN missing per-market GateScore producer: " + $gsPm) -ForegroundColor Yellow
}
# --- Phase-3 producer END ---

# Market enabled guard (fail-closed)
$mg = Join-Path $repoRoot "tools\Test-MarketEnabled.ps1"
if(Test-Path -LiteralPath $mg){
  & powershell -NoProfile -ExecutionPolicy Bypass -File $mg -Market $Market | Out-Host
  if($LASTEXITCODE -ne 0){ $finalExit = [int]$LASTEXITCODE; $continue = $false; Write-Host ("[RISKCAP] FAIL-CLOSED: exitcode=" + $finalExit + " (will still emit onetap_summary)") -ForegroundColor Red }

# Risk cap guard (fail-closed)
$rc = Join-Path $repoRoot "tools\Test-MarketRiskCaps.ps1"
if(Test-Path -LiteralPath $rc){
  & powershell -NoProfile -ExecutionPolicy Bypass -File $rc -Market $Market -Mode REQUIRE_ENABLED | Out-Host
  if($LASTEXITCODE -ne 0){ $finalExit = [int]$LASTEXITCODE; $continue = $false; Write-Host ("[RISKCAP] FAIL-CLOSED: exitcode=" + $finalExit + " (will still emit onetap_summary)") -ForegroundColor Red }
} else {
  Write-Host ("[RISKCAP] FAIL-CLOSED: missing validator => " + $rc) -ForegroundColor Red
  $finalExit = 2; $continue = $false; Write-Host ("[RISKCAP] FAIL-CLOSED: missing validator (will still emit onetap_summary)") -ForegroundColor Red
}

}

Write-Host ("[ONETAP] Daily readiness start today=" + $today + " symbol=" + $Symbol + " market=" + $Market) -ForegroundColor Cyan

# 1) Phase-4 validation (existing artifact builder may be different; adjust later if needed)
$phase4 = Join-Path $repoRoot "tools\Run-Phase4Validation.ps1"
if(Test-Path $phase4){
  & powershell -NoProfile -ExecutionPolicy Bypass -File $phase4 | Out-Host

# --- A2: Phase4 status producer (market-scoped; fail-closed readers) ---
$p4s = Join-Path $repoRoot "tools\Write-Phase4Status.ps1"
if(Test-Path -LiteralPath $p4s){
  & powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $p4s -Market $Market -Symbol $Symbol *>&1 | Out-Host
} else {
  Write-Host ("[ONETAP] WARN missing Phase4 status producer: " + $p4s) -ForegroundColor Yellow
}
# --- A2 END ---

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
  if([int]$finalExit -eq 0){ $finalExit = [int]$LASTEXITCODE }
  $continue = $false
} else {
  Write-Host "[ONETAP] FAIL-CLOSED: missing checker: $chk" -ForegroundColor Yellow
  $finalExit = 1
  $continue = $false
}
# --- ONETAP_SUMMARY ---
# --- OneTap summary JSON (for Notion ingest) ---
try {
  # Canonical repoRoot (filesystem truth)
  $repo = $repoRoot

  # RunContext day is single-truth; fall back to st.as_of_date only if needed
  $todayStr = (([string]$asOfDate) + "").Trim()
  if($todayStr.Length -ge 10){ $todayStr = $todayStr.Substring(0,10) }
  if(-not $todayStr){ $todayStr = (Get-Date).ToString("yyyy-MM-dd") }

  # Resolve per-market log root (prefer tool, fallback to logs\<Market>)
  $logRoot = $null
  try {
    $logRoot = & powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $repo "tools\Get-MarketLogRoot.ps1") -Market $Market
  } catch { $logRoot = $null }
  $logRoot = (([string]$logRoot) + "").Trim()
  if(-not $logRoot){ $logRoot = Join-Path (Join-Path $repo "logs") $Market }
  New-Item -ItemType Directory -Force -Path $logRoot | Out-Null

  # Load blockg status stub if present; else synthesize fail-closed stub
  $p = Join-Path $logRoot "blockg_status_stub.json"
  $st = $null
  if(Test-Path -LiteralPath $p){
    $st = Get-Content -LiteralPath $p -Raw -Encoding UTF8 | ConvertFrom-Json
  } else {
    $st = [pscustomobject]@{
      as_of_date         = $todayStr
      phase4_ok_today    = $false
      gatescore_ok_today = $false
      nvda_blockg_ready  = $false
      spy_blockg_ready   = $false
      qqq_blockg_ready   = $false
      reasons_not_ready  = @("missing_blockg_status_stub")
    }
  }

  # Derive Phase23 + EV-HARD from CSV evidence (fail-closed; match RunContext day)
  $phase23_health_ok_today = $false
  $ev_hard_daily_ok_today  = $false

  function Get-LatestOkTodayFromCsv([string]$csvPath, [string]$todayStr){
    if(-not (Test-Path -LiteralPath $csvPath)){ return $false }
    $rows = @(Import-Csv -LiteralPath $csvPath)
    if($rows.Count -lt 1){ return $false }
    $last = $rows[-1]
    $d = ""
    if($last.PSObject.Properties.Name -contains "as_of_date"){ $d = ($last.as_of_date + "") }
    elseif($last.PSObject.Properties.Name -contains "date"){ $d = ($last.date + "") }
    elseif($last.PSObject.Properties.Name -contains "today"){ $d = ($last.today + "") }
    if($d.Length -ge 10){ $d = $d.Substring(0,10) } else { return $false }

    $ok = $false
    if($last.PSObject.Properties.Name -contains "ok_today"){ $ok = [bool]$last.ok_today }
    elseif($last.PSObject.Properties.Name -contains "ok"){ $ok = [bool]$last.ok }
    elseif($last.PSObject.Properties.Name -contains "okToday"){ $ok = [bool]$last.okToday }
    elseif($last.PSObject.Properties.Name -contains "phase23_ok"){
      $s = (($last.phase23_ok + "")).Trim().ToLowerInvariant()
      $ok = ($s -eq "true" -or $s -eq "1" -or $s -eq "yes" -or $s -eq "y")
    }
    return ($d -eq $todayStr -and $ok)
  }

  try {
    $p23 = Join-Path $logRoot "phase23_health_daily.csv"
    $phase23_health_ok_today = Get-LatestOkTodayFromCsv -csvPath $p23 -todayStr $todayStr
  } catch { $phase23_health_ok_today = $false }

  try {
    $ev = Join-Path $logRoot "phase5_ev_hard_veto_daily.csv"
    $ev_hard_daily_ok_today = Get-LatestOkTodayFromCsv -csvPath $ev -todayStr $todayStr
  } catch { $ev_hard_daily_ok_today = $false }

  # Emit summary (hard-proof print before write)
  $out = [ordered]@{
    ts_utc                 = (Get-Date).ToUniversalTime().ToString("o")
    as_of_date             = $todayStr
    phase4_ok_today        = [bool]$st.phase4_ok_today
    phase23_health_ok_today= [bool]$phase23_health_ok_today
    ev_hard_daily_ok_today = [bool]$ev_hard_daily_ok_today
    gatescore_ok_today     = [bool]$st.gatescore_ok_today
    nvda_blockg_ready      = [bool]$st.nvda_blockg_ready
    spy_blockg_ready       = [bool]$st.spy_blockg_ready
    qqq_blockg_ready       = [bool]$st.qqq_blockg_ready
    reasons_not_ready      = $st.reasons_not_ready
  }
  $json = ($out | ConvertTo-Json -Depth 6)
  $dst = Join-Path $logRoot "onetap_summary.json"
  Write-Host ("[ONETAP] TARGET logRoot=" + $logRoot + " dst=" + $dst + " as_of=" + $todayStr + " Market=" + $Market) -ForegroundColor Cyan
  [System.IO.File]::WriteAllText($dst, ($json -replace "`r`n","`n"), (New-Object System.Text.UTF8Encoding($false)))
  Write-Host ("[ONETAP] wrote " + $dst) -ForegroundColor Cyan
} catch {
  Write-Host "[ONETAP] summary json skipped: $($_.Exception.Message)" -ForegroundColor Yellow
}
exit $finalExit