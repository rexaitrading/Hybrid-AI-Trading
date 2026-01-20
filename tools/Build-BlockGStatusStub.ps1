[CmdletBinding()]
param(
    [ValidateSet("NVDA","SPY","QQQ","ALL")]
    [string]$Symbol = "ALL",

    [ValidateSet("US","JP","HK","SG","IN","KR","TW","HK_SH","HK_SZ")]
    [string]$Market = "US"
)
function Resolve-RepoRoot(){
  # Canonical filesystem path; never trust invocation-string representation
  $toolsDir = Split-Path -Parent $PSCommandPath
  $rr = Split-Path -Parent $toolsDir
  try { return (Resolve-Path -LiteralPath $rr -ErrorAction Stop).Path } catch { return $rr }
}

function Ensure-GlobalReadyV0([string]$Market,[string]$LogsDir,[string]$TodayLocal){
  $psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
  $repoRoot = Resolve-RepoRoot
  $prods = @(
    @{ name="market_dna.json";        script=(Join-Path $repoRoot "tools\Build-MarketDNA.ps1") },
    @{ name="edge_validity.json";     script=(Join-Path $repoRoot "tools\Build-EdgeValidity.ps1") },
    @{ name="dependency_risk.json";   script=(Join-Path $repoRoot "tools\Build-DependencyRisk.ps1") },
    @{ name="risk_guard_status.json"; script=(Join-Path $repoRoot "tools\Build-RiskGuardStatus.ps1") }
  )

  foreach($p in $prods){
    $path = Join-Path $LogsDir $p.name
    $need = $true
    if(Test-Path -LiteralPath $path){
      try{
        $o = (Get-Content -LiteralPath $path -Raw -Encoding UTF8) | ConvertFrom-Json
        if(([string]$o.as_of_date) -eq $TodayLocal -and ($null -ne $o.ok_today)){
          $need = $false
        }
      } catch { $need = $true }
    }
    if($need){
      if(Test-Path -LiteralPath $p.script){
        & $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $p.script -Market $Market | Out-Null
      }
    }
  }
}


function WantSym([string]$sym){
  $s = $Symbol.ToUpperInvariant()
  return ($s -eq "ALL" -or $s -eq $sym.ToUpperInvariant())
}
function Prefer-LogsPath([string]$Primary,[string]$Fallback){
  if($Primary -and (Test-Path -LiteralPath $Primary)){ return $Primary }
  if($Fallback -and (Test-Path -LiteralPath $Fallback)){ return $Fallback }
  return $Primary
}
function Resolve-GatescoreEventsPath([string]$sym,[string]$logsDir){
  $s = ($sym + "").ToLowerInvariant()
  # Prefer canonical STD file first (freshest truth).
  $pMain = Join-Path $logsDir ("{0}_gatescore_events.jsonl" -f $s)
  if(Test-Path -LiteralPath $pMain){ return $pMain }

  # Fallback: legacy/real file
  $pReal = Join-Path $logsDir ("{0}_gatescore_events_real.jsonl" -f $s)
  if(Test-Path -LiteralPath $pReal){ return $pReal }

  return $pMain  # deterministic fallback (may not exist)
}

function Resolve-GatescoreEventsPathToday([string]$sym,[string]$logsDir){
  $s = ($sym + '').ToLowerInvariant()
  $pToday = Join-Path $logsDir (('{0}_gatescore_events_today.jsonl' -f $s))
  if(Test-Path -LiteralPath $pToday){ return $pToday }
  return (Resolve-GatescoreEventsPath $sym $logsDir)
}


function Get-MaxAsOfDateFromJsonlTail([string]$Path,[int]$TailLines=8000){
  if(-not (Test-Path -LiteralPath $Path)){ return "" }
  $max = ""
  foreach($ln in (Get-Content -LiteralPath $Path -Tail $TailLines -Encoding UTF8)){
    $s = ($ln + "").Trim(); if(-not $s){ continue }
    try {
      $o = $s | ConvertFrom-Json
      if($o.PSObject.Properties.Name -contains "as_of_date"){
        $d = [string]$o.as_of_date
        if($d.Length -ge 10){ $d = $d.Substring(0,10) }
        if($d -and $d -gt $max){ $max = $d }
      }
    } catch { }
  }
  return $max
}

function Has-TodayAsOfDateInJsonlTail([string]$Path,[string]$Today,[int]$TailLines=8000){
  if(-not $Today){ return $false }
  if(-not (Test-Path -LiteralPath $Path)){ return $false }
  $t = $Today
  if($t.Length -ge 10){ $t = $t.Substring(0,10) }
  foreach($ln in (Get-Content -LiteralPath $Path -Tail $TailLines -Encoding UTF8)){
    $s = ($ln + "").Trim(); if(-not $s){ continue }
    try {
      $o = $s | ConvertFrom-Json
      if($o -and ($o.PSObject.Properties.Name -contains "as_of_date")){
        $d = [string]$o.as_of_date
        if($d.Length -ge 10){ $d = $d.Substring(0,10) }
        if($d -eq $t){ return $true }
      }
    } catch { }
  }
  return $false
}

# Audit: capture metrics_source per symbol from RESOLVED events file (today-only).
function Get-MetricsSourceTop([string]$sym,[string]$logsDir,[string]$todayLocal){
  $p = Resolve-GatescoreEventsPathToday $sym $logsDir
  $seen = @{}
  $exists = [bool](Test-Path -LiteralPath $p)

  if($exists){
    foreach($ln in (Get-Content -LiteralPath $p -Encoding utf8)){
      $s = ($ln + "").Trim(); if(-not $s){ continue }
      try {
        $o = $s | ConvertFrom-Json
        $d = ""
        if($o.PSObject.Properties.Name -contains "as_of_date"){
          $d = ([string]$o.as_of_date)
          if($d.Length -ge 10){ $d = $d.Substring(0,10) }
        }
        if($d -ne $todayLocal){ continue }

        $ms = ""
        if($o.PSObject.Properties.Name -contains "metrics_source"){
          $ms = ([string]$o.metrics_source).Trim()
        }
        if(-not $ms){ $ms = "(missing)" }

        if(-not $seen.ContainsKey($ms)){ $seen[$ms]=0 }
        $seen[$ms] += 1
      } catch { }
    }
  }

  $top = ""
  if($seen.Count -gt 0){
    $top = ($seen.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 1).Name
  }
  return [pscustomobject]@{ path=$p; exists=$exists; seen_count=[int]$seen.Count; top=$top }
}
# GS_METRICS_SOURCE_BY_SYMBOL_END
Set-StrictMode -Version Latest
# --- HAT_RUNMODE_SINGLETRUTH_BEGIN
$toolsDir = Split-Path -Parent $PSCommandPath
$rmPath = Join-Path $toolsDir "Resolve-HatRunMode.ps1"
if(-not (Test-Path -LiteralPath $rmPath)){ throw "[FAIL-CLOSED] missing Resolve-HatRunMode.ps1" }
$rmRaw = (& $rmPath 2>&1 | Out-String)
$ix0 = $rmRaw.IndexOf("{"); $ix1 = $rmRaw.LastIndexOf("}")
if($ix0 -lt 0 -or $ix1 -le $ix0){ throw "[FAIL-CLOSED] Resolve-HatRunMode did not return JSON" }
$rmObj = ($rmRaw.Substring($ix0, ($ix1 - $ix0 + 1)) | ConvertFrom-Json -ErrorAction Stop)
$script:__HAT_RUNMODE = ([string]$rmObj.run_mode).Trim().ToUpperInvariant()
# --- HAT_RUNMODE_SINGLETRUTH_END
function Get-RunContextOrFail([string]$RepoRoot,[string]$Market,[string]$Symbol){
  $rcPath = Join-Path $RepoRoot "tools\Resolve-RunContext.ps1"
  if(-not (Test-Path -LiteralPath $rcPath)){ throw "[FAIL-CLOSED] Missing Resolve-RunContext.ps1: $rcPath" }
  $raw = (& $rcPath -Market $Market -Symbol $Symbol | Out-String)
  $raw = (($raw + "")).Trim()
  $i0 = $raw.IndexOf("{"); $i1 = $raw.LastIndexOf("}")
  if($i0 -lt 0 -or $i1 -le $i0){ throw "[FAIL-CLOSED] Resolve-RunContext did not return JSON" }
  $rc = ($raw.Substring($i0, ($i1-$i0+1))) | ConvertFrom-Json
  if(-not $rc -or -not $rc.as_of_date){ throw "[FAIL-CLOSED] Resolve-RunContext missing as_of_date" }
  return $rc
}

# [A3] Helper must exist BEFORE any call sites (call-before-def caused CommandNotFoundException).
if(-not (Get-Command _GetTodayLocalFromRunContext -ErrorAction SilentlyContinue)){
  function _SliceDate([string]$d){
    if(-not $d){ return "" }
    $s = ([string]$d).Trim()
    if($s.Length -ge 10){ return $s.Substring(0,10) }
    return $s
  }
  function _GetTodayLocalFromRunContext([string]$Market,[string]$Symbol,[string]$RepoRoot){
    $rcPath = Join-Path $RepoRoot "tools\Resolve-RunContext.ps1"
    if(-not (Test-Path -LiteralPath $rcPath)){ throw "[FAIL-CLOSED] Missing Resolve-RunContext.ps1: $rcPath" }
    $raw = (& $rcPath -Market $Market -Symbol $Symbol | Out-String)
    $raw = (($raw + "")).Trim()
    $i0 = $raw.IndexOf("{"); $i1 = $raw.LastIndexOf("}")
    if($i0 -lt 0 -or $i1 -le $i0){ throw "[FAIL-CLOSED] Resolve-RunContext did not return JSON" }
    $rc = ($raw.Substring($i0, ($i1-$i0+1))) | ConvertFrom-Json
    if(-not $rc -or -not $rc.as_of_date){ throw "[FAIL-CLOSED] Resolve-RunContext missing as_of_date" }
    return (_SliceDate ([string]$rc.as_of_date))
  }
}
# Mode truth (single semantic): LIVE must remain strict.
  $mode = $script:__HAT_RUNMODE
$isLiveMode = ($mode -eq "LIVE")
  # Contract semantics level (fail-closed deterministic)
  $contract_semantics_level = "PAPER_STRICT"
  if($mode -eq "PAPERLIVE"){ $contract_semantics_level = "PAPERLIVE_STRICT" }
  if($isLiveMode){ $contract_semantics_level = "LIVE_STRICT" }
try {
# --- OUTPUT ENCODING (institutional) ---
try {
  $utf8 = New-Object System.Text.UTF8Encoding($false)
  [Console]::OutputEncoding = $utf8
  [Console]::InputEncoding  = $utf8
  $global:OutputEncoding    = $utf8
} catch { }
# --- END OUTPUT ENCODING ---
function Canon([string]$p){
  try {
    if([string]::IsNullOrWhiteSpace($p)){ return $p }
    $full = $p
    if(-not [System.IO.Path]::IsPathRooted($full)){
      $full = Join-Path $repoRoot $full
    }
    $full = [System.IO.Path]::GetFullPath($full)

    # If path exists, Resolve-Path to canonicalize.
    if(Test-Path -LiteralPath $full){
      try { return (Resolve-Path -LiteralPath $full -ErrorAction Stop).Path } catch { return $full }
    }

    # If path does NOT exist yet (common for output files), canonicalize parent dir if possible.
    $parent = Split-Path -Parent $full
    if($parent -and (Test-Path -LiteralPath $parent)){
      try {
        $p2 = (Resolve-Path -LiteralPath $parent -ErrorAction Stop).Path
        return (Join-Path $p2 (Split-Path -Leaf $full))
      } catch { return $full }
    }

    return $full
  } catch {
    return $p
  }
}
function Get-LatestIntelRunToday {
  param(
    [Parameter(Mandatory=$true)][string]$LogsIntelFeedPath,
    [Parameter(Mandatory=$true)][string]$Kind,  # intel_news_run | intel_youtube_run
    [Parameter(Mandatory=$true)][string]$TodayLocal
  )
  if(-not (Test-Path -LiteralPath $LogsIntelFeedPath)){ return $null }
  $lines = Get-Content -LiteralPath $LogsIntelFeedPath -Encoding utf8 -ErrorAction SilentlyContinue
  if(-not $lines){ return $null }
  $best = $null
  foreach($ln in ($lines | Select-Object -Last 5000)){
    $s = ($ln + "").Trim()
    if(-not $s){ continue }
    try {
      $j = $s | ConvertFrom-Json -ErrorAction Stop
      if(($j.kind + "") -ne $Kind){ continue }
      if(($j.as_of_date + "") -ne $TodayLocal){ continue }
      $best = $j
    } catch { continue }
  }
  return $best
}

function Resolve-IntelOkToday {
  param(
    [Parameter(Mandatory=$true)][string]$RepoRoot,
    [Parameter(Mandatory=$true)][string]$TodayLocal,
    [switch]$YouTubeOptional
  )
  $logsIntelFeed = Join-Path $RepoRoot "logs\intel_feed.jsonl"
  $news = Get-LatestIntelRunToday -LogsIntelFeedPath $logsIntelFeed -Kind "intel_news_run" -TodayLocal $TodayLocal
  $yt   = Get-LatestIntelRunToday -LogsIntelFeedPath $logsIntelFeed -Kind "intel_youtube_run" -TodayLocal $TodayLocal

  # If any full-run pulses exist, they become authoritative
  $hasFull = ($null -ne $news) -or ($null -ne $yt)

  if($hasFull){
    $newsOk = $false
    if($null -ne $news){ $newsOk = [bool]$news.ok }

    $ytOk = $false
    if($null -ne $yt){ $ytOk = [bool]$yt.ok }

    $ok = $newsOk -and ( $YouTubeOptional.IsPresent -or $ytOk )
    return [ordered]@{
      intel_ok_today = [bool]$ok
      intel_kind = "intel_full_pulses"
      intel_as_of_date = $TodayLocal
      intel_source_path = $logsIntelFeed
      intel_news_ok_today = [bool]$newsOk
      intel_youtube_ok_today = [bool]$ytOk
    }
  }

  # No full pulses found: do not allow minimal pulse to green-light live readiness
  return [ordered]@{
    intel_ok_today = $false
    intel_kind = "intel_minimal_only"
    intel_as_of_date = $TodayLocal
    intel_source_path = (Join-Path $RepoRoot "logs\risk_pulse.jsonl")
    intel_news_ok_today = $false
    intel_youtube_ok_today = $false
  }
}


# --- PATCH1: type-safe field setter (hashtable OR pscustomobject) ---
function Set-ObjField([object]$obj,[string]$name,[object]$value){
  if($null -eq $obj){ return }
  if($obj -is [hashtable] -or $obj -is [System.Collections.IDictionary]){
    $obj[$name] = $value
    return
  }
  # PSCustomObject / other: Add-Member if missing, else set
  if($obj.PSObject.Properties.Name -notcontains $name){
    Add-Member -InputObject $obj -NotePropertyName $name -NotePropertyValue $value -Force
  } else {
    $obj.$name = $value
  }
}
# --- END PATCH1 ---

# --- PATCH1: robust GateScore events loader (JSON array OR JSONL), micro field detection ---
function Get-GSEventsObjects([string]$path){
  if(-not (Test-Path $path)){ return @() }
  $raw = Get-Content -LiteralPath $path -Encoding UTF8 -Raw
  $t = ($raw+"").Trim()
  if(-not $t){ return @() }

  if($t.StartsWith("[")){
    try { return @($t | ConvertFrom-Json) } catch { return @() }
  }

  $out=@()
  foreach($ln in Get-Content -LiteralPath $path -Encoding UTF8){
    $s=($ln+"").Trim(); if(-not $s){ continue }
    try { $out += @($s | ConvertFrom-Json) } catch { }
  }
  return $out
}

function Find-FirstMatchingKey([object]$obj,[string]$regex){
  foreach($p in $obj.PSObject.Properties.Name){
    if($p -match $regex){ return $p }
  }
  return $null
}
# --- END PATCH1 ---

function Read-JsonlLines([string]$Path){
  if(-not (Test-Path -LiteralPath $Path)){ return @() }
  $out=@()
  foreach($ln in (Get-Content -LiteralPath $Path -Encoding UTF8)){
    $s=$ln.Trim(); if(-not $s){ continue }
    try { $out += ($s | ConvertFrom-Json) } catch { }
  }
  return @($out)
}
function SliceDate([string]$d){
  if(-not $d){ return "" }
  if($d.Length -ge 10){ return $d.Substring(0,10) }
  return $d
}
function IsTradingDay([datetime]$dt){
  $dow = [int]$dt.DayOfWeek
  return ($dow -ne 0 -and $dow -ne 6)
}
function LastNTradingDays([string]$asOf,[int]$n){
  $d = [datetime]::ParseExact($asOf,"yyyy-MM-dd",$null)
  $days=@()
  while($days.Count -lt $n){
    if(IsTradingDay $d){ $days += $d.ToString("yyyy-MM-dd") }
    $d = $d.AddDays(-1)
  }
  return $days
}
function ComputeGateScoreRolling([string]$sym,[string]$logsDir,[string[]]$days){
  $path = Resolve-GatescoreEventsPath $sym $logsDir
  $evs = @()
  foreach($ln in (Get-Content -LiteralPath $path -Encoding utf8)){
    $s = ($ln + "").Trim(); if(-not $s){ continue }
    try {
      $o = $s | ConvertFrom-Json -ErrorAction Stop
      if($o -and ($o.PSObject.Properties.Name -contains "symbol")){
        $symKey = (($sym + "")).Trim().ToUpperInvariant()
        $rowSym = (([string]$o.symbol).Trim().ToUpperInvariant())
        if($rowSym -eq $symKey){ $evs += $o }
      }
    } catch { }
  }
  if($evs.Count -eq 0){ return [pscustomobject]@{ samples=0; pnl_samples=0; mean_edge=0.0; mean_micro=0.0 } }

  $sel=@()
  foreach($e in $evs){
    $d = SliceDate ([string]$e.as_of_date)
    if($days -contains $d){
      if(-not ($e.PSObject.Properties.Name -contains "eligible") -or [bool]$e.eligible){
        $sel += $e
      }
    }
  }

  $edge=@(); $micro=@(); $pnlCount=0
  foreach($e in $sel){
    if($null -ne $e.edge_ratio){ $edge += [double]$e.edge_ratio }
    if($null -ne $e.micro_score){ $micro += [double]$e.micro_score }
    # PNL_SAMPLE_COUNT_BEGIN
try {
  if($e.PSObject.Properties.Name -contains "realized_pnl" -and $null -ne $e.realized_pnl){
    $pnlCount += 1
  } elseif($e.PSObject.Properties.Name -contains "pnl_samples") {
    $n = 0
    try { $n = [int]$e.pnl_samples } catch { $n = 0 }
    if($n -gt 0){ $pnlCount += $n }
  }
} catch { }
# PNL_SAMPLE_COUNT_END
  }

  $meanEdge  = if($edge.Count -gt 0){ ($edge | Measure-Object -Average).Average } else { 0.0 }
  $meanMicro = if($micro.Count -gt 0){ ($micro | Measure-Object -Average).Average } else { 0.0 }

  return [pscustomobject]@{
    samples     = [int]$sel.Count
    pnl_samples = [int]$pnlCount
    mean_edge   = [double]$meanEdge
    mean_micro  = [double]$meanMicro
  }
}

function Get-GSFromEvents([string]$sym, [string]$asOf, [string]$todayLocal){
  $asOfKey = ((($asOf + "")).Trim())
  # Compute GateScore metrics for a single as_of_date from resolved events source.
  $repoRoot = Resolve-RepoRoot

# Phase-5 Policy A: GLOBAL inputs, per-market outputs
$logsDirOut = $null
$logsRoot = Join-Path $repoRoot "logs"

try {
  $logsDirOut = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Get-MarketLogRoot.ps1") -Market $Market
} catch { $logsDirOut = $null }
# G_READY_STUB_LOGSDIROUT_FAILCLOSED_BEGIN
if(-not $logsDirOut){
  throw ("[FAIL-CLOSED] Get-MarketLogRoot returned empty (no root logs fallback). market=" + (($Market + "")).Trim().ToUpperInvariant() + " repoRoot=" + $repoRoot)
}
# G_READY_STUB_LOGSDIROUT_FAILCLOSED_END
$logsDir = $logsDirOut
# CRISIS_REGIME_STATUS_BEGIN
# A2: Crisis regime producer status (fail-closed for LIVE when missing/stale)
$crisisOkToday = $false
$crisisRegime = $false
$crisisPortfolioHalt = $false
$crisisRiskFlatten = $false
$crisisCooldownMinutes = 0
$crisisStatusPath = Join-Path $logsDir "crisis_regime_status.json"

# If missing, default OK for NON-LIVE only; keep fail-closed for LIVE.
# LIVE semantics preserved: missing => crisisOkToday stays false.
try {
  $mode = $script:__HAT_RUNMODE
  if(-not (Test-Path -LiteralPath $crisisStatusPath)){
    if($mode -ne "LIVE"){
      $crisisOkToday = $true
      $crisisRegime  = $false
      $crisisReason  = "missing_crisis_status_default_ok_nonlive"
    }
  }
} catch { }
try {
  $cj = Read-JsonSafe $crisisStatusPath
  if($cj){
    $asOf = ""
    if($cj.PSObject.Properties.Name -contains "as_of_date"){ $asOf = [string]$cj.as_of_date }
    if($asOf.Length -ge 10){ $asOf = $asOf.Substring(0,10) }
      # TODAYKEY_BEGIN (crisis reader): ensure compare key exists even before RunContext sets todayLocal
      $todayKey = ""
      try { if(Get-Variable -Name "todayLocal" -Scope Local -ErrorAction SilentlyContinue){ $todayKey = ([string]$todayLocal) } } catch { $todayKey = "" }
      $todayKey = (($todayKey + "")).Trim()
      if($todayKey.Length -ge 10){ $todayKey = $todayKey.Substring(0,10) }
      if(-not $todayKey){
        $todayKey = ((($env:HAT_ASOF_DATE + "")).Trim())
        if($todayKey.Length -ge 10){ $todayKey = $todayKey.Substring(0,10) }
        if($todayKey -notmatch '^\d{4}-\d{2}-\d{2}$'){ $todayKey = "" }
      }
      if(-not $todayKey){
        # Non-LIVE last resort; LIVE semantics for missing files remain handled by existing logic above
        $todayKey = (Get-Date).ToString("yyyy-MM-dd")
      }
      # TODAYKEY_END

    if($asOf -eq $todayKey){
      if($cj.PSObject.Properties.Name -contains "ok_today"){ $crisisOkToday = [bool]$cj.ok_today }
      if($cj.PSObject.Properties.Name -contains "crisis_regime"){ $crisisRegime = [bool]$cj.crisis_regime }
      if($cj.PSObject.Properties.Name -contains "portfolio_halt"){ $crisisPortfolioHalt = [bool]$cj.portfolio_halt }
      if($cj.PSObject.Properties.Name -contains "risk_flatten"){ $crisisRiskFlatten = [bool]$cj.risk_flatten }
      if($cj.PSObject.Properties.Name -contains "cooldown_minutes"){
        try { $crisisCooldownMinutes = [int]$cj.cooldown_minutes } catch { $crisisCooldownMinutes = 0 }
      }
    }
  }
} catch { }
# CRISIS_REGIME_STATUS_END



  $path = Resolve-GatescoreEventsPath $sym $logsDir
  $evs = @()
  foreach($ln in (Get-Content -LiteralPath $path -Encoding utf8)){
    $s = ($ln + "").Trim(); if(-not $s){ continue }
    try {
      $o = $s | ConvertFrom-Json -ErrorAction Stop
      if($o -and ($o.PSObject.Properties.Name -contains "symbol")){
        $symKey = (($sym + "")).Trim().ToUpperInvariant()
        $rowSym = (([string]$o.symbol).Trim().ToUpperInvariant())
        if($rowSym -eq $symKey){ $evs += $o }
      }
    } catch { }
  }
  if($evs.Count -eq 0){
    return [pscustomobject]@{ fresh=$false; cnt=0; pnl=0; edge=0.0; micro=0.0 }
  }

  $sel=@()
  foreach($e in $evs){
    $d = SliceDate ([string]$e.as_of_date)
    if($d -eq $asOfKey){
      if(-not ($e.PSObject.Properties.Name -contains "eligible") -or [bool]$e.eligible){
        $sel += $e
      }
    }
  }

  $edge=@(); $micro=@(); $pnlCount=0
  foreach($e in $sel){
    if($null -ne $e.edge_ratio){ $edge += [double]$e.edge_ratio }
    if($null -ne $e.micro_score){ $micro += [double]$e.micro_score }
    # PNL_SAMPLE_COUNT_BEGIN
try {
  if($e.PSObject.Properties.Name -contains "realized_pnl" -and $null -ne $e.realized_pnl){
    $pnlCount += 1
  } elseif($e.PSObject.Properties.Name -contains "pnl_samples") {
    $n = 0
    try { $n = [int]$e.pnl_samples } catch { $n = 0 }
    if($n -gt 0){ $pnlCount += $n }
  }
} catch { }
# PNL_SAMPLE_COUNT_END
  }

  $meanEdge  = if($edge.Count -gt 0){ ($edge | Measure-Object -Average).Average } else { 0.0 }
  $meanMicro = if($micro.Count -gt 0){ ($micro | Measure-Object -Average).Average } else { 0.0 }

  return [pscustomobject]@{
    fresh = ([int]$sel.Count -gt 0)
    cnt   = [int]$sel.Count
    pnl   = [int]$pnlCount
    edge  = [double]$meanEdge
    micro = [double]$meanMicro
  }
}
$ErrorActionPreference = "Stop"



# A3_MARKET_ENVFIRST_BEGIN
# MARKET_PARAM_WINS_V1_BEGIN
# Contract: -Market parameter MUST win. Env is fallback only (prevents HAT_MARKET bleed into other markets).
$m = (($Market + "")).Trim().ToUpperInvariant()
if(-not $m){
  $m = (($env:HAT_MARKET + "")).Trim().ToUpperInvariant()
}
if(-not $m){ $m = "US" }
$Market = $m
# MARKET_PARAM_WINS_V1_END
# A3_MARKET_ENVFIRST_END

# A3_MARKET_ENVFIRST_BEGIN
# Contract: Market must be resolved env-first to prevent US log bleed.
$m = (($Market + "")).Trim().ToUpperInvariant()
if(-not $m){ $m = (($env:HAT_MARKET + "")).Trim().ToUpperInvariant() }
if(-not $m){ $m = "US" }
$Market = $m
# A3_MARKET_ENVFIRST_END

function Get-Phase4OkToday([string]$RepoRoot, [string]$LogsDir, [string]$Today){
  $path = Join-Path $LogsDir "phase4_validation_passed.json"
  if(-not (Test-Path $path)){ return $false }

  try {
    $raw = Get-Content -LiteralPath $path -Raw -Encoding utf8
    $j = $raw | ConvertFrom-Json
    $asOf = [string]$j.as_of_date
    $ok = [bool]$j.phase4_ok_today
    $t = ((($Today + "")).Trim())
    if($t.Length -ge 10){ $t = $t.Substring(0,10) }
    $a = ((($asOf + "")).Trim())
    if($a.Length -ge 10){ $a = $a.Substring(0,10) }
    return ($a -eq $t) -and $ok
  } catch {
    return $false
  }
}
# A2_STATUS_JSON_HELPERS_BEGIN
function Read-JsonSafe([string]$Path){
  try{
    if(-not (Test-Path -LiteralPath $Path)){ return $null }
    $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    if(-not $raw){ return $null }
    return ($raw | ConvertFrom-Json -ErrorAction Stop)
  } catch { return $null }
}

function Read-StatusOkToday([string]$StatusPath,[string]$TodayLocal){
  # expects status json schema: { as_of_date, ok_today, ... }
  $j = Read-JsonSafe $StatusPath
  if(-not $j){ return $null }
  try{
    $asOf = ""
    if($j.PSObject.Properties.Name -contains "as_of_date"){ $asOf = [string]$j.as_of_date }
    if($asOf.Length -ge 10){ $asOf = $asOf.Substring(0,10) }
    if($asOf -ne $TodayLocal){ return $false }
    if($j.PSObject.Properties.Name -contains "ok_today"){ return [bool]$j.ok_today }
  } catch { }
  return $false
}
# A2_STATUS_JSON_HELPERS_END
# A2_STATUS_JSON_STRICT_BEGIN
function Read-StatusJsonStrict(
  [string]$Path,
  [string]$ExpectedKind,
  [string]$TodayLocal,
  [string]$ExpectedMarket = $null
){
  if(-not (Test-Path -LiteralPath $Path)){ return $null }

  $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
  if(-not $raw){ throw "[FAIL-CLOSED] empty status json: $Path" }

  $j = $raw | ConvertFrom-Json -ErrorAction Stop

  if(-not ($j.PSObject.Properties.Name -contains "kind")){
    throw "[FAIL-CLOSED] status json missing kind: $Path"
  }
  if($j.kind -ne $ExpectedKind){
    throw "[FAIL-CLOSED] status json kind mismatch: $Path expected=$ExpectedKind got=$($j.kind)"
  }

  if($ExpectedMarket){
    if(-not ($j.PSObject.Properties.Name -contains "market")){
      throw "[FAIL-CLOSED] status json missing market: $Path"
    }
    if(([string]$j.market).ToUpperInvariant() -ne $ExpectedMarket){
      throw "[FAIL-CLOSED] status json market mismatch: $Path expected=$ExpectedMarket got=$($j.market)"
    }
  }

  if(-not ($j.PSObject.Properties.Name -contains "as_of_date")){
    throw "[FAIL-CLOSED] status json missing as_of_date: $Path"
  }

  $asOf = [string]$j.as_of_date
  if($asOf.Length -ge 10){ $asOf = $asOf.Substring(0,10) }
  if($asOf -ne $TodayLocal){
    throw "[FAIL-CLOSED] status json stale: $Path as_of_date=$asOf today=$TodayLocal"
  }

  if(-not ($j.PSObject.Properties.Name -contains "ok_today")){
    throw "[FAIL-CLOSED] status json missing ok_today: $Path"
  }

  return [bool]$j.ok_today
}
# A2_STATUS_JSON_STRICT_END

$repoRoot = Resolve-RepoRoot

# Phase-5 Policy A: GLOBAL inputs, per-market outputs
$logsDirOut = $null
$logsRoot = Join-Path $repoRoot "logs"

try {
  $logsDirOut = & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repoRoot "tools\Get-MarketLogRoot.ps1") -Market $Market
} catch { $logsDirOut = $null }
# G_READY_STUB_LOGSDIROUT_FAILCLOSED_BEGIN
if(-not $logsDirOut){
  throw ("[FAIL-CLOSED] Get-MarketLogRoot returned empty (no root logs fallback). market=" + (($Market + "")).Trim().ToUpperInvariant() + " repoRoot=" + $repoRoot)
}
# G_READY_STUB_LOGSDIROUT_FAILCLOSED_END
# repoRoot resolved above (canonical)
$logsDir = $logsDirOut
# CRISIS_REGIME_STATUS_BEGIN
# A2: Crisis regime producer status (fail-closed for LIVE when missing/stale)
$crisisOkToday = $false
$crisisRegime = $false
$crisisPortfolioHalt = $false
$crisisRiskFlatten = $false
$crisisCooldownMinutes = 0
$crisisStatusPath = Join-Path $logsDir "crisis_regime_status.json"

# If missing, default OK for NON-LIVE only; keep fail-closed for LIVE.
# LIVE semantics preserved: missing => crisisOkToday stays false.
try {
  $mode = $script:__HAT_RUNMODE
  if(-not (Test-Path -LiteralPath $crisisStatusPath)){
    if($mode -ne "LIVE"){
      $crisisOkToday = $true
      $crisisRegime  = $false
      $crisisReason  = "missing_crisis_status_default_ok_nonlive"
    }
  }
} catch { }
try {
  $cj = Read-JsonSafe $crisisStatusPath
  if($cj){
    $asOf = ""
    if($cj.PSObject.Properties.Name -contains "as_of_date"){ $asOf = [string]$cj.as_of_date }
    if($asOf.Length -ge 10){ $asOf = $asOf.Substring(0,10) }
      # TODAYKEY_BEGIN (crisis reader): ensure compare key exists even before RunContext sets todayLocal
      $todayKey = ""
      try { if(Get-Variable -Name "todayLocal" -Scope Local -ErrorAction SilentlyContinue){ $todayKey = ([string]$todayLocal) } } catch { $todayKey = "" }
      $todayKey = (($todayKey + "")).Trim()
      if($todayKey.Length -ge 10){ $todayKey = $todayKey.Substring(0,10) }
      if(-not $todayKey){
        $todayKey = ((($env:HAT_ASOF_DATE + "")).Trim())
        if($todayKey.Length -ge 10){ $todayKey = $todayKey.Substring(0,10) }
        if($todayKey -notmatch '^\d{4}-\d{2}-\d{2}$'){ $todayKey = "" }
      }
      if(-not $todayKey){
        # Non-LIVE last resort; LIVE semantics for missing files remain handled by existing logic above
        $todayKey = (Get-Date).ToString("yyyy-MM-dd")
      }
      # TODAYKEY_END

    if($asOf -eq $todayKey){
      if($cj.PSObject.Properties.Name -contains "ok_today"){ $crisisOkToday = [bool]$cj.ok_today }
      if($cj.PSObject.Properties.Name -contains "crisis_regime"){ $crisisRegime = [bool]$cj.crisis_regime }
      if($cj.PSObject.Properties.Name -contains "portfolio_halt"){ $crisisPortfolioHalt = [bool]$cj.portfolio_halt }
      if($cj.PSObject.Properties.Name -contains "risk_flatten"){ $crisisRiskFlatten = [bool]$cj.risk_flatten }
      if($cj.PSObject.Properties.Name -contains "cooldown_minutes"){
        try { $crisisCooldownMinutes = [int]$cj.cooldown_minutes } catch { $crisisCooldownMinutes = 0 }
      }
    }
  }
} catch { }
# CRISIS_REGIME_STATUS_END




# --- FAST BUILDER MODE (Phase3-safe, institutional) ---
# Phase3 must be able to build a stub quickly without scanning huge event files.
# Enable by: $env:HAT_BLOCKG_BUILDER_FAST="1"
if((($env:HAT_BLOCKG_BUILDER_FAST + "") -eq "1")){
  try{
    if(-not (Test-Path -LiteralPath $logsDir)){ New-Item -ItemType Directory -Force -Path $logsDir | Out-Null }
    $statusPath = Join-Path $logsDirOut "blockg_status_stub.json"

# --- BREADCRUMB (debug, deterministic) ---
try {
  $toolsDir = Split-Path -Parent $PSCommandPath
  $crumbPath = Join-Path $toolsDir "blockg_builder_breadcrumb.txt"
  $msg = @(
    ("ts=" + (Get-Date).ToString("s")),
    ("repoRoot=" + $repoRoot),
    ("logsDir=" + $logsDir),
    ("statusPath=" + $statusPath),
    ("pwd=" + (Get-Location).Path)
  ) -join "`r`n"
  [System.IO.File]::WriteAllText($crumbPath, $msg, (New-Object System.Text.UTF8Encoding($false)))
} catch { }
# --- END BREADCRUMB ---
$rcA3 = Get-RunContextOrFail $repoRoot $Market $Symbol

# A3_FORCE_LOGSDIR_FROM_RUNCONTEXT_BEGIN
# Contract: logs paths MUST be derived from RunContext (authoritative) to prevent US bleed.
if(-not $rcA3){ throw "[FAIL-CLOSED] rcA3 empty" }
if(-not ($rcA3.PSObject.Properties.Name -contains "market")){ throw "[FAIL-CLOSED] rcA3 missing market" }
if(-not ($rcA3.PSObject.Properties.Name -contains "logs_dir_out")){ throw "[FAIL-CLOSED] rcA3 missing logs_dir_out" }
$Market = ([string]$rcA3.market).Trim().ToUpperInvariant()
$logsDir = ([string]$rcA3.logs_dir_out).Trim()
  # A3: logsDirOut must follow RunContext logs_dir_out (prevents US debug/path bleed).
  $logsDirOut = $logsDir
  # A3: recompute statusPath after forcing logsDirOut
  $statusPath = Join-Path $logsDirOut "blockg_status_stub.json"
if(-not $logsDir){ throw "[FAIL-CLOSED] rcA3.logs_dir_out empty" }

if(($Market -ne "US") -and ($logsDir -match "\\\\logs\\\\US(\\\\|$)")){ throw ("[FAIL-CLOSED] US_LOG_BLEED: Market=" + $Market + " logsDir=" + $logsDir) }
# A3_FORCE_LOGSDIR_FROM_RUNCONTEXT_END

$todayLocal = _SliceDate ([string]$rcA3.as_of_date)
$tsUtc = (Get-Date).ToUniversalTime().ToString("o")

    function _Slice([string]$d){ $t=(($d+"")).Trim(); if($t.Length -ge 10){ $t=$t.Substring(0,10) }; $t }
    function _ToBool($v){ $s=(($v+"")).Trim().ToLowerInvariant(); return ($s -in @("1","true","yes","y","ok","pass","passed")) }
# GREADY_MAP_OKTODAY_V1_BEGIN
# StrictMode-safe: map ok_today -> <component>_ok_today for Global-Ready files.
function _PickOkToday([object]$j, [string]$preferredKey){
  if($null -eq $j){ return $false }
  try{
    if($j.PSObject.Properties.Name -contains $preferredKey){ return [bool]$j.$preferredKey }
    if($j.PSObject.Properties.Name -contains "ok_today"){ return [bool]$j.ok_today }
    if($j.PSObject.Properties.Name -contains "ok"){ return [bool]$j.ok }
  } catch { }
  return $false
}
# GREADY_MAP_OKTODAY_V1_END
# GSFLAGS_DIAG_HELPER_V1_BEGIN
# StrictMode-safe GSFLAGS diagnostics resolver (dashboard-only; NO gating changes).
function Resolve-GSFlagsDiag {
  param(
    [bool]$MarketClosedToday,
    [object]$GsRecentEnough
  )
  $re = $false
  $fs = $false
  try {
    if($null -ne $GsRecentEnough){
      $re = [bool]$GsRecentEnough
      $fs = [bool]$GsRecentEnough
    }
  } catch { $re = $false; $fs = $false }

  if($MarketClosedToday){
    $re = $true
    $fs = $true
  }

  return [ordered]@{
    recent_enough = [bool]$re
    fresh_for_session = [bool]$fs
  }
}
# GSFLAGS_DIAG_HELPER_V1_END

    # Ensure logsRoot points to repo-root logs (not market logs) for fallback paths
    if(-not (Get-Variable -Name "logsRoot" -Scope Local -ErrorAction SilentlyContinue)){
      $logsRoot = Join-Path $repoRoot "logs"
    } elseif(-not $logsRoot){
      $logsRoot = Join-Path $repoRoot "logs"
    }

    # MARKET_SELECTOR_AUDIT_BEGIN
    # Audit-only: read market_selector.json (producer: tools/Build-MarketSelector.ps1)
    $ms_ok_today = $false
    $ms_decision = "NO_TRADE"
    $ms_chosen_market = ""
    $ms_chosen_module = ""
    $ms_reason = "missing_market_selector_json"
    try {
      $msPath = Prefer-LogsPath (Join-Path $logsDirOut "market_selector.json") (Join-Path $logsDir "market_selector.json")
      $msPath = Prefer-LogsPath $msPath (Join-Path $logsRoot "market_selector.json")
      if($msPath -and (Test-Path -LiteralPath $msPath)){
        $msj = $null
        try { $msj = (Get-Content -LiteralPath $msPath -Raw -Encoding UTF8 | ConvertFrom-Json -ErrorAction Stop) } catch { $msj = $null }
        if($msj){
          if($msj.PSObject.Properties.Name -contains "ok_today"){ $ms_ok_today = [bool]$msj.ok_today }
          if($msj.PSObject.Properties.Name -contains "decision"){ $ms_decision = ([string]$msj.decision).Trim() }
          if($msj.PSObject.Properties.Name -contains "chosen_market"){ $ms_chosen_market = ([string]$msj.chosen_market).Trim() }
          if($msj.PSObject.Properties.Name -contains "chosen_module"){ $ms_chosen_module = ([string]$msj.chosen_module).Trim() }
          if($msj.PSObject.Properties.Name -contains "reason"){ $ms_reason = ([string]$msj.reason).Trim() }
        }
      }
    } catch { }
    # MARKET_SELECTOR_AUDIT_END

    # Phase23 today
    $phase23Ok=$false
    # A2: prefer producer status json (fallback to CSV below)
$p23s = Prefer-LogsPath (Join-Path $logsDir "phase23_status.json") (Join-Path $logsRoot "phase23_status.json")
    $p23ok = Read-StatusOkToday $p23s $todayLocal
    if($null -ne $p23ok){ $phase23Ok = [bool]$p23ok }
$p23 = Prefer-LogsPath (Join-Path $logsDir "phase23_health_daily.csv") (Join-Path (Join-Path $repoRoot "logs") "phase23_health_daily.csv")
    if(Test-Path -LiteralPath $p23){
      try{
        $rows=@(Import-Csv -LiteralPath $p23)
        foreach($r in $rows){
          $d=""
          if($r.PSObject.Properties.Name -contains "date"){ $d=_Slice $r.date }
          elseif($r.PSObject.Properties.Name -contains "as_of_date"){ $d=_Slice $r.as_of_date }
          if($d -ne $todayLocal){ continue }
          if($r.PSObject.Properties.Name -contains "phase23_ok"){ $phase23Ok=_ToBool $r.phase23_ok }
        }
      } catch { $phase23Ok=$false }
    }

    # EV-hard today
    $evHardOk=$false
    # EVH_STATUS_JSON_STICKY_BEGIN
    $evHardOkFromStatusJson = $false
    # EVH_STATUS_JSON_STICKY_END
    # A2: prefer producer status json (fallback to CSV below)
$evs = Prefer-LogsPath (Join-Path $logsDir "ev_hard_status.json") (Join-Path $logsRoot "ev_hard_status.json")
    # EVH_STATUS_JSON_AUTHORITY_BEGIN
    # A2 coherence: if per-market ev_hard_status.json exists for todayLocal, it is authoritative for evHardOk.
    try {
      if($evs -and (Test-Path -LiteralPath $evs)){
        $evj = $null
        try { $evj = (Get-Content -LiteralPath $evs -Raw -Encoding UTF8 | ConvertFrom-Json -ErrorAction Stop) } catch { $evj = $null }
        if($evj -and ($evj.PSObject.Properties.Name -contains "as_of_date")){
          $d = [string]$evj.as_of_date; if($d.Length -ge 10){ $d = $d.Substring(0,10) }
          if($d -eq $todayLocal){
            $evHardOkFromStatusJson = $true
            if($evj.PSObject.Properties.Name -contains "ok_today"){ $evHardOk = [bool]$evj.ok_today }
            if($evj.PSObject.Properties.Name -contains "not_evaluated_market_closed"){ $ev_hard_not_evaluated_market_closed = [bool]$evj.not_evaluated_market_closed }
          }
        }
      }
    } catch { }
    # EVH_STATUS_JSON_AUTHORITY_END
# ---- C5 Global-Ready gates (fail-closed) ----
Ensure-GlobalReadyV0 -Market $Market -LogsDir $logsDir -TodayLocal $todayLocal
$gdnaPath  = Prefer-LogsPath (Join-Path $logsDir "market_dna.json") (Join-Path $logsRoot "market_dna.json")
$gedgePath = Prefer-LogsPath (Join-Path $logsDir "edge_validity.json") (Join-Path $logsRoot "edge_validity.json")
$gdepPath  = Prefer-LogsPath (Join-Path $logsDir "dependency_risk.json") (Join-Path $logsRoot "dependency_risk.json")
$griskPath = Prefer-LogsPath (Join-Path $logsDir "risk_guard_status.json") (Join-Path $logsRoot "risk_guard_status.json")
$gdnaOk  = $false
$gedgeOk = $false
$gdepOk  = $false
$griskOk = $false

try { $gdnaOk  = Read-StatusOkToday $gdnaPath  $todayLocal } catch { $gdnaOk  = $false }
try { $gedgeOk = Read-StatusOkToday $gedgePath $todayLocal } catch { $gedgeOk = $false }
try { $gdepOk  = Read-StatusOkToday $gdepPath  $todayLocal } catch { $gdepOk  = $false }
try { $griskOk = Read-StatusOkToday $griskPath $todayLocal } catch { $griskOk = $false }

$globalReadyOk = ([bool]$gdnaOk -and [bool]$gedgeOk -and [bool]$gdepOk -and [bool]$griskOk)
# Ensure reasons list exists before C5 adds (StrictMode-safe)
if(-not (Get-Variable -Name "reasons" -Scope Local -ErrorAction SilentlyContinue)){
  $reasons = New-Object System.Collections.Generic.List[string]
}
# Ensure reasons list exists before C5 adds (StrictMode-safe)
if(-not (Get-Variable -Name "reasons" -Scope Local -ErrorAction SilentlyContinue)){
  $reasons = New-Object System.Collections.Generic.List[string]
}if(-not $gdnaOk){  $reasons.Add("market_dna_ok_today=false") | Out-Null }
if(-not $gedgeOk){ $reasons.Add("edge_validity_ok_today=false") | Out-Null }
if(-not $gdepOk){  $reasons.Add("dependency_risk_ok_today=false") | Out-Null }
if(-not $griskOk){ $reasons.Add("risk_guard_ok_today=false") | Out-Null }
# ---- end C5 ----
    if(-not $evHardOkFromStatusJson){
    $evDecided = $false
    $evok = Read-StatusOkToday $evs $todayLocal
if($null -ne $evok){ $evHardOk = [bool]$evok; $evAsOf=$todayLocal; $evDecided = $true }
if(-not $evDecided){ $evAsOf="" }
if(-not $evDecided){
$evp = Prefer-LogsPath (Join-Path $logsDir "phase5_ev_hard_veto_daily.csv") (Join-Path (Join-Path $repoRoot "logs") "phase5_ev_hard_veto_daily.csv")
    if(Test-Path -LiteralPath $evp){
      try{
        $rows=@(Import-Csv -LiteralPath $evp)
        foreach($r in $rows){
          if(_Slice $r.date -eq $todayLocal){
            $evAsOf=$todayLocal
            if($r.PSObject.Properties.Name -contains "ok"){ $evHardOk=_ToBool $r.ok } else { $evHardOk=$true }
            break
          }
        }
      } catch { $evHardOk=$false }
    }

}

    }
    # Phase4 today
    $phase4Ok=$false
    # A2: prefer producer status json (fallback to legacy JSON below)
$p4s = Prefer-LogsPath (Join-Path $logsDir "phase4_status.json") (Join-Path $logsRoot "phase4_status.json")
    $p4ok = Read-StatusOkToday $p4s $todayLocal
    if($null -ne $p4ok){ $phase4Ok = [bool]$p4ok }
$p4 = Prefer-LogsPath (Join-Path $logsDir "phase4_validation_passed.json") (Join-Path $logsRoot "phase4_validation_passed.json")
    if(Test-Path -LiteralPath $p4){
      try{
        $j = Get-Content -LiteralPath $p4 -Raw -Encoding UTF8 | ConvertFrom-Json
        $asOf = _Slice ([string]$j.as_of_date)
        $ok = $false
        if($j.PSObject.Properties.Name -contains "phase4_ok_today"){ $ok = [bool]$j.phase4_ok_today }
        $phase4Ok = ($asOf -eq $todayLocal -and $ok)
      } catch { $phase4Ok=$false }
    }
    # GateScore as_of (FAST, institutional): prefer resolved events file (tail scan), fallback to summary CSV
    $gsAsOf=""
    $gsOkToday=$false

    try {
      $evPath = Resolve-GatescoreEventsPath "NVDA" $logsDir
      $mx = Get-MaxAsOfDateFromJsonlTail -Path $evPath -TailLines 8000
      if($mx){ $gsAsOf = $mx }
      # If events file has any rows stamped todayLocal, treat GateScore as fresh today (fail-closed).
      if(Has-TodayAsOfDateInJsonlTail -Path $evPath -Today $todayLocal -TailLines 8000){ $gsAsOf = $todayLocal }
    } catch { $gsAsOf="" }

    if(-not $gsAsOf){
      $pnl = Join-Path $logsDir "gatescore_pnl_summary.csv"
      if(-not (Test-Path -LiteralPath $pnl)){ $pnl = Join-Path $logsDir "gatescore_daily_summary.csv" }
      if(Test-Path -LiteralPath $pnl){
        try{
          $rows=@(Import-Csv -LiteralPath $pnl)
          if($rows.Count -gt 0){
            $last=$rows[-1]
            if($last.PSObject.Properties.Name -contains "as_of_date"){ $gsAsOf=_Slice ([string]$last.as_of_date) }
          }
        } catch { $gsAsOf="" }
      }
    }

    $gsFreshToday = ($gsAsOf -ne "" -and $gsAsOf -eq $todayLocal)
$reasons = New-Object System.Collections.Generic.List[string]
    if(-not $phase23Ok){ $reasons.Add("phase23_health_ok_today=false") | Out-Null }
    if(-not $evHardOk){  $reasons.Add("ev_hard_daily_ok_today=false") | Out-Null }
    if(-not $phase4Ok){  $reasons.Add("phase4_ok_today=false") | Out-Null }
    if(-not $gsFreshToday){ $reasons.Add("gatescore_fresh_today=false") | Out-Null }

    $nvdaReady = ($phase23Ok -and $evHardOk -and $phase4Ok -and $gsFreshToday)

    # REGIME_READER_BEGIN
# Regime fields (producer: regime_status.json). Per-market log root.
$regime = "NORMAL"
$regimeOkToday = $false
$regimeReason = "missing_regime_status_json"
$regimePath = Join-Path $logsDirOut "regime_status.json"
try {
  if(Test-Path -LiteralPath $regimePath){
    $rj = Get-Content -LiteralPath $regimePath -Raw -Encoding UTF8 | ConvertFrom-Json
    if($rj){
      if($rj.PSObject.Properties.Name -contains "regime"){ $regime = [string]$rj.regime }
      if($rj.PSObject.Properties.Name -contains "regime_ok_today"){ $regimeOkToday = [bool]$rj.regime_ok_today }
      if($rj.PSObject.Properties.Name -contains "regime_reason"){ $regimeReason = [string]$rj.regime_reason }
    }
  }
} catch {
  $regimeOkToday = $false
  $regimeReason = "regime_status_parse_failed"
}
$crisisAlphaEnabled = $false
# REGIME_READER_END

# POLICYB_GSFLAGS_DIAG_SHARED_V1_BEGIN
# Policy B: GSFLAGS diagnostics for FAST payload (NO gating changes).
$gsRecentEnough_diag = $false
$gsFreshForSession_diag = $false
try {
  $d = Resolve-GSFlagsDiag -MarketClosedToday:$marketClosedToday -GsRecentEnough $null
  $gsRecentEnough_diag = [bool]$d.recent_enough
  $gsFreshForSession_diag = [bool]$d.fresh_for_session
} catch { $gsRecentEnough_diag = $false; $gsFreshForSession_diag = $false }
# POLICYB_GSFLAGS_DIAG_SHARED_V1_END

  # EVH_FINALMILE_SAFE_BEGIN
  # A2 coherence: compute evHardOk_final from per-market ev_hard_status.json (todayLocal) OUTSIDE payload hash (parser-safe).
  $evHardOk_final = $evHardOk
  try {
    $pEv = Join-Path $logsDir "ev_hard_status.json"
    if(Test-Path -LiteralPath $pEv){
      $jEv = $null
      try { $jEv = (Get-Content -LiteralPath $pEv -Raw -Encoding UTF8 | ConvertFrom-Json -ErrorAction Stop) } catch { $jEv = $null }
      if($jEv -and ($jEv.PSObject.Properties.Name -contains "as_of_date")){
        $dEv = [string]$jEv.as_of_date; if($dEv.Length -ge 10){ $dEv = $dEv.Substring(0,10) }
        if($dEv -eq $todayLocal){
          if($jEv.PSObject.Properties.Name -contains "ok_today"){ $evHardOk_final = [bool]$jEv.ok_today }
          if($jEv.PSObject.Properties.Name -contains "not_evaluated_market_closed"){ $ev_hard_not_evaluated_market_closed = [bool]$jEv.not_evaluated_market_closed }
        }
      }
    }
  } catch { }
  # EVH_FINALMILE_SAFE_END

# MARKET_SELECTOR_PAYLOAD_DEFAULTS_BEGIN
# Fail-closed: ensure selector vars exist in payload scope (StrictMode-safe).
$ms_ok_today = $false
$ms_decision = "NO_TRADE"
$ms_chosen_market = ""
$ms_chosen_module = ""
$ms_reason = "missing_market_selector_json"
try {
  $msPath2 = Prefer-LogsPath (Join-Path $logsDirOut "market_selector.json") (Join-Path $logsDir "market_selector.json")
  $msPath2 = Prefer-LogsPath $msPath2 (Join-Path $logsRoot "market_selector.json")
  if($msPath2 -and (Test-Path -LiteralPath $msPath2)){
    $msj2 = $null
    try { $msj2 = (Get-Content -LiteralPath $msPath2 -Raw -Encoding UTF8 | ConvertFrom-Json -ErrorAction Stop) } catch { $msj2 = $null }
    if($msj2){
      if($msj2.PSObject.Properties.Name -contains "ok_today"){ $ms_ok_today = [bool]$msj2.ok_today }
      if($msj2.PSObject.Properties.Name -contains "decision"){ $ms_decision = ([string]$msj2.decision).Trim() }
      if($msj2.PSObject.Properties.Name -contains "chosen_market"){ $ms_chosen_market = ([string]$msj2.chosen_market).Trim() }
      if($msj2.PSObject.Properties.Name -contains "chosen_module"){ $ms_chosen_module = ([string]$msj2.chosen_module).Trim() }
      if($msj2.PSObject.Properties.Name -contains "reason"){ $ms_reason = ([string]$msj2.reason).Trim() }
    }
  }
} catch { }
# MARKET_SELECTOR_PAYLOAD_DEFAULTS_END

$payload = [ordered]@{
      ts_utc=$tsUtc
      as_of_date = $todayLocal
      builder_path = "FAST"
      contract_semantics_reason = ""  # FAST is not authoritative for LIVE eligibility
    contract_semantics_level = $contract_semantics_level
      date = $todayLocal
      is_trading_day=[bool]$rcIsTradingDayFast
      session_name=[string]$rcSessionNameFast
      phase23_health_ok_today=[bool]$phase23Ok
      phase23_not_evaluated_market_closed = [bool]$marketClosedToday
      ev_hard_daily_ok_today=[bool]$evHardOk
      ev_hard_daily_as_of_date=$evAsOf
      phase4_ok_today=[bool]$phase4Ok
      gatescore_as_of_date=$gsAsOf
      gatescore_fresh_today=[bool]$gsFreshToday
      gatescore_age_days=0
      gatescore_recent_enough=$gsRecentEnough_diag
      gatescore_fresh_for_session=$gsFreshForSession_diag
      gatescore_ok_today=[bool]$gsFreshToday
      nvda_blockg_ready=[bool]$nvdaReady
      reasons_not_ready=@($reasons)
      build_mode="FAST_PHASE3"
    }

    $enc = New-Object System.Text.UTF8Encoding($false)
    $script:__emit_reached = $true
    [System.IO.File]::WriteAllText($statusPath, ($payload | ConvertTo-Json -Depth 6), $enc)
    Write-Host ("[BLOCK-G] FAST stub wrote: " + $statusPath) -ForegroundColor Yellow
    if([bool]$marketClosedToday){ return }  # closed day: FAST is authoritative
    # open day: continue into FULL builder for FULL_LIVE_ELIGIBLE computation
  } catch {
    # Fail-closed: still try to emit something
    try{
      $statusPath = Join-Path $logsDirOut "blockg_status_stub.json"
# --- BREADCRUMB (debug, deterministic) ---
try {
  $toolsDir = Split-Path -Parent $PSCommandPath
  $crumbPath = Join-Path $toolsDir "blockg_builder_breadcrumb.txt"
  $msg = @(
    ("ts=" + (Get-Date).ToString("s")),
    ("repoRoot=" + $repoRoot),
    ("logsDir=" + $logsDir),
    ("statusPath=" + $statusPath),
    ("pwd=" + (Get-Location).Path)
  ) -join "`r`n"
  [System.IO.File]::WriteAllText($crumbPath, $msg, (New-Object System.Text.UTF8Encoding($false)))
} catch { }
# --- END BREADCRUMB ---
      $enc = New-Object System.Text.UTF8Encoding($false)
      [System.IO.File]::WriteAllText($statusPath, '{"ok":false,"reason":"fast_builder_exception"}', $enc)
    } catch { }
    if([bool]$marketClosedToday){ return }  # closed day: FAST fail-closed returns
    # open day: continue into FULL builder (fail-closed later if needed)
  }
}
# --- END FAST BUILDER MODE ---
# INTEL_CONTRACT_BEGIN
function _SliceDate([string]$d){
  if(-not $d){ return "" }
  if($d.Length -ge 10){ return $d.Substring(0,10) }
  return $d
}
function _TryParseUtc([string]$s){
  try { return [datetime]::Parse($s, $null, [System.Globalization.DateTimeStyles]::AssumeUniversal).ToUniversalTime() } catch { return $null }
}

# Fail-closed intel contract fields (source of truth: logs\risk_pulse.jsonl)
$intel_ok_today = $false
$intel_as_of_date = ""
$intel_age_minutes = 999999
$intel_kind = ""
# Intel pulse path: prefer per-market, then logs root, then logs\.intel
$intel_source_path = Prefer-LogsPath (Join-Path $logsDir "risk_pulse.jsonl") (Join-Path $logsRoot "risk_pulse.jsonl")
$intel_source_path = Prefer-LogsPath $intel_source_path (Join-Path $logsRoot ".intel\risk_pulse.jsonl")

try{
  if(Test-Path -LiteralPath $intel_source_path){
    $lines = @(Get-Content -LiteralPath $intel_source_path -Encoding utf8)
    # scan from bottom for most recent intel_* pulse
    for($i=$lines.Count-1; $i -ge 0; $i--){
      $s = ($lines[$i] + "").Trim()
      if(-not $s){ continue }
      $j = $null
      try { $j = $s | ConvertFrom-Json } catch { continue }
      if($null -eq $j){ continue }
      $props = $j.PSObject.Properties.Name
      if($props -contains "kind"){
        $k = (($j.kind)+"").Trim()
        if($k -match '^(?i)intel_'){
          $intel_kind = $k
          if($props -contains "as_of_date"){ $intel_as_of_date = _SliceDate(([string]$j.as_of_date)) }
          if($props -contains "ts_utc"){
            $dt = _TryParseUtc(([string]$j.ts_utc))
            if($dt){
              $intel_age_minutes = [int][math]::Floor(((Get-Date).ToUniversalTime() - $dt).TotalMinutes)
            }
          }
          break
        }
      }
    }
  }
}catch{ }

# Today-ness + freshness: require as_of_date == today and age <= 180 minutes (tuneable)
$rcA3 = Get-RunContextOrFail $repoRoot $Market $Symbol
$todayLocal = _SliceDate ([string]$rcA3.as_of_date)
$intel_ok_today = ($intel_as_of_date -eq $todayLocal -and $intel_age_minutes -le 180)

# Per-symbol field (NVDA only right now)
$nvda_intel_ok_today = $intel_ok_today
# INTEL_CONTRACT_END

# GS_METRICS_SOURCE_CAPTURE_BEGIN
$gatescore_metrics_source = ""
$gsMsSeenCount = 0
$gsMsTop = ""
$gsMsPath = ""
$gsMsToday = ""
$gsMsExists = $false

try {
$rcA3 = Get-RunContextOrFail $repoRoot $Market $Symbol
$todayLocal = _SliceDate ([string]$rcA3.as_of_date)
# GS_ASOF_FORCE_FROM_EVENTS_BEGIN
# FINAL AUTHORITY: gsAsOf must follow the resolved NVDA events file (array OR jsonl).
try {
  $selNvda = Resolve-GatescoreEventsPath "NVDA" $logsDir
  $mx = Get-MaxAsOfDateFromJsonl $selNvda
  if($mx){ $gsAsOf = $mx }
} catch { }
# GS_ASOF_FORCE_FROM_EVENTS_END
# GS_ASOF_FROM_EVENTS_BEGIN
# GateScore session date must follow the selected NVDA source for TODAY (paper vs replay).
try {
  $sel = Resolve-GatescoreEventsPath "NVDA" $logsDir
  $gsAsOf = Get-MaxAsOfDateFromJsonl $sel
} catch { $gsAsOf = "" }
# GS_ASOF_FROM_EVENTS_END
  $gsMsToday = $todayLocal

  $p = Join-Path $logsDir "nvda_gatescore_events.jsonl"
  $gsMsPath = $p
  $gsMsExists = [bool](Test-Path -LiteralPath $p)

  if ($gsMsExists) {
    $seen = @{}
    foreach($ln in (Get-Content -LiteralPath $p -Encoding utf8)) {
      $s = ($ln + "").Trim(); if(-not $s){ continue }
      try {
        $o = $s | ConvertFrom-Json
        $d = ($o.as_of_date + "")
        if($d.Length -ge 10){ $d = $d.Substring(0,10) }
        if($d -ne $todayLocal){ continue }

        if($o.PSObject.Properties.Name -contains "metrics_source"){
          $ms = ([string]$o.metrics_source).Trim()
          if($ms){
            if(-not $seen.ContainsKey($ms)){ $seen[$ms]=0 }
            $seen[$ms] += 1
          }
        }
      } catch { }
    }
    $gsMsSeenCount = [int]$seen.Count
    if($seen.Count -gt 0){
      $gsMsTop = ($seen.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 1).Name
      $gatescore_metrics_source = $gsMsTop
    }
  }
} catch {
  $gatescore_metrics_source = ""
  $gsMsSeenCount = 0
  $gsMsTop = ""
  $gsMsToday = ""
  $gsMsExists = $false
}
# GS_METRICS_SOURCE_CAPTURE_END
# PROXY_METRICS_SOURCE_LIVE_VETO_BEGIN
# Institutional rule: proxy GateScore sources are NEVER live-eligible.
# We still compute/record them, but we fail-closed for live readiness.
$gsMetricsSourceDisallowedForLive = $false
try {
  if ($gatescore_metrics_source) {
    $ms = ([string]$gatescore_metrics_source).Trim()
    if ($ms -match '^(?i)proxy_') { $gsMetricsSourceDisallowedForLive = $true }
  }
} catch { $gsMetricsSourceDisallowedForLive = $false }
# PROXY_METRICS_SOURCE_LIVE_VETO_END
# MICRO_SOURCE_LIVE_VETO_BEGIN
# Institutional: derived micro_score is DIAGNOSTIC-ONLY and must never arm live.
$microSourceDisallowedForLive = $false
$microSourceTop = ""
try {
  $todayLocal2 = (Get-Date).ToString("yyyy-MM-dd")
  $p = Join-Path $logsDir "nvda_gatescore_events.jsonl"
  if(Test-Path -LiteralPath $p){
    $seen = @{}
    foreach($ln in (Get-Content -LiteralPath $p -Encoding utf8)){
      $s = ($ln + "").Trim(); if(-not $s){ continue }
      try {
        $o = $s | ConvertFrom-Json
        $d = ($o.as_of_date + "")
        if($d.Length -ge 10){ $d = $d.Substring(0,10) }
        if($d -ne $todayLocal2){ continue }
        if($o.PSObject.Properties.Name -contains "micro_score_source"){
          $ms = ([string]$o.micro_score_source).Trim()
          if($ms){
            if(-not $seen.ContainsKey($ms)){ $seen[$ms]=0 }
            $seen[$ms] += 1
          }
        }
      } catch { }
    }
    if($seen.Count -gt 0){
      $microSourceTop = ($seen.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 1).Name
      if($microSourceTop -match '^(?i)derived_'){ $microSourceDisallowedForLive = $true }
    }
  }
} catch { $microSourceDisallowedForLive = $false; $microSourceTop="" }
# MICRO_SOURCE_LIVE_VETO_END

# GS_ELIGIBLE_ZERO_BEGIN
# RUNCONTEXT_HELPER_BEGIN
function Read-RunContextSafe([string]$RepoRoot,[string]$Market,[string]$Symbol,[string]$AsOfDate){
  $rcPath = Join-Path $RepoRoot "tools\Resolve-RunContext.ps1"
  if(-not (Test-Path -LiteralPath $rcPath)){ return $null }

  $args = @("-NoProfile","-ExecutionPolicy","Bypass","-File",$rcPath,"-Market",$Market,"-Symbol",$Symbol)
  if((($AsOfDate + "")).Trim()){ $args += @("-AsOfDate",$AsOfDate) }

  $raw = & powershell @args 2>$null | Out-String
  $raw = ($raw + "").Trim()
  if(-not $raw){ return $null }

  $i0 = $raw.IndexOf('{')
  $i1 = $raw.LastIndexOf('}')
  if($i0 -lt 0 -or $i1 -le $i0){ return $null }

  $json = $raw.Substring($i0, ($i1 - $i0 + 1))
  try { return ($json | ConvertFrom-Json -ErrorAction Stop) } catch { return $null }
}
# RUNCONTEXT_HELPER_END

# MARKET_CONTEXT_AUTHORITY_BEGIN
# Phase-5: market truth authority via RunContext (single truth).
# Fail-closed on any error => market_closed_today=true, is_open_now=false, session_name="CLOSED"
$rcSessionName = "CLOSED"
$rcIsTradingDay = $false
$marketIsOpenNow = $false
$marketClosedToday = $true
try {
  $rc = Read-RunContextSafe $repoRoot $Market $Symbol $todayLocal
  if($rc){
    if($rc.PSObject.Properties.Name -contains "market_closed_today"){ $marketClosedToday = [bool]$rc.market_closed_today }
    if($rc.PSObject.Properties.Name -contains "is_open_now"){ $marketIsOpenNow = [bool]$rc.is_open_now }
    if($rc.PSObject.Properties.Name -contains "session_name"){ $rcSessionName = [string]$rc.session_name }
    if($rc.PSObject.Properties.Name -contains "is_trading_day"){ $rcIsTradingDay = [bool]$rc.is_trading_day }
  }
} catch {
  $marketClosedToday = $true
  $marketIsOpenNow = $false
  $rcSessionName = "CLOSED"
  $rcIsTradingDay = $false
}
# MARKET_CONTEXT_AUTHORITY_END
# EVH_MARKET_CLOSED_AUDIT_BEGIN
# Audit-only clarity: when market is closed we do not treat EV-hard as "passed".
$ev_hard_not_evaluated_market_closed = $false
$phase23_not_evaluated_market_closed = $false
try { if($marketClosedToday){ $phase23_not_evaluated_market_closed = $true } } catch { $phase23_not_evaluated_market_closed = $false }
try {
  if($marketClosedToday){ $ev_hard_not_evaluated_market_closed = $true }
} catch { $ev_hard_not_evaluated_market_closed = $false }
# EVH_MARKET_CLOSED_AUDIT_END
# GateScore NVDA data-quality guard: eligible events count
$nvdaEligibleCount = 0
try {
  $nvdaPath = Join-Path $logsDir "nvda_gatescore_events.jsonl"
  if(Test-Path -LiteralPath $nvdaPath){
    foreach($ln in (Get-Content -LiteralPath $nvdaPath -Encoding utf8)){
      $s = $ln.Trim(); if(-not $s){ continue }
      try {
        $o = $s | ConvertFrom-Json
        if($o.PSObject.Properties.Name -contains "eligible" -and [bool]$o.eligible){ $nvdaEligibleCount++ }
      } catch { }
    }
  }
} catch { $nvdaEligibleCount = 0 }

$gsNvdaEligibleZero = ($nvdaEligibleCount -le 0)
# GS_ELIGIBLE_ZERO_END
# GS_NVDA_DIAG_BEGIN
$nvdaLastEventDate = ""
$nvdaMissingMetrics = $false
try {
  $nvdaPath = Join-Path $logsDir "nvda_gatescore_events.jsonl"
  if(Test-Path -LiteralPath $nvdaPath){
    $tail = Get-Content -LiteralPath $nvdaPath -Tail 200 -Encoding utf8
    foreach($ln in $tail){
      $s = $ln.Trim(); if(-not $s){ continue }
      try {
        $o = $s | ConvertFrom-Json
        $d = ""
        if($o.PSObject.Properties.Name -contains "as_of_date"){ $d = Slice-Date ([string]$o.as_of_date) }
        if($d){ $nvdaLastEventDate = $d }
        $erNull = (-not ($o.PSObject.Properties.Name -contains "edge_ratio")) -or ($null -eq $o.edge_ratio)
        $msNull = (-not ($o.PSObject.Properties.Name -contains "micro_score")) -or ($null -eq $o.micro_score)
        if($erNull -and $msNull){ $nvdaMissingMetrics = $true }
      } catch { }
    }
  }
} catch { $nvdaLastEventDate=""; $nvdaMissingMetrics=$false }
# GS_NVDA_DIAG_END
if (-not (Test-Path $logsDir)) { New-Item -ItemType Directory -Path $logsDir -Force | Out-Null }

# Session date (single source of truth): prefer Phase4 stamp as_of_date; fallback to local date
# [A3] Canonical todayLocal must come from RunContext.as_of_date (market-aware). Fail-closed if RunContext missing.
function _SliceDate([string]$d){
  if(-not $d){ return "" }
  $s = ([string]$d).Trim()
  if($s.Length -ge 10){ return $s.Substring(0,10) }
  return $s
}

$today = (Get-Date).ToString("yyyy-MM-dd")
$rcA3 = Get-RunContextOrFail $repoRoot $Market $Symbol
$todayLocal = _SliceDate ([string]$rcA3.as_of_date)
$p4Path = Join-Path $logsDir "phase4_validation_passed.json"
if (Test-Path -LiteralPath $p4Path) {
  try {
    $p4 = (Get-Content -LiteralPath $p4Path -Raw -Encoding utf8 | ConvertFrom-Json)
    $d = [string]$p4.as_of_date
    if ($d -and $d.Length -ge 10) { $today = $d.Substring(0,10) }
    # PHASE4_STAMP_TODAY_GUARD_BEGIN
    # Fail-closed: do NOT let stale Phase4 stamp override local date.
    $localToday = (Get-Date).ToString("yyyy-MM-dd")
    $p4AsOf = ""
    try { $p4AsOf = [string]$p4.as_of_date; if($p4AsOf.Length -ge 10){ $p4AsOf = $p4AsOf.Substring(0,10) } } catch { $p4AsOf = "" }

    if($p4AsOf -and ($p4AsOf -ne $localToday)){
      # keep today as local date; Phase4 is not valid for today
      $today = $localToday
    }
    # PHASE4_STAMP_TODAY_GUARD_END
  } catch { }
}

# ---- GateScore session date (weekend-safe): derive from pnl summary ----
$tsUtc = (Get-Date).ToUniversalTime().ToString("o")
$statusPath = Join-Path $logsDirOut "blockg_status_stub.json"



# --- BREADCRUMB (debug, deterministic) ---
try {
  $toolsDir = Split-Path -Parent $PSCommandPath
  $crumbPath = Join-Path $toolsDir "blockg_builder_breadcrumb.txt"
  $msg = @(
    ("ts=" + (Get-Date).ToString("s")),
    ("repoRoot=" + $repoRoot),
    ("logsDir=" + $logsDir),
    ("statusPath=" + $statusPath),
    ("pwd=" + (Get-Location).Path)
  ) -join "`r`n"
  [System.IO.File]::WriteAllText($crumbPath, $msg, (New-Object System.Text.UTF8Encoding($false)))
} catch { }
# --- END BREADCRUMB ---
# ---- GateScore EVENTS freshness (fail-closed) ----
$GS_MIN_EVENTS_REQUIRED = 25

function Get-GSEventsMeta([string]$RepoRoot, [string]$Sym, [string]$Today){
$logsDir = $logsDirOut
  $p = Resolve-GatescoreEventsPathToday $Sym $logsDir

  $rowsTotal = 0
  $eligibleToday = 0
  $fresh = $false
  $ts = ""

  if(Test-Path -LiteralPath $p){
    try { $rowsTotal = @(Get-Content -LiteralPath $p -Encoding utf8).Count } catch { $rowsTotal = 0 }

    try {
      $it = Get-Item -LiteralPath $p
      $ts = $it.LastWriteTime.ToString("yyyy-MM-dd")
      $fresh = (Has-TodayAsOfDateInJsonlTail -Path $p -Today $todayLocal -TailLines 8000)
    } catch { $fresh = $false; $ts = "" }

    # Quality: count eligible rows for TODAY (prevents toxic files from reporting ok)
    try {
      foreach($ln in (Get-Content -LiteralPath $p -Encoding utf8)){
        $s = ($ln + "").Trim(); if(-not $s){ continue }
        try {
          $o = $s | ConvertFrom-Json
          $d = ""
          if($o.PSObject.Properties.Name -contains "as_of_date"){
            $d = [string]$o.as_of_date
            if($d.Length -ge 10){ $d = $d.Substring(0,10) }
          }
          if ($d -ne $todayLocal) { continue }

          # Eligible semantics: if field missing -> treat as eligible (legacy)
          $ok = $true
          if($o.PSObject.Properties.Name -contains "eligible"){ $ok = [bool]$o.eligible }
          if($ok){ $eligibleToday += 1 }
        } catch { }
      }
    } catch { $eligibleToday = 0 }
  }

  $okMeta = ($fresh -and ($eligibleToday -ge $GS_MIN_EVENTS_REQUIRED))
  return [pscustomobject]@{
    path=$p
    rows_total=[int]$rowsTotal
    eligible_rows_today=[int]$eligibleToday
    fresh=[bool]$fresh
    ts=$ts
    ok=[bool]$okMeta
  }
}
function To-Bool([object]$v) {
    if ($null -eq $v) { return $false }
    $s = ([string]$v).Trim().ToLowerInvariant()
    return $s -in @("1","true","yes","y","ok","pass","passed")
}
function Slice-Date([string]$d) {
    if (-not $d) { return "" }
    if ($d.Length -ge 10) { return $d.Substring(0,10) }
    return $d
}

# ---- GateScore session date (weekend/holiday-safe): derive from pnl summary ----
# ---- GateScore session date (weekend/holiday-safe): derive from pnl summary ----
$pnlPath = Prefer-LogsPath (Join-Path $logsDir "gatescore_pnl_summary.csv") (Join-Path $logsRoot "gatescore_pnl_summary.csv")
if (-not (Test-Path -LiteralPath $pnlPath)) {
  # backward-compatible fallback (older name)
$pnlPath = Prefer-LogsPath (Join-Path $logsDir "gatescore_daily_summary.csv") (Join-Path $logsRoot "gatescore_daily_summary.csv")
}
$gsAsOf = ""
if (Test-Path $pnlPath) {
  try {
    $pnlRows = @(Import-Csv $pnlPath)
    $dates = @($pnlRows | ForEach-Object { Slice-Date ([string]$_.as_of_date) } | Where-Object { $_ })
    if ($dates.Count -gt 0) { $gsAsOf = ($dates | Sort-Object | Select-Object -Last 1) }
  } catch { $gsAsOf = "" }
}
if (-not $gsAsOf) {
  # No reliable GateScore session available (holiday/off-session). Keep blank to avoid false "today".
  $gsAsOf = ""
}
# GS_ASOF_FALLBACK_FROM_EVENTS_TAIL_BEGIN
# If summary CSV is missing/blank, fall back to resolved events tail max as_of_date (single truth).
if (-not $gsAsOf) {
  try {
    $evPath2 = Resolve-GatescoreEventsPath "NVDA" $logsDir
    $mx2 = Get-MaxAsOfDateFromJsonlTail -Path $evPath2 -TailLines 8000
    if ($mx2) { $gsAsOf = $mx2 }
  } catch { }
}
# GS_ASOF_FALLBACK_FROM_EVENTS_TAIL_END

# GS_ASOF_TODAY_PRESENT_OVERRIDE_BEGIN
# If resolved events has any rows stamped todayLocal, treat GateScore as fresh today (fail-closed).
try {
  $evPathToday = Resolve-GatescoreEventsPathToday "NVDA" $logsDir
  if(Has-TodayAsOfDateInJsonlTail -Path $evPathToday -Today $todayLocal -TailLines 8000){
    $gsAsOf = $todayLocal
  }
} catch { }
# GS_ASOF_TODAY_PRESENT_OVERRIDE_END

# A2_GS_SUMMARY_NONLIVE_BEGIN
# PAPER/PAPERLIVE: use per-market GateScore summary CSV as the contract truth for legacy fields.
# LIVE: unchanged (still uses per-event evaluator + live minima + source vetoes).
try {
  $mode = $script:__HAT_RUNMODE
  if($mode -ne "LIVE"){
    # Prefer pnl summary, else daily summary
    $gsCsv = Join-Path $logsDir "gatescore_pnl_summary.csv"
    if(-not (Test-Path -LiteralPath $gsCsv)){ $gsCsv = Join-Path $logsDir "gatescore_daily_summary.csv" }

    if(Test-Path -LiteralPath $gsCsv){
      $rows = @(Import-Csv -LiteralPath $gsCsv)
      foreach($r in $rows){
        $d = ""
        if($r.PSObject.Properties.Name -contains "as_of_date"){ $d = Slice-Date ([string]$r.as_of_date) }
        if($d -ne $todayLocal){ continue }
        if((([string]$r.symbol).Trim().ToUpperInvariant()) -ne "NVDA"){ continue }

        # Populate legacy fields from summary (contract-visible)
        try { $gsCount = [int]$r.count_signals } catch { $gsCount = 0 }
        try { $gsPnl   = [int]$r.pnl_samples } catch { $gsPnl = 0 }
        try { $gsEdge  = [double]$r.mean_edge_ratio } catch { $gsEdge = 0.0 }
        try { $gsMicro = [double]$r.mean_micro_score } catch { $gsMicro = 0.0 }

        # Make daily sample flags reflect these values in non-live (informational, still fail-closed if missing)
        $gatescore_daily_samples_ok = ($gsCount -ge [int]$minSignals -and $gsPnl -ge [int]$minPnl)
        $gsSamplesOk = [bool]$gatescore_daily_samples_ok
        $gsThreshOk = ((([double]$gsEdge + 1e-9) -ge [double]$minEdge) -and (([double]$gsMicro + 1e-9) -ge [double]$minMicro))
        $gsOkToday = ($gsFresh -and $gsSamplesOk -and $gsThreshOk)

        break
      }
    }
  }
} catch { }
# A2_GS_SUMMARY_NONLIVE_END
# ---- Phase4 ----
$phase4Ok = Get-Phase4OkToday $repoRoot $logsDirOut $todayLocal
# A2: prefer producer status json (FULL builder) before legacy fallback logic
$p4s = Prefer-LogsPath (Join-Path $logsDir "phase4_status.json") (Join-Path $logsRoot "phase4_status.json")
$p4ok = Read-StatusOkToday $p4s $todayLocal
$p4 = Prefer-LogsPath (Join-Path $logsDir "phase4_validation_passed.json") (Join-Path $logsRoot "phase4_validation_passed.json")
if(-not (Test-Path -LiteralPath $p4)) {
  if($null -ne $p4ok){ $phase4Ok = [bool]$p4ok }
}
# A2: prefer producer status json (FULL builder) before CSV parsing
$evs = Prefer-LogsPath (Join-Path $logsDir "ev_hard_status.json") (Join-Path $logsRoot "ev_hard_status.json")
# ---- C5 Global-Ready gates (fail-closed) ----
Ensure-GlobalReadyV0 -Market $Market -LogsDir $logsDir -TodayLocal $todayLocal
$gdnaPath  = Prefer-LogsPath (Join-Path $logsDir "market_dna.json") (Join-Path $logsRoot "market_dna.json")
$gedgePath = Prefer-LogsPath (Join-Path $logsDir "edge_validity.json") (Join-Path $logsRoot "edge_validity.json")
$gdepPath  = Prefer-LogsPath (Join-Path $logsDir "dependency_risk.json") (Join-Path $logsRoot "dependency_risk.json")
$griskPath = Prefer-LogsPath (Join-Path $logsDir "risk_guard_status.json") (Join-Path $logsRoot "risk_guard_status.json")
$gdnaOk  = $false
$gedgeOk = $false
$gdepOk  = $false
$griskOk = $false

try { $gdnaOk  = Read-StatusOkToday $gdnaPath  $todayLocal } catch { $gdnaOk  = $false }
try { $gedgeOk = Read-StatusOkToday $gedgePath $todayLocal } catch { $gedgeOk = $false }
try { $gdepOk  = Read-StatusOkToday $gdepPath  $todayLocal } catch { $gdepOk  = $false }
try { $griskOk = Read-StatusOkToday $griskPath $todayLocal } catch { $griskOk = $false }

$globalReadyOk = ([bool]$gdnaOk -and [bool]$gedgeOk -and [bool]$gdepOk -and [bool]$griskOk)
# Ensure reasons list exists before C5 adds (StrictMode-safe)
if(-not (Get-Variable -Name "reasons" -Scope Local -ErrorAction SilentlyContinue)){
  $reasons = New-Object System.Collections.Generic.List[string]
}
# Ensure reasons list exists before C5 adds (StrictMode-safe)
if(-not (Get-Variable -Name "reasons" -Scope Local -ErrorAction SilentlyContinue)){
  $reasons = New-Object System.Collections.Generic.List[string]
}if(-not $gdnaOk){  $reasons.Add("market_dna_ok_today=false") | Out-Null }
if(-not $gedgeOk){ $reasons.Add("edge_validity_ok_today=false") | Out-Null }
if(-not $gdepOk){  $reasons.Add("dependency_risk_ok_today=false") | Out-Null }
if(-not $griskOk){ $reasons.Add("risk_guard_ok_today=false") | Out-Null }
# ---- end C5 ----
$evDecided = $false
$evok = Read-StatusOkToday $evs $todayLocal
if($null -ne $evok){ $evHardOk = [bool]$evok; $evHardDailyAsOf=$todayLocal; $evDecided = $true }


# ---- EV hard veto daily ----
if(-not $evDecided){
$evHardOk = $false
$evPath = Prefer-LogsPath (Join-Path $logsDir "phase5_ev_hard_veto_daily.csv") (Join-Path (Join-Path $repoRoot "logs") "phase5_ev_hard_veto_daily.csv")
$evHardDailyAsOf = ""
$evHardOk = $false
if (Test-Path $evPath) {
    $rows = @(Import-Csv $evPath)
    if ($rows -and $rows.Count -gt 0) {
        # As-of date is last row date (audit). Today-ness enforced separately.
        $last = $rows[-1]
        # A2: prefer explicit as_of_date if present; fallback to legacy date column
if($last.PSObject.Properties.Name -contains "as_of_date"){
  $evHardDailyAsOf = Slice-Date ([string]$last.as_of_date)
} else {
  $evHardDailyAsOf = Slice-Date ([string]$last.date)
}

        # Find today row (if any) and enforce ok only for today.
        foreach ($r in $rows) {
            if ((Slice-Date ([string]$r.date)) -eq $todayLocal) {
                $evHardDailyAsOf = $todayLocal
                if ($r.PSObject.Properties.Name -contains "ok") { $evHardOk = To-Bool $r.ok } else { $evHardOk = $true }
                break
            }
        }
    }
}

}
# StrictMode-safe: $evPath must exist even when EV status JSON decides (CSV skipped).
# Define deterministic fallback path for downstream audit blocks.
if(-not (Get-Variable -Name "evPath" -Scope Local -ErrorAction SilentlyContinue)){
  try{
    $evPath = Prefer-LogsPath (Join-Path $logsDir "phase5_ev_hard_veto_daily.csv") (Join-Path $logsRoot "phase5_ev_hard_veto_daily.csv")
  } catch {
    $evPath = (Join-Path $logsDir "phase5_ev_hard_veto_daily.csv")
  }
}
# EVHARD_REASON_CAPTURE_BEGIN
# Capture today's EV-hard daily reason for audit/contract messaging
$evHardReason = ""
try {
  if (Test-Path $evPath) {
    $rows2 = @(Import-Csv $evPath)
    foreach ($r2 in $rows2) {
      if ((Slice-Date ([string]$r2.date)) -eq $todayLocal) {
        if ($r2.PSObject.Properties.Name -contains "reason") { $evHardReason = [string]$r2.reason }
      }
    }
  }
} catch { $evHardReason = "" }
# EVHARD_REASON_CAPTURE_END
# EVH_SNAPSHOT_REASON_BEGIN
$evHardSnapshotReason = ""
try {
  $p = Join-Path $logsDir "ev_hard_snapshot.json"
  if(Test-Path -LiteralPath $p){
    $jj = Get-Content -LiteralPath $p -Raw -Encoding utf8 | ConvertFrom-Json
    if($jj.PSObject.Properties.Name -contains "reason"){ $evHardSnapshotReason = [string]$jj.reason }
  }
} catch { $evHardSnapshotReason = "" }
# EVH_SNAPSHOT_REASON_END


# ---- EV hard veto session preview (does NOT arm live; informational) ----
$evSessionAsOf = ""
$evSessionOk = $false
$evRaw = Join-Path $logsDir "ev_hard_evidence_raw.json"
if (Test-Path $evRaw) {
  try {
    $j = Get-Content $evRaw -Raw -Encoding UTF8 | ConvertFrom-Json
    $evSessionAsOf = Slice-Date ([string]$j.as_of_date)
    $evSessionOk = To-Bool $j.ok
# A2: prefer producer status json (FULL builder) before CSV parsing
$p23s = Prefer-LogsPath (Join-Path $logsDir "phase23_status.json") (Join-Path $logsRoot "phase23_status.json")
$p23ok = Read-StatusOkToday $p23s $todayLocal
if($null -ne $p23ok){ $phase23Ok = [bool]$p23ok; $phase23SawToday = $true }

  } catch { $evSessionAsOf=""; $evSessionOk=$false }
}# ---- Phase23 health (must match today row; fail-closed) ----

# If daily EV-hard veto CSV is missing, fall back to session raw evidence (fail-closed, today-checked downstream)
if((-not (Test-Path -LiteralPath $evPath)) -and $evSessionOk){
  $evHardOk = $true
  $evSessionAsOf = ($evSessionAsOf + "")
}

$phase23Ok = $false
$phase23Path = Prefer-LogsPath (Join-Path $logsDir "phase23_health_daily.csv") (Join-Path (Join-Path $repoRoot "logs") "phase23_health_daily.csv")
$phase23SawToday = $false

if (Test-Path $phase23Path) {
    $rows = @(Import-Csv $phase23Path)
    foreach ($r in $rows) {
        $d = ""
        if ($r.PSObject.Properties.Name -contains "as_of_date") { $d = Slice-Date ([string]$r.as_of_date) }
        elseif ($r.PSObject.Properties.Name -contains "date") { $d = Slice-Date ([string]$r.date) }

        if ($d -ne $todayLocal) { continue }

        $phase23SawToday = $true

        if ($r.PSObject.Properties.Name -contains "phase23_ok") {
            $phase23Ok = To-Bool $r.phase23_ok
        }
        elseif ($r.PSObject.Properties.Name -contains "phase23_health_ok_today") {
            $phase23Ok = To-Bool $r.phase23_health_ok_today
        }
        else {
            # Unknown schema => fail-closed
            $phase23Ok = $false
        }
    }
}

if (-not $phase23SawToday) {
    # No today row => fail-closed
    $phase23Ok = $false
}

# ---- GateScore thresholds (per-symbol) ----
$thrPath = Join-Path $repoRoot "configs\blockg_thresholds.json"
$thrPathDocs = Join-Path $repoRoot "docs\thresholds\blockg_thresholds.json"
$thrOverride = Join-Path $repoRoot "configs\blockg_thresholds.override.json"
if (Test-Path $thrOverride) {
    $isPaper = ($env:HAT_IS_PAPER -eq "1")
    if ($isPaper) { $thrPath = $thrOverride }
}
if (-not (Test-Path $thrPath) -and (Test-Path $thrPathDocs)) { $thrPath = $thrPathDocs }

$thrObj = $null
if (Test-Path $thrPath) {
    try { $thrObj = Get-Content $thrPath -Raw -Encoding UTF8 | ConvertFrom-Json } catch { $thrObj = $null }
}

function Get-ThresholdsFor([string]$sym) {
    $ms = 999999; $mp = 999999; $me = 999.0; $mm = 999.0
    if ($null -ne $thrObj) {
        $k = $sym.ToUpperInvariant()
        $obj = $null
        if ($thrObj.PSObject.Properties.Name -contains $k) { $obj = $thrObj.$k }
        elseif ($thrObj.PSObject.Properties.Name -contains "DEFAULT") { $obj = $thrObj.DEFAULT }
        if ($null -ne $obj) {
            try { $ms = [int]$obj.min_signals } catch { }
            try { $mp = [int]$obj.min_pnl_samples } catch { }
            try { $me = [double]$obj.min_edge_ratio } catch { }
            try { $mm = [double]$obj.min_micro_score } catch { }
        }
    }
    return [pscustomobject]@{ minSignals=$ms; minPnl=$mp; minEdge=$me; minMicro=$mm }
}

# ---- GateScore daily summary (per-symbol today row) ----
$gsPath = $pnlPath  # source-of-truth: gatescore_pnl_summary.csv (fallback daily_summary)
$gsRows = @()
if (Test-Path $gsPath) { $gsRows = @(Import-Csv $gsPath) }

function Get-GSAsOfFromEvents([string]$sym, [string]$logsDir){
  $p = Resolve-GatescoreEventsPath $sym $logsDir
  if(-not (Test-Path -LiteralPath $p)){ return "" }

  $max = ""
  foreach($ln in (Get-Content -LiteralPath $p -Encoding utf8)){
    $s = ($ln + "").Trim(); if(-not $s){ continue }
    try {
      $o = $s | ConvertFrom-Json
      $d = ""
      if($o.PSObject.Properties.Name -contains "as_of_date"){ $d = SliceDate ([string]$o.as_of_date) }
      if($d){
        if((-not $max) -or ($d -gt $max)){ $max = $d }
      }
    } catch { }
  }
  return ($max + "")
}
function Get-GSFor([string]$sym) {
    # Per-symbol GateScore session date (do not reuse NVDA global $gsAsOf)
    if(-not $script:todayLocal){ try { $script:todayLocal = $today } catch { $script:todayLocal = (Get-Date).ToString("yyyy-MM-dd") } }

    $asOfSym = Get-GSAsOfFromEvents $sym $logsDirOut
    if(-not $asOfSym){
      return [pscustomobject]@{ fresh=$false; cnt=0; pnl=0; edge=0.0; micro=0.0 }
    }

    $gs0 = Get-GSFromEvents $sym $asOfSym $todayLocal
    return [pscustomobject]@{ fresh=$gs0.fresh; cnt=$gs0.cnt; pnl=$gs0.pnl; edge=$gs0.edge; micro=$gs0.micro }
}
# --- Institutional LIVE GateScore hard minima (separate from diagnostic thresholds.json) ---
$GS_LIVE_MIN_SIGNALS = 100
$GS_LIVE_MIN_PNL_SAMPLES = 300
$GS_LIVE_MIN_EDGE_RATIO = 0.03
$GS_LIVE_MIN_MICRO_SCORE = 0.55

function Eval-GS([string]$sym) {
    $thr = Get-ThresholdsFor $sym
    $gs  = Get-GSFor $sym
    $samplesOk = ($gs.cnt -ge $thr.minSignals -and $gs.pnl -ge $thr.minPnl)
    $threshOk  = (($gs.edge + 1e-9) -ge $thr.minEdge -and ($gs.micro + 1e-9) -ge $thr.minMicro)
    $okToday   = ($gs.fresh -and $samplesOk -and $threshOk)
    # LIVE-hard thresholds (institutional; independent of gatescore_thresholds.json)
    $samplesOkLive = ($gs.cnt -ge $GS_LIVE_MIN_SIGNALS -and $gs.pnl -ge $GS_LIVE_MIN_PNL_SAMPLES)
    # LIVE_THRESH_ROUNDING_BEGIN
    # Institutional: deterministic compares (avoid float-representation luck).
    $edgeLive  = [math]::Round([double]$gs.edge, 6)
    $microLive = [math]::Round([double]$gs.micro, 6)
    $threshOkLive = ($edgeLive -ge [double]$GS_LIVE_MIN_EDGE_RATIO -and $microLive -ge [double]$GS_LIVE_MIN_MICRO_SCORE)
    # LIVE_THRESH_ROUNDING_END
    $okLiveToday   = ($gs.fresh -and $samplesOkLive -and $threshOkLive)
    return [pscustomobject]@{
        fresh=$gs.fresh; samplesOk=$samplesOk; threshOk=$threshOk; okToday=$okToday; okLiveToday=$okLiveToday; samplesOkLive=$samplesOkLive; threshOkLive=$threshOkLive;
        cnt=$gs.cnt; pnl=$gs.pnl; edge=$gs.edge; micro=$gs.micro;
        minSignals=$thr.minSignals; minPnl=$thr.minPnl; minEdge=$thr.minEdge; minMicro=$thr.minMicro
    }
}

$gsNVDA = Eval-GS "NVDA"
$gsSPY  = Eval-GS "SPY"
$gsQQQ  = Eval-GS "QQQ"

# --- GateScore rolling truth (30 trading days) ---
$ROLL_DAYS = 30
$gsDays = LastNTradingDays $todayLocal $ROLL_DAYS
$gsNVDA_roll = ComputeGateScoreRolling "NVDA" $logsDirOut $gsDays

$gatescore_samples_rolling     = $gsNVDA_roll.samples
$gatescore_pnl_samples_rolling = $gsNVDA_roll.pnl_samples
$gatescore_mean_edge_ratio_rolling  = $gsNVDA_roll.mean_edge
$gatescore_mean_micro_score_rolling = $gsNVDA_roll.mean_micro
# --- explicit sample policy flags (audit) ---
$gatescore_daily_samples_ok   = ([int]$gsNVDA.cnt -ge [int]$gsNVDA.minSignals -and [int]$gsNVDA.pnl -ge [int]$gsNVDA.minPnl)
$gatescore_rolling_samples_ok = ([int]$gatescore_samples_rolling -ge [int]$gsNVDA.minSignals -and [int]$gatescore_pnl_samples_rolling -ge [int]$gsNVDA.minPnl)
# --- end explicit policy flags ---


# GS_LEGACY_DEFAULTS_STRICTMODE_BEGIN
# StrictMode-safe defaults (overwritten later after Eval-GS).
$gsCount = 0
$gsPnl   = 0
$gsEdge  = 0.0
$gsMicro = 0.0
$gsFresh = $false
$minSignals = 999999
$minPnl     = 999999
$minEdge    = 999.0
$minMicro   = 999.0
# GS_LEGACY_DEFAULTS_STRICTMODE_END

# --- FIXED policy metrics + booleans (rolling-first) ---
$gsCountPolicy = if([int]$gatescore_samples_rolling -gt 0){ [int]$gatescore_samples_rolling } else { [int]$gsCount }
$gsPnlPolicy   = if([int]$gatescore_pnl_samples_rolling -gt 0){ [int]$gatescore_pnl_samples_rolling } else { [int]$gsPnl }
$gsEdgePolicy  = [double]$gatescore_mean_edge_ratio_rolling
$gsMicroPolicy = [double]$gatescore_mean_micro_score_rolling
# LIVE policy A: strict daily only (fail-closed)
$gsSamplesOk = [bool]$gatescore_daily_samples_ok
$gsThreshOk = ((([double]$gsNVDA.edge + 1e-9) -ge [double]$gsNVDA.minEdge) -and (([double]$gsNVDA.micro + 1e-9) -ge [double]$gsNVDA.minMicro))  # THRESH_OK_DAILY_FROM_GSNVDA
$gsOkToday   = ([bool]$gsNVDA.fresh -and $gsSamplesOk -and $gsThreshOk)
# NOTE: gsPolicyOk depends on gsRecentEnough, computed later (age policy); we will recompute it after age check.
# --- END FIXED policy metrics + booleans ---


# ---- Legacy GateScore vars (NVDA-based) for backward-compatible payload/reasons ----
$gsFresh     = [bool]$gsNVDA.fresh

$gsCount = [int]$gsNVDA.cnt
$gsPnl   = [int]$gsNVDA.pnl
$gsEdge  = [double]$gsNVDA.edge
$gsMicro = [double]$gsNVDA.micro
# A2_GS_SUMMARY_NONLIVE_POST_BEGIN
# After legacy vars are overwritten from $gsNVDA (which can be 0 in proxy/PAPER modes),
# re-hydrate legacy GateScore fields from per-market summary CSV for PAPER/PAPERLIVE only.
try {
  $mode2 = $script:__HAT_RUNMODE
  if($mode2 -ne "LIVE" -and [int]$gsNVDA.cnt -le 0){
    $gsCsv2 = Join-Path $logsDir "gatescore_pnl_summary.csv"
    if(-not (Test-Path -LiteralPath $gsCsv2)){ $gsCsv2 = Join-Path $logsDir "gatescore_daily_summary.csv" }

    if(Test-Path -LiteralPath $gsCsv2){
      $rows2 = @(Import-Csv -LiteralPath $gsCsv2)
      foreach($r2 in $rows2){
        $d2 = ""
        if($r2.PSObject.Properties.Name -contains "as_of_date"){ $d2 = Slice-Date ([string]$r2.as_of_date) }
        if($d2 -ne $todayLocal){ continue }
        if((([string]$r2.symbol).Trim().ToUpperInvariant()) -ne "NVDA"){ continue }

        try { $gsCount = [int]$r2.count_signals } catch { $gsCount = 0 }
        try { $gsPnl   = [int]$r2.pnl_samples } catch { $gsPnl = 0 }
        try { $gsEdge  = [double]$r2.mean_edge_ratio } catch { $gsEdge = 0.0 }
        try { $gsMicro = [double]$r2.mean_micro_score } catch { $gsMicro = 0.0 }
        break
      }
    }
  }
} catch { }
# A2_GS_SUMMARY_NONLIVE_POST_END

$minSignals = [int]$gsNVDA.minSignals
$minPnl     = [int]$gsNVDA.minPnl
$minEdge    = [double]$gsNVDA.minEdge
$minMicro   = [double]$gsNVDA.minMicro

# Defaults for StrictMode (computed later in GateScore policy block)
$gsAgeDays = 9999
$gsRecentEnough = $false
$gsPolicyOk = [bool]($gsRecentEnough -and $gsSamplesOk -and $gsThreshOk)

$evNVDA = Get-GSEventsMeta $repoRoot "NVDA" $today
$evSPY  = Get-GSEventsMeta $repoRoot "SPY"  $today
$evQQQ  = Get-GSEventsMeta $repoRoot "QQQ"  $today

# ---- Per-symbol ready (institutional) ----
# NOTE: GateScore global fields remain NVDA-based for compatibility; readiness is per-symbol.
$nvdaReady = $phase23Ok -and $evHardOk -and $phase4Ok -and $gsPolicyOk -and $gsNVDA.okLiveToday -and ($gsAsOf -ne "" -and $gsAsOf -eq $todayLocal) -and [bool]$evNVDA.ok
$spyReady = $phase23Ok -and $evHardOk -and $phase4Ok -and $gsPolicyOk -and $gsSPY.okLiveToday -and ($gsAsOf -ne "" -and $gsAsOf -eq $todayLocal) -and [bool]$evSPY.ok
$qqqReady = $phase23Ok -and $evHardOk -and $phase4Ok -and $gsPolicyOk -and $gsQQQ.okLiveToday -and ($gsAsOf -ne "" -and $gsAsOf -eq $todayLocal) -and [bool]$evQQQ.ok
$reasons = New-Object System.Collections.Generic.List[string]
if ($gsMetricsSourceDisallowedForLive) {
  $reasons.Add(("gatescore_metrics_source_disallowed_for_live=" + $gatescore_metrics_source)) | Out-Null
}
if ($marketClosedToday) { $reasons.Add("ev_hard_market_closed_today=true") | Out-Null }
if ($isLiveMode -and $gatescore_metrics_source) { $reasons.Add(("gatescore_metrics_source=" + $gatescore_metrics_source)) | Out-Null }
# GateScore NVDA data-quality reason (audit-only; does not change gating)
# GateScore NVDA data-quality reason (audit-only; does not change gating)
if ($gsNvdaEligibleZero) { $reasons.Add("gatescore_nvda_eligible_zero=true") | Out-Null }
if ($gsNvdaEligibleZero -and $nvdaMissingMetrics) { $reasons.Add("gatescore_nvda_missing_metrics=true") | Out-Null }
if ($gsNvdaEligibleZero -and $nvdaLastEventDate) { $reasons.Add(("gatescore_nvda_last_event_date=" + $nvdaLastEventDate)) | Out-Null }
if (-not $gsAsOf) { $reasons.Add("gatescore_missing_source_data") | Out-Null }


# GateScore policy (session-age based; holiday/weekend safe)
$MAX_GS_AGE_DAYS = 3
$gsAgeDays = 9999
try {
  if ($gsAsOf) {
    $d0 = [datetime]::ParseExact(($gsAsOf + ""), "yyyy-MM-dd", $null)
    $d1 = [datetime]::ParseExact(($todayLocal + ""), "yyyy-MM-dd", $null)
    $gsAgeDays = [int]([math]::Floor(($d1 - $d0).TotalDays))
  # Clamp: age_days must never be negative (market as_of_date can be ahead of local clock).
  if($gsAgeDays -lt 0){ $gsAgeDays = 0 }
  }
} catch { $gsAgeDays = 9999 }

$gsRecentEnough = ($gsAgeDays -le $MAX_GS_AGE_DAYS)
$gsPolicyOk = [bool]($gsRecentEnough -and $gsSamplesOk -and $gsThreshOk)
if (-not $gsRecentEnough) {
  $reasons.Add(("gatescore_too_old age_days=" + $gsAgeDays + " max=" + $MAX_GS_AGE_DAYS + " session=" + $gsAsOf + " today=" + $today)) | Out-Null
}
# QQQ_GS_OK_TODAY omitted for NVDA-only readiness
if($crisisRegime){ $reasons.Add("crisis_regime=true") | Out-Null }
if (-not $phase23Ok) { $reasons.Add("phase23_health_ok_today=false") }
if (-not $evHardOk)  { $reasons.Add("ev_hard_daily_ok_today=false") }
if (-not $evHardOk -and $evHardReason) { $reasons.Add(("ev_hard_daily_reason=" + $evHardReason)) }
if (-not $evHardOk -and $evHardSnapshotReason) { $reasons.Add(("ev_hard_snapshot_reason=" + $evHardSnapshotReason)) }
if (-not $phase4Ok)  { $reasons.Add("phase4_ok_today=false") }
if (-not $gsAsOf -or $gsAsOf -ne $todayLocal) { $reasons.Add("gatescore_fresh_today=false") }
if (-not $gsSamplesOk) { $reasons.Add("gatescore_samples_not_ok") }
# LIVE_HARD_REASONS_BEGIN
try {
  # NVDA live-hard specifics (institutional)
  if (-not $gsNVDA.samplesOkLive) {
    $reasons.Add(("gatescore_live_samples_below_min cnt=" + $gsNVDA.cnt + " pnl=" + $gsNVDA.pnl + " min_cnt=" + $GS_LIVE_MIN_SIGNALS + " min_pnl=" + $GS_LIVE_MIN_PNL_SAMPLES)) | Out-Null
  }
  if (-not $gsNVDA.threshOkLive) {
    # LIVE_REASON_ROUNDING_BEGIN
    $edgeLive6  = [math]::Round([double]$gsNVDA.edge, 6)
    $microLive6 = [math]::Round([double]$gsNVDA.micro, 6)
    if ($edgeLive6 -lt [double]$GS_LIVE_MIN_EDGE_RATIO) {
      $reasons.Add(("gatescore_live_edge_below_min edge=" + $edgeLive6 + " min=" + $GS_LIVE_MIN_EDGE_RATIO)) | Out-Null
    }
    if ($microLive6 -lt [double]$GS_LIVE_MIN_MICRO_SCORE) {
      $reasons.Add(("gatescore_live_micro_below_min micro=" + $microLive6 + " min=" + $GS_LIVE_MIN_MICRO_SCORE)) | Out-Null
    }
    # LIVE_REASON_ROUNDING_END
  }
} catch { }
# LIVE_HARD_REASONS_END
# MICRO_SOURCE_LIVE_VETO_APPLY_BEGIN
try{
  if($microSourceDisallowedForLive){
    $reasons.Add(("micro_score_source_disallowed_for_live=" + $microSourceTop)) | Out-Null
    # Force live deny
    $gsOkToday = $false
    $gsPolicyOk = $false
    $nvdaReady = $false
    $spyReady  = $false
    $qqqReady  = $false
  }
} catch { }
# MICRO_SOURCE_LIVE_VETO_APPLY_END


if (-not $gsThreshOk)  { $reasons.Add("gatescore_below_threshold") }

# Recompute per-symbol readiness AFTER GateScore age policy (StrictMode-safe)
# MARKET_CLOSED_FORCE_SYMBOL_READY_BEGIN
# Institutional: when market is closed, symbol readiness must be false (do not "arm" on closed days).
if ($marketClosedToday) {
  $nvdaReady = $false
  $spyReady  = $false
  $qqqReady  = $false
  try { $reasons.Add("market_closed_forces_symbol_ready=false") | Out-Null } catch { }
}
# MARKET_CLOSED_FORCE_SYMBOL_READY_END
# PROXY_METRICS_SOURCE_FORCE_NOT_READY_BEGIN
if ($gsMetricsSourceDisallowedForLive) {
  # fail-closed: do not allow live readiness on proxy metrics source
  $gsOkToday = $false
  $gsPolicyOk = $false
  $nvdaReady = $false
  $spyReady  = $false
  $qqqReady  = $false
}
# PROXY_METRICS_SOURCE_FORCE_NOT_READY_END
$nvdaReady = $phase23Ok -and $evHardOk -and $phase4Ok -and $gsPolicyOk -and $gsNVDA.okLiveToday -and ($gsAsOf -ne "" -and $gsAsOf -eq $todayLocal) -and [bool]$evNVDA.ok
$spyReady = $phase23Ok -and $evHardOk -and $phase4Ok -and $gsPolicyOk -and $gsSPY.okLiveToday -and ($gsAsOf -ne "" -and $gsAsOf -eq $todayLocal) -and [bool]$evSPY.ok
$qqqReady = $phase23Ok -and $evHardOk -and $phase4Ok -and $gsPolicyOk -and $gsQQQ.okLiveToday -and ($gsAsOf -ne "" -and $gsAsOf -eq $todayLocal) -and [bool]$evQQQ.ok


# Audit: include per-symbol not-ready flags (even if NVDA is ready)
if (WantSym "NVDA" -and -not $nvdaReady) { $reasons.Add("nvda_blockg_ready=false") | Out-Null }
if (WantSym "SPY" -and -not $spyReady) { $reasons.Add("spy_blockg_ready=false") | Out-Null }
if (WantSym "QQQ" -and -not $qqqReady) { $reasons.Add("qqq_blockg_ready=false") | Out-Null }
# MARKET_CLOSED_FORCE_SYMBOL_READY_FINAL_BEGIN
# FINAL AUTHORITY: on market-closed days, per-symbol readiness MUST be false in the payload.
if ($marketClosedToday) {
  $nvdaReady = $false
  $spyReady  = $false
  $qqqReady  = $false
}
# MARKET_CLOSED_FORCE_SYMBOL_READY_FINAL_END
# REASONS_SANITIZE_BEGIN
# Contract integrity: reasons_not_ready must never contradict final readiness flags.
try {
  $tmp = New-Object System.Collections.Generic.List[string]
  foreach($r in @($reasons)){
    $s = ($r + "")
    if(-not $s){ continue }

    # Drop false negatives after final recompute
    if($nvdaReady -and $s -eq "nvda_blockg_ready=false"){ continue }
    if($spyReady  -and $s -eq "spy_blockg_ready=false"){  continue }
    if($qqqReady  -and $s -eq "qqq_blockg_ready=false"){  continue }

    $tmp.Add($s) | Out-Null
  }
  $reasons = $tmp
} catch { }
# REASONS_SANITIZE_END
# STRICT_OPTION_B_VETO_BEGIN
# Option B (strict): SPY/QQQ must remain blocked until GateScore metrics source is true paper/live for them.
# This is defense-in-depth; your daily runner also enforces this.
try {
  $ms = ([string]$gatescore_metrics_source).Trim()
  $allow = ($ms -eq "paperlive_real_v1")
  if(-not $allow){
    $spyReady = $false
    $qqqReady = $false
    $reasons.Add("strict_option_b_blocks_spy_qqq=true") | Out-Null
  }
} catch {
  $spyReady = $false
  $qqqReady = $false
  try { $reasons.Add("strict_option_b_blocks_spy_qqq=true") | Out-Null } catch { }
}
# STRICT_OPTION_B_VETO_END
# AUDIT_METRICS_SOURCE_MISSING_BEGIN
# POLICYA_USONLY_SPYQQQ_BEGIN
# Policy A: Only US market audits SPY/QQQ metrics_source; non-US treats them non-applicable.
if((($Market + "")).Trim().ToUpperInvariant() -eq "US"){
# Audit-only: add explicit reasons when per-symbol metrics_source is missing (does not change gating)
try {
  $msSpy = ((Get-MetricsSourceTop "SPY" $logsDir $todayLocal).top + "")
  if((-not $msSpy) -or ($msSpy -eq "(missing)")){
    $reasons.Add("metrics_source_missing_for_symbol=SPY") | Out-Null
  }
} catch {
  try { $reasons.Add("metrics_source_missing_for_symbol=SPY") | Out-Null } catch { }
}

try {
  $msQqq = ((Get-MetricsSourceTop "QQQ" $logsDir $todayLocal).top + "")
  if((-not $msQqq) -or ($msQqq -eq "(missing)")){
    $reasons.Add("metrics_source_missing_for_symbol=QQQ") | Out-Null
  }
} catch {
  try { $reasons.Add("metrics_source_missing_for_symbol=QQQ") | Out-Null } catch { }
}
# AUDIT_METRICS_SOURCE_MISSING_END
}
# POLICYA_USONLY_SPYQQQ_END

# --- EMIT GUARANTEE (institutional) ---
$script:__emit_reached = $true
# --- END EMIT GUARANTEE ---

# --- CANONICALIZE OUTPUT PATHS (institutional; MUST be outside payload hashtable) ---
try { $statusPath = Canon $statusPath } catch { }
try { $intel_source_path = Canon $intel_source_path } catch { }
try { $gsMsPath = Canon $gsMsPath } catch { }

# Explicit resolved events path (NVDA) for payload key
$gatescore_events_path = ""
try { $gatescore_events_path = (Resolve-GatescoreEventsPath "NVDA" $logsDir) } catch { $gatescore_events_path = "" }
try { if($gatescore_events_path){ $gatescore_events_path = Canon $gatescore_events_path } } catch { }
# --- END CANONICALIZE OUTPUT PATHS ---
# REGIME_READER_BEGIN
# Regime fields (producer: regime_status.json). Per-market log root.
$regime = "NORMAL"
$regimeOkToday = $false
$regimeReason = "missing_regime_status_json"
$regimePath = Join-Path $logsDirOut "regime_status.json"
try {
  if(Test-Path -LiteralPath $regimePath){
    $rj = Get-Content -LiteralPath $regimePath -Raw -Encoding UTF8 | ConvertFrom-Json
    if($rj){
      if($rj.PSObject.Properties.Name -contains "regime"){ $regime = [string]$rj.regime }
      if($rj.PSObject.Properties.Name -contains "regime_ok_today"){ $regimeOkToday = [bool]$rj.regime_ok_today }
      if($rj.PSObject.Properties.Name -contains "regime_reason"){ $regimeReason = [string]$rj.regime_reason }
    }
  }
} catch {
  $regimeOkToday = $false
  $regimeReason = "regime_status_parse_failed"
}
$crisisAlphaEnabled = $false
# REGIME_READER_END
# CRASHMODE_FLATTEN_READER_BEGIN
# CrashMode flatten evidence (producer: logs/<Market>/crashmode_flatten_status.json).
# StrictMode-safe, fail-closed defaults; reader overrides if JSON exists and parses.
function Read-CrashModeFlattenEvidence([string]$LogsDirOut){
  $res = [ordered]@{
    ok = $false
    exit_code = 0
    path = (Join-Path $LogsDirOut "crashmode_flatten_status.json")
  }
  try{
    if(Test-Path -LiteralPath $res.path){
      $j = Get-Content -LiteralPath $res.path -Raw -Encoding UTF8 | ConvertFrom-Json
      if($j){
        if($j.PSObject.Properties.Name -contains "ok"){ $res.ok = [bool]$j.ok }
        if($j.PSObject.Properties.Name -contains "exit_code"){
          try { $res.exit_code = [int]$j.exit_code } catch { $res.exit_code = 2 }
        }
      }
    }
  } catch {
    $res.ok = $false
    $res.exit_code = 2
  }
  return $res
}

$cm = Read-CrashModeFlattenEvidence $logsDirOut
$crashFlattenOk   = [bool]$cm.ok
$crashFlattenExit = [int]$cm.exit_code
$crashFlattenPath = [string]$cm.path
# CRASHMODE_FLATTEN_READER_END
# EVH_STUB_SESSION_ASOF_CLAMP_V1_PRE_BEGIN
# Policy B: compute EV-hard session/as_of diagnostic outside hash literal (PS5-safe).
$evSessionAsOfPinned = $evSessionAsOf
if($marketClosedToday){
  $evSessionAsOfPinned = $todayLocal
  try {
    $pEv = Join-Path $logsDir "ev_hard_status.json"
    if(Test-Path -LiteralPath $pEv){
      $jEv = Get-Content -LiteralPath $pEv -Raw -Encoding UTF8 | ConvertFrom-Json
      $namesEv = @($jEv.PSObject.Properties.Name)
      # Closed day: keep pinned todayLocal (do NOT overwrite with evidence_as_of_date/as_of_date)
      $null = $namesEv  # no-op: preserve parse without changing pinned value
    }
  } catch { }
}
# EVH_STUB_SESSION_ASOF_CLAMP_V1_PRE_END
# INTEL_GS_POLICYB_CLAMP_V1_PRE_BEGIN
# Policy B: on market-closed days, clamp intel/gatescore as_of diagnostics to pinned todayLocal (DENY unchanged).
$intel_as_of_date_pinned = $intel_as_of_date
$gatescore_as_of_date_pinned = $gsAsOf
if($marketClosedToday){
  if($todayLocal){
    $intel_as_of_date_pinned = $todayLocal
    $gatescore_as_of_date_pinned = $todayLocal
  }
}
# INTEL_GS_POLICYB_CLAMP_V1_PRE_END
# POLICYB_AGE_CLAMP_V1_BEGIN
# Policy B: market-closed days are NOT evaluated (DENY unchanged). Clamp age diagnostics only.
if($marketClosedToday){
  $intel_age_minutes = 0
  $gsAgeDays = 0
}
# POLICYB_AGE_CLAMP_V1_END

# POLICYB_GSFLAGS_DIAG_SHARED_V1_BEGIN
# Policy B: GSFLAGS diagnostics for FULL payload (NO gating changes).
$gsRecentEnough_diag = $false
$gsFreshForSession_diag = $false
try {
  $ge = $null
  if(Get-Variable -Name 'gsRecentEnough' -Scope Local -ErrorAction SilentlyContinue){ $ge = $gsRecentEnough }
  $d = Resolve-GSFlagsDiag -MarketClosedToday:$marketClosedToday -GsRecentEnough $ge
  $gsRecentEnough_diag = [bool]$d.recent_enough
  $gsFreshForSession_diag = [bool]$d.fresh_for_session
} catch { $gsRecentEnough_diag = $false; $gsFreshForSession_diag = $false }
# POLICYB_GSFLAGS_DIAG_SHARED_V1_END

# GREADY_MAP_OKTODAY_V1_APPLY_BEGIN
# Map Global-Ready file schemas into contract booleans (accept ok_today fallback).
try { if(Get-Variable -Name 'jdna' -Scope Local -ErrorAction SilentlyContinue){ $gdnaOk = _PickOkToday $jdna 'market_dna_ok_today' } } catch { }
try { if(Get-Variable -Name 'jedge' -Scope Local -ErrorAction SilentlyContinue){ $gedgeOk = _PickOkToday $jedge 'edge_validity_ok_today' } } catch { }
try { if(Get-Variable -Name 'jdep' -Scope Local -ErrorAction SilentlyContinue){ $gdepOk = _PickOkToday $jdep 'dependency_risk_ok_today' } } catch { }
try { if(Get-Variable -Name 'jrisk' -Scope Local -ErrorAction SilentlyContinue){ $griskOk = _PickOkToday $jrisk 'risk_guard_ok_today' } } catch { }
try { $globalReadyOk = ([bool]$gdnaOk -and [bool]$gedgeOk -and [bool]$gdepOk -and [bool]$griskOk) } catch { $globalReadyOk = $false }
# GREADY_MAP_OKTODAY_V1_APPLY_END

  # [FIX] precompute rounded values OUTSIDE hashtable (parser-safe)
  $gatescore_mean_edge_ratio_rounded6 = 0.0
  try {
    $gatescore_mean_edge_ratio_rounded6 = [math]::Round([double]$gatescore_mean_edge_ratio, 6)
  } catch {
    $gatescore_mean_edge_ratio_rounded6 = 0.0
  }
  # CONTRACT_SEMANTICS_FULL_LIVE_ELIGIBLE_BEGIN
  try {
    $liveEligible = $false
    if(-not [bool]$marketClosedToday){
      $liveEligible = $true
      # Session gate (ALL_STRICT open day expects RTH)
      try { if((([string]$rcSessionName).Trim().ToUpperInvariant()) -ne "RTH"){ $liveEligible = $false } } catch { $liveEligible = $false }
      # Core daily receipts
      if(-not [bool]$phase4Ok){ $liveEligible = $false }
      if(-not [bool]$phase23Ok){ $liveEligible = $false }
      if(-not [bool]$evHardOk){  $liveEligible = $false }
      # Global-Ready receipts
      if(-not [bool]$globalReadyOk){ $liveEligible = $false }
      if(-not [bool]$regimeOkToday){ $liveEligible = $false }
      # GateScore receipts (use computed vars when present)
      try { if(-not [bool]$gsFreshToday){ $liveEligible = $false } } catch { $liveEligible = $false }
      try { if(Get-Variable -Name "gsRecentEnough" -Scope Local -ErrorAction SilentlyContinue){ if(-not [bool]$gsRecentEnough){ $liveEligible = $false } } } catch { $liveEligible = $false }
      try { if(Get-Variable -Name "gsNVDA" -Scope Local -ErrorAction SilentlyContinue){ if($gsNVDA -and ($gsNVDA.PSObject.Properties.Name -contains "okLiveToday")){ if(-not [bool]$gsNVDA.okLiveToday){ $liveEligible = $false } } } } catch { $liveEligible = $false }
    }
    if($liveEligible){ $contract_semantics_level = "FULL_LIVE_ELIGIBLE" }
  } catch { }
  # CONTRACT_SEMANTICS_FULL_LIVE_ELIGIBLE_END
  # CONTRACT_SEMANTICS_REASON_BEGIN
  $contract_semantics_reason = ""
  try {
    if([bool]$marketClosedToday){ $contract_semantics_reason = "closed_day" }
    else {
      if((([string]$rcSessionName).Trim().ToUpperInvariant()) -ne "RTH"){ if((($contract_semantics_level + "") -eq "PAPERLIVE_STRICT")){ $contract_semantics_reason = "paperlive_after_hours" } else { $contract_semantics_reason = "session_not_rth" } }
      elseif(-not [bool]$phase4Ok){ $contract_semantics_reason = "phase4_ok_today=false" }
      elseif(-not [bool]$phase23Ok){ $contract_semantics_reason = "phase23_health_ok_today=false" }
      elseif(-not [bool]$evHardOk){ $contract_semantics_reason = "ev_hard_daily_ok_today=false" }
      elseif(-not [bool]$globalReadyOk){ $contract_semantics_reason = "global_ready_ok_today=false" }
      elseif(-not [bool]$regimeOkToday){ $contract_semantics_reason = "regime_ok_today=false" }
      elseif(-not [bool]$gsFreshToday){ $contract_semantics_reason = "gatescore_fresh_today=false" }
      else {
        try { if(Get-Variable -Name "gsRecentEnough" -Scope Local -ErrorAction SilentlyContinue){ if(-not [bool]$gsRecentEnough){ $contract_semantics_reason = "gatescore_recent_enough=false" } } } catch { }
        try { if(Get-Variable -Name "gsNVDA" -Scope Local -ErrorAction SilentlyContinue){ if($gsNVDA -and ($gsNVDA.PSObject.Properties.Name -contains "okLiveToday")){ if(-not [bool]$gsNVDA.okLiveToday){ $contract_semantics_reason = "gatescore_ok_live_today=false" } } } } catch { }
      }
    }
  } catch { }
  try { if((-not [bool]$marketClosedToday) -and (($contract_semantics_level + "") -ne "FULL_LIVE_ELIGIBLE")){ Write-Host ("[SEM] full_live_eligible=false reason=" + $contract_semantics_reason) -ForegroundColor DarkGray } } catch { }
  # CONTRACT_SEMANTICS_REASON_END
  # EVH_FINALMILE_DEFINE_FULL_BEGIN
  # StrictMode safety: define evHardOk_final for FULL payload path.
  $evHardOk_final = $evHardOk
  # If per-market ev_hard_status.json exists for todayLocal, prefer it (A2 coherence).
  try {
    $pEv = Join-Path $logsDir "ev_hard_status.json"
    if(Test-Path -LiteralPath $pEv){
      $jEv = $null
      try { $jEv = (Get-Content -LiteralPath $pEv -Raw -Encoding UTF8 | ConvertFrom-Json -ErrorAction Stop) } catch { $jEv = $null }
      if($jEv -and ($jEv.PSObject.Properties.Name -contains "as_of_date")){
        $dEv = [string]$jEv.as_of_date; if($dEv.Length -ge 10){ $dEv = $dEv.Substring(0,10) }
        if($dEv -eq $todayLocal){
          if($jEv.PSObject.Properties.Name -contains "ok_today"){ $evHardOk_final = [bool]$jEv.ok_today }
          if($jEv.PSObject.Properties.Name -contains "not_evaluated_market_closed"){ $ev_hard_not_evaluated_market_closed = [bool]$jEv.not_evaluated_market_closed }
        }
      }
    }
  } catch { }
  # EVH_FINALMILE_DEFINE_FULL_END

# REGIME_ACTIONS_AUDIT_V1_BEGIN
# Audit-only: read regime_actions.json (producer: tools/Build-RegimeActions.ps1)
# MUST be defined BEFORE payload hashtable so variables are in scope.
$regimeActionsPath = Join-Path $logsDir "regime_actions.json"
$ra_ok_today = $false
$ra_deny_new_trades = $false
$ra_size_multiplier = 1.0
$ra_cooldown_minutes = 0
$ra_stop_multiplier = 1.0
$ra_target_multiplier = 1.0
$ra_reason = ""

try {
  if(Test-Path -LiteralPath $regimeActionsPath){
    $raj = Get-Content -LiteralPath $regimeActionsPath -Raw -Encoding UTF8 | ConvertFrom-Json -ErrorAction Stop
    if($raj){
      if($raj.PSObject.Properties.Name -contains "ok_today"){ $ra_ok_today = [bool]$raj.ok_today }
      if($raj.PSObject.Properties.Name -contains "deny_new_trades"){ $ra_deny_new_trades = [bool]$raj.deny_new_trades }
      if($raj.PSObject.Properties.Name -contains "size_multiplier"){ $ra_size_multiplier = [double]$raj.size_multiplier }
      if($raj.PSObject.Properties.Name -contains "cooldown_minutes"){ $ra_cooldown_minutes = [int]$raj.cooldown_minutes }
      if($raj.PSObject.Properties.Name -contains "stop_multiplier"){ $ra_stop_multiplier = [double]$raj.stop_multiplier }
      if($raj.PSObject.Properties.Name -contains "target_multiplier"){ $ra_target_multiplier = [double]$raj.target_multiplier }
      if($raj.PSObject.Properties.Name -contains "regime_reason"){ $ra_reason = [string]$raj.regime_reason }
      if((-not $ra_reason) -and ($raj.PSObject.Properties.Name -contains "reasons")){
        try { $ra_reason = (@($raj.reasons) -join ",") } catch { }
      }
    }
  } else {
    $ra_reason = "missing_regime_actions_json"
  }
} catch {
  $ra_reason = "regime_actions_parse_error"
}
# REGIME_ACTIONS_AUDIT_V1_END
$payload = [ordered]@{
    ts_utc = $tsUtc
    as_of_date = $todayLocal
    contract_semantics_level = $contract_semantics_level
    builder_path = "FULL"
    contract_semantics_reason = $contract_semantics_reason
    gatescore_metrics_source = $gatescore_metrics_source

    # Audit: per-symbol metrics_source (do NOT use for gating in strict Option-B)
    gatescore_metrics_source_by_symbol = [ordered]@{
      NVDA = (Get-MetricsSourceTop "NVDA" $logsDir $todayLocal).top
      SPY  = (Get-MetricsSourceTop "SPY"  $logsDir $todayLocal).top
      QQQ  = (Get-MetricsSourceTop "QQQ"  $logsDir $todayLocal).top
    }
    gatescore_metrics_source_debug_seen_count = $gsMsSeenCount
    gatescore_metrics_source_debug_top        = $gsMsTop
    gatescore_metrics_source_debug_today      = $gsMsToday

    gatescore_metrics_source_debug_path       = $gsMsPath
    gatescore_metrics_source_debug_exists     = $gsMsExists

    # Explicit paths (schema-stable; prevents path-as-key pollution)
    status_path           = $statusPath
    gatescore_events_path = $gatescore_events_path


    market_closed_today = $marketClosedToday
    market_is_open_now  = [bool]$marketIsOpenNow
    is_trading_day   = [bool]$rcIsTradingDay
    session_name     = [string]$rcSessionName
    ev_hard_not_evaluated_market_closed = $ev_hard_not_evaluated_market_closed
    gatescore_nvda_eligible_zero = $gsNvdaEligibleZero
    date = $todayLocal
    phase23_health_ok_today = $phase23Ok
     phase23_not_evaluated_market_closed = [bool]$phase23_not_evaluated_market_closed
    ev_hard_daily_ok_today  = $evHardOk_final
    ev_hard_daily_as_of_date = $evHardDailyAsOf
    # EVH_STUB_SESSION_ASOF_CLAMP_V1_BEGIN
    # Policy B: on CLOSED days, session/as_of diagnostic must use pinned todayLocal (not snapshot as_of).
    ev_hard_session_as_of_date = $evSessionAsOfPinned
    ev_hard_as_of_date         = $evSessionAsOfPinned
    # EVH_STUB_SESSION_ASOF_CLAMP_V1_END
    ev_hard_session_ok = $evSessionOk
    phase4_ok_today         = $phase4Ok
intel_ok_today           = [bool]$intel_ok_today

# C5 Global-Ready fields
market_dna_ok_today      = [bool]$gdnaOk
edge_validity_ok_today   = [bool]$gedgeOk
dependency_risk_ok_today = [bool]$gdepOk
risk_guard_ok_today      = [bool]$griskOk
global_ready_ok_today    = [bool]$globalReadyOk
# Crash-mode contract fields (producer: crisis_regime_status.json)
# Regime Actions (audit-only; producer: regime_actions.json)
regime_actions_ok_today           = [bool]$ra_ok_today
regime_actions_deny_new_trades    = [bool]$ra_deny_new_trades
regime_actions_size_multiplier    = [double]$ra_size_multiplier
regime_actions_cooldown_minutes   = [int]$ra_cooldown_minutes
regime_actions_stop_multiplier    = [double]$ra_stop_multiplier
regime_actions_target_multiplier  = [double]$ra_target_multiplier
regime_actions_reason             = $ra_reason
market_selector_ok_today        = [bool]$ms_ok_today
market_selector_decision        = $ms_decision
market_selector_chosen_market   = $ms_chosen_market
market_selector_chosen_module   = $ms_chosen_module
market_selector_reason          = $ms_reason
regime               = $regime
    regime_ok_today      = [bool]$regimeOkToday
    regime_reason        = $regimeReason
    regime_status_path   = (Canon $regimePath)
    crisis_alpha_enabled = [bool]$crisisAlphaEnabled
    crashmode_flatten_ok        = [bool]$crashFlattenOk
    crashmode_flatten_exit_code = [int]$crashFlattenExit
    crashmode_flatten_status_path = (Canon $crashFlattenPath)
    crisis_ok_today = [bool]$crisisOkToday
    crisis_regime        = [bool]$crisisRegime
    portfolio_halt       = [bool]$crisisPortfolioHalt
    risk_flatten         = [bool]$crisisRiskFlatten
    cooldown_minutes     = [int]$crisisCooldownMinutes
    crisis_status_path   = (Canon $crisisStatusPath)
    intel_as_of_date          = $intel_as_of_date_pinned
    intel_age_minutes         = [int]$intel_age_minutes
    intel_kind                = $intel_kind
    intel_source_path         = $intel_source_path
    nvda_intel_ok_today        = [bool]$nvda_intel_ok_today


    gatescore_fresh_today   = (($gsAsOf -ne "") -and ($gsAsOf -eq $todayLocal))

    gatescore_as_of_date = $gatescore_as_of_date_pinned
    gatescore_age_days = $gsAgeDays
    gatescore_recent_enough = [bool]$gsRecentEnough
    gatescore_recent_enough_diag = $gsRecentEnough_diag
    gatescore_fresh_for_session = $gsFreshForSession_diag
gatescore_samples_ok    = $gsSamplesOk
    gatescore_daily_samples_ok   = $gatescore_daily_samples_ok
    gatescore_rolling_samples_ok = $gatescore_rolling_samples_ok
    min_samples_ok_today   = $gsSamplesOk
    gatescore_threshold_ok_today = $gsThreshOk
    gatescore_ok_today      = ([bool]$gsOkToday -and [bool]$gsRecentEnough -and ($gsAsOf -eq $todayLocal))

    # Per-symbol GateScore detail (audit/Notion-friendly)
    gatescore_by_symbol = [ordered]@{
        NVDA = [ordered]@{
            fresh=$gsNVDA.fresh; samples_ok=$gsNVDA.samplesOk; threshold_ok=$gsNVDA.threshOk; ok_today=$gsNVDA.okToday; samples_ok_live=$gsNVDA.samplesOkLive; threshold_ok_live=$gsNVDA.threshOkLive; ok_live_today=$gsNVDA.okLiveToday;
            count_signals=$gsNVDA.cnt; pnl_samples=$gsNVDA.pnl; mean_edge_ratio=$gsNVDA.edge; mean_micro_score=$gsNVDA.micro;
            min_signals=$gsNVDA.minSignals; min_pnl_samples=$gsNVDA.minPnl; min_edge_ratio=$gsNVDA.minEdge; min_micro_score=$gsNVDA.minMicro
        }
        SPY = [ordered]@{
            fresh=$gsSPY.fresh; samples_ok=$gsSPY.samplesOk; threshold_ok=$gsSPY.threshOk; ok_today=$gsSPY.okLiveToday;
            count_signals=$gsSPY.cnt; pnl_samples=$gsSPY.pnl; mean_edge_ratio=$gsSPY.edge; mean_micro_score=$gsSPY.micro;
            min_signals=$gsSPY.minSignals; min_pnl_samples=$gsSPY.minPnl; min_edge_ratio=$gsSPY.minEdge; min_micro_score=$gsSPY.minMicro
        }
        QQQ = [ordered]@{
            fresh=$gsQQQ.fresh; samples_ok=$gsQQQ.samplesOk; threshold_ok=$gsQQQ.threshOk; ok_today=$gsQQQ.okLiveToday;
            count_signals=$gsQQQ.cnt; pnl_samples=$gsQQQ.pnl; mean_edge_ratio=$gsQQQ.edge; mean_micro_score=$gsQQQ.micro;
            min_signals=$gsQQQ.minSignals; min_pnl_samples=$gsQQQ.minPnl; min_edge_ratio=$gsQQQ.minEdge; min_micro_score=$gsQQQ.minMicro
        }
    }
    gatescore_min_samples_live   = $GS_LIVE_MIN_SIGNALS
    gatescore_min_pnl_samples_live = $GS_LIVE_MIN_PNL_SAMPLES
    gatescore_min_edge_ratio_live   = $GS_LIVE_MIN_EDGE_RATIO
    gatescore_min_micro_score_live  = $GS_LIVE_MIN_MICRO_SCORE
    gatescore_ok_live_today      = ([bool]$gatescore_rolling_samples_ok -and ([math]::Round([double]$gatescore_mean_edge_ratio_rolling,6) -ge [math]::Round([double]$GS_LIVE_MIN_EDGE_RATIO,6)) -and ([math]::Round([double]$gatescore_mean_micro_score_rolling,6) -ge [math]::Round([double]$GS_LIVE_MIN_MICRO_SCORE,6)) -and [bool]$gsRecentEnough -and ($gsAsOf -eq $todayLocal) -and [bool]$evNVDA.ok)

    gatescore_events_min_required = $GS_MIN_EVENTS_REQUIRED
    gatescore_events_by_symbol = [ordered]@{
        NVDA = $evNVDA
        SPY  = $evSPY
        QQQ  = $evQQQ
    }
    gatescore_samples       = $gsCount
    gatescore_min_samples   = $minSignals
    gatescore_pnl_samples   = $gsPnl
    gatescore_samples_rolling          = $gatescore_samples_rolling
    gatescore_pnl_samples_rolling      = $gatescore_pnl_samples_rolling
    gatescore_mean_edge_ratio_rolling  = $gatescore_mean_edge_ratio_rolling
    gatescore_mean_micro_score_rolling = $gatescore_mean_micro_score_rolling
    gatescore_mean_edge_ratio_rolling_rounded6  = [math]::Round([double]$gatescore_mean_edge_ratio_rolling,6)
    gatescore_mean_micro_score_rolling_rounded6 = [math]::Round([double]$gatescore_mean_micro_score_rolling,6)
    gatescore_min_edge_ratio_live_rounded6      = [math]::Round([double]$GS_LIVE_MIN_EDGE_RATIO,6)
    gatescore_min_micro_score_live_rounded6     = [math]::Round([double]$GS_LIVE_MIN_MICRO_SCORE,6)
    gatescore_min_pnl_samples = $minPnl

    gatescore_mean_edge_ratio  = $gsEdge
    # A3_GS_EDGE_ROUNDING_BEGIN
    gatescore_mean_edge_ratio_rounded6 = $gatescore_mean_edge_ratio_rounded6
# --- END PATCH1 ---

    nvda_blockg_ready = [bool]$nvdaReady
    spy_blockg_ready  = [bool]$spyReady
    qqq_blockg_ready  = [bool]$qqqReady
  }
$payloadJson = $payload | ConvertTo-Json -Depth 6
Write-Host ("[BLOCK-G] Writing Block-G status stub: " + (Split-Path -Leaf $statusPath)) -ForegroundColor Cyan
# Phase-5 transition: keep legacy stub path ONLY for US (prevents cross-market contamination)
try {
  $m = (($Market + "")).Trim().ToUpperInvariant()
  if($m -eq "US"){
    $legacy = Join-Path $repoRoot "logs\blockg_status_stub.json"
    if($statusPath -and (Test-Path -LiteralPath $statusPath)){
      Copy-Item -LiteralPath $statusPath -Destination $legacy -Force
    }
  }
} catch { }
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

# --- FAIL-CLOSED EMIT GUARD: if payload block was skipped, write minimal stub then exit 2 ---
if(-not (Get-Variable -Name "__emit_reached" -Scope Script -ErrorAction SilentlyContinue)){
  try {
    $tsUtc = (Get-Date).ToUniversalTime().ToString("o")
$rcA3 = Get-RunContextOrFail $repoRoot $Market $Symbol
$todayLocal = _SliceDate ([string]$rcA3.as_of_date)
if(-not $repoRoot){ $repoRoot = Resolve-RepoRoot }
    if(-not $logsDir){ $logsDir = Join-Path $repoRoot "logs" }
    if(-not (Test-Path -LiteralPath $logsDir)){ New-Item -ItemType Directory -Force -Path $logsDir | Out-Null }
    if(-not $statusPath){ $statusPath = Join-Path $logsDirOut "blockg_status_stub.json" }
    $min = [ordered]@{ ts_utc=$tsUtc; as_of_date=$todayLocal; ok=$false; reason="builder_skipped_emit_block_failclosed"; reasons_not_ready=@("builder_skipped_emit_block") ; contract_semantics_level=$contract_semantics_level }
    $enc = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($statusPath, ($min | ConvertTo-Json -Depth 6), $enc)
  } catch { }
throw "[BLOCKG] DEBUG: exit 2 hit"
}
# --- END FAIL-CLOSED EMIT GUARD ---

[System.IO.File]::WriteAllText($statusPath, $payloadJson, $utf8NoBom)

Write-Host "[BLOCK-G] Status snapshot:" -ForegroundColor Yellow
$payload.GetEnumerator() | Format-Table -AutoSize

exit 0









} catch {
  try {
    $toolsDir = Split-Path -Parent $PSCommandPath
    $p = Join-Path $toolsDir "blockg_builder_crash.txt"
    $msg = $_.Exception.ToString()
    [System.IO.File]::WriteAllText($p, $msg, (New-Object System.Text.UTF8Encoding($false)))
  } catch { }
  throw
}
