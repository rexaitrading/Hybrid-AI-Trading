# tools\Run-DailyReadiness-OneTap.ps1
[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "NVDA",

  [ValidateSet("US","JP","HK","SG","IN","KR","TW","HK_SH","HK_SZ","CN_SH","CN_SZ")]
  [string]$Market = "US",

  [switch]$Build
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Force UTF-8 output (prevents mojibake in child output decoding)
$OutputEncoding = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)


function Get-CanonicalRepoRoot {
  # FAIL-CLOSED canonical repo root: prefer env:HAT_REPO_ROOT if valid, else walk up from this script.
  $envRoot = (($env:HAT_REPO_ROOT + "")).Trim()
  if($envRoot){
    try {
      $r = (Resolve-Path -LiteralPath $envRoot -ErrorAction Stop).Path
      if(Test-Path -LiteralPath (Join-Path $r ".git")){ return $r }
    } catch { }
  }

  $p = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..") -ErrorAction Stop).Path
  while($p -and -not (Test-Path -LiteralPath (Join-Path $p ".git"))){
    $parent = Split-Path -Parent $p
    if(-not $parent -or $parent -eq $p){ break }
    $p = $parent
  }
  if(-not $p -or -not (Test-Path -LiteralPath (Join-Path $p ".git"))){
    throw "[FAIL-CLOSED] repo root not found (.git missing). envRoot=$envRoot scriptRoot=$PSScriptRoot"
  }
  return $p
}

function Resolve-MarketSafe([string]$MarketParam){
  $m = ""
  # IMPORTANT: inside a function, $PSBoundParameters refers to THIS function (param name is MarketParam).
  # So prefer MarketParam directly when provided; env is fallback only.
  if((($MarketParam + "") -ne "")){
    $m = ([string]$MarketParam).ToUpperInvariant().Trim()
  } elseif(($env:HAT_MARKET + "") -ne ""){
    $m = ([string]$env:HAT_MARKET).ToUpperInvariant().Trim()
  } else {
    $m = "US"
  }

  # Stock Connect normalization (no engine constraints)
  if($m -eq "CN_SH"){ $m = "HK_SH" }
  if($m -eq "CN_SZ"){ $m = "HK_SZ" }

  return $m
}

function Resolve-SymbolSafe([string]$SymbolParam){
  $s = ([string]$SymbolParam).ToUpperInvariant().Trim()
  if(-not $s){ $s = "NVDA" }
  return $s
}

function Get-CanonicalLogRoot([string]$RepoRoot,[string]$MarketResolved){
  $repoFull = (Resolve-Path -LiteralPath $RepoRoot -ErrorAction Stop).Path
  if(-not (Test-Path -LiteralPath (Join-Path $repoFull ".git"))){
    throw "[FAIL-CLOSED] repo root missing .git: $repoFull"
  }
  $m = ([string]$MarketResolved).ToUpperInvariant().Trim()
  if(-not $m){ $m = "US" }
  $logRoot = Join-Path (Join-Path $repoFull "logs") $m
  if($logRoot -notlike ($repoFull + "*")){
    throw "[FAIL-CLOSED] logRoot escaped repo: logRoot=$logRoot repo=$repoFull"
  }
  New-Item -ItemType Directory -Force -Path $logRoot | Out-Null
  return $logRoot
}

function Resolve-AsOfDateSafe([string]$RepoRoot,[string]$MarketResolved,[string]$SymbolResolved){
  # NO child powershell.exe. Call Resolve-RunContext in-process and parse JSON safely.
  try {
    $rcPath = Join-Path $RepoRoot "tools\Resolve-RunContext.ps1"
    if(-not (Test-Path -LiteralPath $rcPath)){ throw "[FAIL-CLOSED] Missing Resolve-RunContext.ps1: $rcPath" }

    $rcRaw = & $rcPath -Market $MarketResolved -Symbol $SymbolResolved 2>$null | Out-String
    $rcRaw = (($rcRaw + "")).Trim()
    if(-not $rcRaw){ return (Get-Date).ToString("yyyy-MM-dd") }

    # keep only JSON object
    $ix0 = $rcRaw.IndexOf('{')
    $ix1 = $rcRaw.LastIndexOf('}')
    if($ix0 -lt 0 -or $ix1 -le $ix0){ return (Get-Date).ToString("yyyy-MM-dd") }

    $rcObj = ($rcRaw.Substring($ix0, ($ix1 - $ix0 + 1))) | ConvertFrom-Json
    if($rcObj -and ($rcObj.PSObject.Properties.Name -contains "as_of_date")){
      $d = ([string]$rcObj.as_of_date).Trim()
      if($d.Length -ge 10){ return $d.Substring(0,10) }
      if($d){ return $d }
    }
  } catch { }
  return (Get-Date).ToString("yyyy-MM-dd")
}

function Emit-OneTapSummary {
  # Unconditional, fail-closed emission; never throws to caller.
  try {
    $repo = Get-CanonicalRepoRoot
    $m    = Resolve-MarketSafe $Market
    $sym  = Resolve-SymbolSafe $Symbol
    $todayStr = Resolve-AsOfDateSafe -RepoRoot $repo -MarketResolved $m -SymbolResolved $sym
    if($todayStr.Length -ge 10){ $todayStr = $todayStr.Substring(0,10) }

    # Canonical per-market log root (FAIL-CLOSED): never trust child stdout for paths.
    $logRoot = Get-CanonicalLogRoot -RepoRoot $repo -MarketResolved $m

    # Load blockg status stub if present; else synthesize fail-closed stub
    $stubPath = Join-Path $logRoot "blockg_status_stub.json"
    $st = $null
    if(Test-Path -LiteralPath $stubPath){
      $st = Get-Content -LiteralPath $stubPath -Raw -Encoding UTF8 | ConvertFrom-Json
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

    function Get-LatestOkTodayFromCsv([string]$csvPath, [string]$t0){
      if(-not (Test-Path -LiteralPath $csvPath)){ return $false }
      $rows = @(Import-Csv -LiteralPath $csvPath)
      if($rows.Count -lt 1){ return $false }
      $last = $rows[-1]

      $d = ""
      if($last.PSObject.Properties.Name -contains "as_of_date"){ $d = ($last.as_of_date + "") }
      elseif($last.PSObject.Properties.Name -contains "date"){ $d = ($last.date + "") }
      elseif($last.PSObject.Properties.Name -contains "today"){ $d = ($last.today + "") }
      $d = ($d + "").Trim()
      if($d.Length -ge 10){ $d = $d.Substring(0,10) } else { return $false }

      $ok = $false
      if($last.PSObject.Properties.Name -contains "ok_today"){ $ok = [bool]$last.ok_today }
      elseif($last.PSObject.Properties.Name -contains "ok"){ $ok = [bool]$last.ok }
      elseif($last.PSObject.Properties.Name -contains "okToday"){ $ok = [bool]$last.okToday }
      elseif($last.PSObject.Properties.Name -contains "phase23_ok"){
        $s = (($last.phase23_ok + "")).Trim().ToLowerInvariant()
        $ok = ($s -eq "true" -or $s -eq "1" -or $s -eq "yes" -or $s -eq "y")
      }
      return ($d -eq $t0 -and $ok)
    }

    $phase23_health_ok_today = $false
    $ev_hard_daily_ok_today  = $false
    try { $phase23_health_ok_today = Get-LatestOkTodayFromCsv (Join-Path $logRoot "phase23_health_daily.csv") $todayStr } catch { $phase23_health_ok_today = $false }
    try { $ev_hard_daily_ok_today  = Get-LatestOkTodayFromCsv (Join-Path $logRoot "phase5_ev_hard_veto_daily.csv") $todayStr } catch { $ev_hard_daily_ok_today = $false }

    $out = [ordered]@{
      ts_utc                   = (Get-Date).ToUniversalTime().ToString("o")
      as_of_date               = $todayStr
      phase4_ok_today          = [bool]$st.phase4_ok_today
      phase23_health_ok_today  = [bool]$phase23_health_ok_today
      ev_hard_daily_ok_today   = [bool]$ev_hard_daily_ok_today
      gatescore_ok_today       = [bool]$st.gatescore_ok_today
      nvda_blockg_ready        = [bool]$st.nvda_blockg_ready
      spy_blockg_ready         = [bool]$st.spy_blockg_ready
      qqq_blockg_ready         = [bool]$st.qqq_blockg_ready
      reasons_not_ready        = $st.reasons_not_ready
    }

    $json = ($out | ConvertTo-Json -Depth 6)
    $dst  = Join-Path $logRoot "onetap_summary.json"
    Write-Host ("[ONETAP] TARGET logRoot=" + $logRoot + " dst=" + $dst + " as_of=" + $todayStr + " Market=" + $m) -ForegroundColor Cyan
    [System.IO.File]::WriteAllText($dst, ($json -replace "`r`n","`n"), (New-Object System.Text.UTF8Encoding($false)))
    Write-Host ("[ONETAP] wrote " + $dst) -ForegroundColor Cyan
  } catch {
    Write-Host ("[ONETAP] summary finally failed: " + $_.Exception.Message) -ForegroundColor Yellow
  }
}

# =========================
# Main body (fail-closed)
# =========================
$finalExit = 0

try {
  $repoRoot = Get-CanonicalRepoRoot
  $psExe    = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"

  # Normalize Market/Symbol early (A3 single truth)
  $Market = Resolve-MarketSafe $Market
  $Symbol = Resolve-SymbolSafe $Symbol
  # Ensure child scripts that rely on env get the per-market context
  $env:HAT_MARKET = $Market
  $env:HAT_SYMBOL = $Symbol
  $env:HAT_REPO_ROOT = $repoRoot



  # Resolve RunContext ONCE (NO child powershell.exe)
  $rcPath = Join-Path $repoRoot "tools\Resolve-RunContext.ps1"
  if(-not (Test-Path -LiteralPath $rcPath)){ throw "[FAIL-CLOSED] Missing Resolve-RunContext.ps1: $rcPath" }
  $rc = (& $rcPath -Market $Market -Symbol $Symbol | Out-String)
  $rc = (($rc + "")).Trim()
  if(-not $rc){ throw "[A3] Resolve-RunContext empty stdout (fail-closed)" }
  $ix0 = $rc.IndexOf('{'); $ix1 = $rc.LastIndexOf('}')
  if($ix0 -lt 0 -or $ix1 -le $ix0){ throw "[A3] Resolve-RunContext did not return JSON (fail-closed)" }
  $rcObj = ($rc.Substring($ix0, ($ix1 - $ix0 + 1))) | ConvertFrom-Json
  if(-not $rcObj -or -not $rcObj.as_of_date){ throw "[A3] Resolve-RunContext missing as_of_date (fail-closed)" }
  $asOfDate = ([string]$rcObj.as_of_date).Trim()
  if($asOfDate.Length -ge 10){ $asOfDate = $asOfDate.Substring(0,10) }
  $env:HAT_ASOF_DATE = $asOfDate  # A3: propagate market-aware as_of_date to child producers

  Push-Location -LiteralPath $repoRoot
  try {
    Write-Host "`n[OPS] Block-G LOCKPACK (non-fatal)..." -ForegroundColor Cyan
    $lockpack_exit = 0

    # Crisis producer (non-fatal) — script itself has been hardened in your Fix Pack
    try {
& (Join-Path $repoRoot "tools\Write-CrisisRegimeStatus.ps1") -Market $Market -Symbol $Symbol 2>&1 | Out-Host
    } catch {
      Write-Host ("[CRISIS] producer failed: " + $_.Exception.Message) -ForegroundColor Yellow
    }

    try {
      # MOVED: Run-BlockGLockPack.ps1 is executed after producers to avoid stale BlockG snapshot
      $lockpack_exit = [int]$LASTEXITCODE
    } catch { $lockpack_exit = 2 }

    if($lockpack_exit -ne 0){
      Write-Host ("[ONETAP] WARN: LockPack failed (exit=" + $lockpack_exit + "). Continuing so onetap_summary.json is emitted (fail-closed).") -ForegroundColor Yellow
    }

    # GateScore daily summary
    $gsCsv     = Join-Path $repoRoot "logs\gatescore_daily_summary.csv"
    $gsSummary = Join-Path $repoRoot "tools\Run-GateScoreDailySummary.ps1"
    if(Test-Path -LiteralPath $gsSummary){ & $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $gsSummary 2>&1 | Out-Host }
    if(-not (Test-Path -LiteralPath $gsCsv)){ throw ("[A2] FAIL-CLOSED: missing GateScore daily summary csv: " + $gsCsv) }

    $today = $asOfDate
    if(-not $today){ $today = (Get-Date).ToString("yyyy-MM-dd") }

    # Per-market GateScore events (script hardened in your Fix Pack)
    $gsPm = Join-Path $repoRoot "tools\Write-GateScoreEvents-PerMarket.ps1"

    # LOCKPACK_MOVED_AFTER_GS_BEGIN
    # Re-run LockPack AFTER producers so BlockG snapshot reflects current-day evidence (GateScore + GlobalReady + EV-hard + Phase23).
    try {
      & (Join-Path $repoRoot "tools\Run-BlockGLockPack.ps1") -Market $Market -Symbol $Symbol 2>&1 | Out-Host
      $lockpack_exit = [int]$LASTEXITCODE
    } catch { $lockpack_exit = 2 }
    if($lockpack_exit -ne 0){
      Write-Host ("[ONETAP] WARN: LockPack failed (exit=" + $lockpack_exit + "). Continuing so onetap_summary.json is emitted (fail-closed).") -ForegroundColor Yellow
    }
    # LOCKPACK_MOVED_AFTER_GS_END

    if(Test-Path -LiteralPath $gsPm){
      & $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $gsPm -Market $Market -Symbol $Symbol -Mode rewrite -MinEvents 10 2>&1 | Out-Host
    } else {
      Write-Host ("[ONETAP] WARN missing per-market GateScore producer: " + $gsPm) -ForegroundColor Yellow
    }

    # Market enabled guard
    $mg = Join-Path $repoRoot "tools\Test-MarketEnabled.ps1"
    if(Test-Path -LiteralPath $mg){
      & $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $mg -Market $Market 2>&1 | Out-Host
      if($LASTEXITCODE -ne 0){ $finalExit = [int]$LASTEXITCODE; Write-Host ("[MARKET] FAIL-CLOSED: exitcode=" + $finalExit) -ForegroundColor Red }
    } else { $finalExit = 2; Write-Host ("[MARKET] FAIL-CLOSED: missing validator => " + $mg) -ForegroundColor Red }

    # Risk cap guard
    $rcCaps = Join-Path $repoRoot "tools\Test-MarketRiskCaps.ps1"
    if(Test-Path -LiteralPath $rcCaps){
      & $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $rcCaps -Market $Market -Mode REQUIRE_ENABLED 2>&1 | Out-Host
      if($LASTEXITCODE -ne 0 -and $finalExit -eq 0){ $finalExit = [int]$LASTEXITCODE; Write-Host ("[RISKCAP] FAIL-CLOSED: exitcode=" + $finalExit) -ForegroundColor Red }
    } else { if($finalExit -eq 0){ $finalExit = 2 }; Write-Host ("[RISKCAP] FAIL-CLOSED: missing validator => " + $rcCaps) -ForegroundColor Red }

    Write-Host ("[ONETAP] Daily readiness start today=" + $today + " symbol=" + $Symbol + " market=" + $Market) -ForegroundColor Cyan

    # Phase-4 validation + status producer
    $phase4 = Join-Path $repoRoot "tools\Run-Phase4Validation.ps1"
    if(Test-Path -LiteralPath $phase4){
& $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $phase4 -Market $Market -Symbol $Symbol 2>&1 | Out-Host
      $p4s = Join-Path $repoRoot "tools\Write-Phase4Status.ps1"
      if(Test-Path -LiteralPath $p4s){ & $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $p4s -Market $Market -Symbol $Symbol 2>&1 | Out-Host }
    } else { Write-Host ("[ONETAP] WARN missing Phase4 builder: " + $phase4) -ForegroundColor Yellow }

    # Phase-23 health daily
    $p23 = Join-Path $repoRoot "tools\Run-Phase23HealthDaily.ps1"
    if(Test-Path -LiteralPath $p23){
    & $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $p23 -Market $Market -Symbol $Symbol 2>&1 | Out-Host
    }
    # [A2] refresh phase23_status.json (per-market) AFTER heartbeat so today row exists
    try { & (Join-Path $repoRoot "tools\Write-Phase23Status.ps1") -Market $Market -Symbol $Symbol 2>&1 | Out-Host } catch { Write-Host ("[A2] WARN Phase23Status producer failed: " + $_.Exception.Message) -ForegroundColor Yellow }

    if($LASTEXITCODE -ne 0 -and $finalExit -eq 0){ $finalExit = [int]$LASTEXITCODE; Write-Host ("[ONETAP] FAIL-CLOSED: Phase23 health failed exit=" + $LASTEXITCODE) -ForegroundColor Red }

    # EV-hard daily
    $evd = Join-Path $repoRoot "tools\Run-EvHardVetoDaily.ps1"
    # EV-hard snapshot chain (REQUIRED): regenerates ev_hard_evidence_raw.json + builds veto snapshot before daily veto
    try { & (Join-Path $repoRoot "tools\Write-EvHardVetoSnapshot.ps1") -Market $Market -Symbol $Symbol 2>&1 | Out-Host } catch { Write-Host ("[EV-HARD] WARN snapshot chain failed: " + $_.Exception.Message) -ForegroundColor Yellow }

    # EV-hard daily (per-market)  REQUIRED to create logs\<Market>\phase5_ev_hard_veto_daily.csv
    if(Test-Path -LiteralPath $evd){ & $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $evd -Market $Market -Symbol $Symbol 2>&1 | Out-Host } else { Write-Host ("[ONETAP] WARN missing EV-hard runner: " + $evd) -ForegroundColor Yellow }
    # [A2] refresh ev_hard_status.json (per-market)



    # [A2] refresh ev_hard_status.json (per-market)  AFTER evd so evidence is current
    try { & (Join-Path $repoRoot "tools\Write-EvHardStatus.ps1") -Market $Market -Symbol $Symbol 2>&1 | Out-Host } catch { Write-Host ("[A2] WARN EvHardStatus producer failed: " + $_.Exception.Message) -ForegroundColor Yellow }

# A2_EFFECTIVE_AUDIT_BEGIN
# Fail-closed: ensure BlockG stub matches contract-effective A2 status JSONs for this market.
try {
  $a2 = Join-Path $repoRoot "tools\Test-A2StatusJsonsEffective.ps1"
  if(Test-Path -LiteralPath $a2){
    Write-Host ("[A2] effective audit (market=" + $Market + " symbol=" + $Symbol + ")") -ForegroundColor Cyan
    & $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $a2 -Markets @($Market) -Symbol $Symbol 2>&1 | Out-Host
    $a2Exit = [int]$LASTEXITCODE
    if($a2Exit -ne 0){
      if($finalExit -eq 0){ $finalExit = $a2Exit }
      Write-Host ("[A2] FAIL-CLOSED: effective audit failed exit=" + $a2Exit) -ForegroundColor Red
    }
  } else {
    if($finalExit -eq 0){ $finalExit = 2 }
    Write-Host ("[A2] FAIL-CLOSED: missing effective audit script => " + $a2) -ForegroundColor Red
  }
} catch {
  if($finalExit -eq 0){ $finalExit = 2 }
  Write-Host ("[A2] FAIL-CLOSED: effective audit exception: " + $_.Exception.Message) -ForegroundColor Red
}
# A2_EFFECTIVE_AUDIT_END



















  } finally {
    Pop-Location
  }

} finally {
  Emit-OneTapSummary
}

exit $finalExit

