[CmdletBinding()]
param(
    [ValidateSet("NVDA","SPY","QQQ","ALL")]
    [string]$Symbol = "ALL"
)

function WantSym([string]$sym){
  $s = $Symbol.ToUpperInvariant()
  return ($s -eq "ALL" -or $s -eq $sym.ToUpperInvariant())
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
Set-StrictMode -Version Latest


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
  $evs = @(Read-JsonlLines $path)
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
  return ($dow -ne 0 -and $dow -ne 6) # Mon-Fri
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
function Get-GSFromEvents([string]$sym, [string]$asOf, [string]$todayLocal){
  # Compute GateScore metrics for a single as_of_date from resolved events source.
  $repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
  $logsDir  = Join-Path $repoRoot "logs"

  $path = Resolve-GatescoreEventsPath $sym $logsDir
  $evs = @(Read-JsonlLines $path)
  if($evs.Count -eq 0){
    return [pscustomobject]@{ fresh=$false; cnt=0; pnl=0; edge=0.0; micro=0.0 }
  }

  $sel=@()
  foreach($e in $evs){
    $d = SliceDate ([string]$e.as_of_date)
    if($d -eq $asOf){
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

function Get-Phase4OkToday([string]$RepoRoot, [string]$Today){
  $path = Join-Path $RepoRoot "logs\phase4_validation_passed.json"
  if(-not (Test-Path $path)){ return $false }

  try {
    $raw = Get-Content -LiteralPath $path -Raw -Encoding utf8
    $j = $raw | ConvertFrom-Json
    $asOf = [string]$j.as_of_date
    $ok = [bool]$j.phase4_ok_today
    return (($asOf.Substring(0,10)) -eq $Today) -and $ok
  } catch {
    return $false
  }
}

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
$logsDir  = Join-Path $repoRoot "logs"
# GS_METRICS_SOURCE_CAPTURE_BEGIN
$gatescore_metrics_source = ""
$gsMsSeenCount = 0
$gsMsTop = ""
$gsMsPath = ""
$gsMsToday = ""
$gsMsExists = $false

try {
  $todayLocal = (Get-Date).ToString("yyyy-MM-dd")
# GS_ASOF_FORCE_FROM_EVENTS_BEGIN
# FINAL AUTHORITY: gsAsOf must follow the resolved NVDA events file (array OR jsonl).
try {
  $selNvda = Resolve-GsPath "NVDA" $todayLocal
  $mx = Get-MaxAsOfDateFromJsonl $selNvda
  if($mx){ $gsAsOf = $mx }
} catch { }
# GS_ASOF_FORCE_FROM_EVENTS_END
# GS_ASOF_FROM_EVENTS_BEGIN
# GateScore session date must follow the selected NVDA source for TODAY (paper vs replay).
try {
  $sel = Resolve-GsPath "NVDA" $todayLocal
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
# Weekend-aware clarity (no holiday calendar): market_closed_today is true on Sat/Sun.
$marketClosedToday = $false
try {
  $dow = [int](Get-Date).DayOfWeek
  if($dow -eq 0 -or $dow -eq 6){ $marketClosedToday = $true }
} catch { $marketClosedToday = $false }


# EVH_MARKET_CLOSED_AUDIT_BEGIN
# Audit-only clarity: when market is closed we do not treat EV-hard as "passed".
$ev_hard_not_evaluated_market_closed = $false
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
# MARKET_HOLIDAY_CAL_BEGIN
# Extend market_closed_today with optional holiday calendar (configs\market_holidays.json).
try {
  $holPath = Join-Path $repoRoot "configs\market_holidays.json"
  if(Test-Path -LiteralPath $holPath){
    $hj = Get-Content -LiteralPath $holPath -Raw -Encoding utf8 | ConvertFrom-Json
    $closed = @()
    if($hj.PSObject.Properties.Name -contains "closed_dates"){ $closed = @($hj.closed_dates) }
    if($closed -contains $today){ $marketClosedToday = $true }
  }
} catch { }
# MARKET_HOLIDAY_CAL_END
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
$today = (Get-Date).ToString("yyyy-MM-dd")
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
$statusPath = Join-Path $logsDir "blockg_status_stub.json"


# ---- GateScore EVENTS freshness (fail-closed) ----
$GS_MIN_EVENTS_REQUIRED = 25

function Get-GSEventsMeta([string]$RepoRoot, [string]$Sym, [string]$Today){
  $p = Join-Path $RepoRoot ("logs\{0}_gatescore_events.jsonl" -f $Sym.ToLower())
  $rows = 0; $fresh = $false; $ts = ""
  if(Test-Path -LiteralPath $p){
    try { $rows = @(Get-Content -LiteralPath $p -Encoding utf8).Count } catch { $rows = 0 }
    try {
      $it = Get-Item -LiteralPath $p
      $ts = $it.LastWriteTime.ToString("yyyy-MM-dd")
      $fresh = ($ts -eq $Today)
    } catch { $fresh = $false; $ts = "" }
  }
  $ok = ($fresh -and $rows -ge $GS_MIN_EVENTS_REQUIRED)
  return [pscustomobject]@{ path=$p; rows=$rows; fresh=$fresh; ts=$ts; ok=$ok }
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
$pnlPath = Join-Path $logsDir "gatescore_pnl_summary.csv"
if (-not (Test-Path -LiteralPath $pnlPath)) {
  # backward-compatible fallback (older name)
  $pnlPath = Join-Path $logsDir "gatescore_daily_summary.csv"
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
# ---- Phase4 ----
$phase4Ok = Get-Phase4OkToday $repoRoot $today

# ---- EV hard veto daily ----
$evHardOk = $false
$evPath = Join-Path $logsDir "phase5_ev_hard_veto_daily.csv"
$evHardDailyAsOf = ""
$evHardOk = $false
if (Test-Path $evPath) {
    $rows = @(Import-Csv $evPath)
    if ($rows -and $rows.Count -gt 0) {
        # As-of date is last row date (audit). Today-ness enforced separately.
        $last = $rows[-1]
        $evHardDailyAsOf = Slice-Date ([string]$last.date)

        # Find today row (if any) and enforce ok only for today.
        foreach ($r in $rows) {
            if ((Slice-Date ([string]$r.date)) -eq $today) {
                $evHardDailyAsOf = $today
                if ($r.PSObject.Properties.Name -contains "ok") { $evHardOk = To-Bool $r.ok } else { $evHardOk = $true }
                break
            }
        }
    }
}
# EVHARD_REASON_CAPTURE_BEGIN
# Capture today's EV-hard daily reason for audit/contract messaging
$evHardReason = ""
try {
  if (Test-Path $evPath) {
    $rows2 = @(Import-Csv $evPath)
    foreach ($r2 in $rows2) {
      if ((Slice-Date ([string]$r2.date)) -eq $today) {
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
  } catch { $evSessionAsOf=""; $evSessionOk=$false }
}# ---- Phase23 health (must match today row; fail-closed) ----

# If daily EV-hard veto CSV is missing, fall back to session raw evidence (fail-closed, today-checked downstream)
if((-not (Test-Path -LiteralPath $evPath)) -and $evSessionOk){
  $evHardOk = $true
  $evSessionAsOf = ($evSessionAsOf + "")
}

$phase23Ok = $false
$phase23Path = Join-Path $logsDir "phase23_health_daily.csv"
$phase23SawToday = $false

if (Test-Path $phase23Path) {
    $rows = @(Import-Csv $phase23Path)
    foreach ($r in $rows) {
        $d = ""
        if ($r.PSObject.Properties.Name -contains "as_of_date") { $d = Slice-Date ([string]$r.as_of_date) }
        elseif ($r.PSObject.Properties.Name -contains "date") { $d = Slice-Date ([string]$r.date) }

        if ($d -ne $today) { continue }

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

function Get-GSFor([string]$sym) {
    # Use the selected events source as truth (paper vs replay) for the computed gsAsOf.
    $gs0 = Get-GSFromEvents $sym $gsAsOf $todayLocal
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
$gsDays = LastNTradingDays $today $ROLL_DAYS
$gsNVDA_roll = ComputeGateScoreRolling "NVDA" $logsDir $gsDays

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
$nvdaReady = $phase23Ok -and $evHardOk -and $phase4Ok -and $gsPolicyOk -and $gsNVDA.okLiveToday -and ($gsAsOf -ne "" -and $gsAsOf -eq $today) -and [bool]$evNVDA.ok
$spyReady = $phase23Ok -and $evHardOk -and $phase4Ok -and $gsPolicyOk -and $gsSPY.okLiveToday -and ($gsAsOf -ne "" -and $gsAsOf -eq $today) -and [bool]$evSPY.ok
$qqqReady = $phase23Ok -and $evHardOk -and $phase4Ok -and $gsPolicyOk -and $gsQQQ.okLiveToday -and ($gsAsOf -ne "" -and $gsAsOf -eq $today) -and [bool]$evQQQ.ok
$reasons = New-Object System.Collections.Generic.List[string]
if ($gsMetricsSourceDisallowedForLive) {
  $reasons.Add(("gatescore_metrics_source_disallowed_for_live=" + $gatescore_metrics_source)) | Out-Null
}
if ($marketClosedToday) { $reasons.Add("ev_hard_market_closed_today=true") | Out-Null }
if ($gatescore_metrics_source) { $reasons.Add(("gatescore_metrics_source=" + $gatescore_metrics_source)) | Out-Null }
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
    $d1 = [datetime]::ParseExact(($today + ""), "yyyy-MM-dd", $null)
    $gsAgeDays = [int]([math]::Floor(($d1 - $d0).TotalDays))
  }
} catch { $gsAgeDays = 9999 }

$gsRecentEnough = ($gsAgeDays -le $MAX_GS_AGE_DAYS)
$gsPolicyOk = [bool]($gsRecentEnough -and $gsSamplesOk -and $gsThreshOk)
if (-not $gsRecentEnough) {
  $reasons.Add(("gatescore_too_old age_days=" + $gsAgeDays + " max=" + $MAX_GS_AGE_DAYS + " session=" + $gsAsOf + " today=" + $today)) | Out-Null
}
# QQQ_GS_OK_TODAY omitted for NVDA-only readiness
if (-not $phase23Ok) { $reasons.Add("phase23_health_ok_today=false") }
if (-not $evHardOk)  { $reasons.Add("ev_hard_daily_ok_today=false") }
if (-not $evHardOk -and $evHardReason) { $reasons.Add(("ev_hard_daily_reason=" + $evHardReason)) }
if (-not $evHardOk -and $evHardSnapshotReason) { $reasons.Add(("ev_hard_snapshot_reason=" + $evHardSnapshotReason)) }
if (-not $phase4Ok)  { $reasons.Add("phase4_ok_today=false") }
if (-not $gsAsOf -or $gsAsOf -ne $today) { $reasons.Add("gatescore_fresh_today=false") }
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
$nvdaReady = $phase23Ok -and $evHardOk -and $phase4Ok -and $gsPolicyOk -and $gsNVDA.okLiveToday -and ($gsAsOf -ne "" -and $gsAsOf -eq $today) -and [bool]$evNVDA.ok
$spyReady = $phase23Ok -and $evHardOk -and $phase4Ok -and $gsPolicyOk -and $gsSPY.okLiveToday -and ($gsAsOf -ne "" -and $gsAsOf -eq $today) -and [bool]$evSPY.ok
$qqqReady = $phase23Ok -and $evHardOk -and $phase4Ok -and $gsPolicyOk -and $gsQQQ.okLiveToday -and ($gsAsOf -ne "" -and $gsAsOf -eq $today) -and [bool]$evQQQ.ok


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
$payload = [ordered]@{
    ts_utc = $tsUtc
    as_of_date = $today
    gatescore_metrics_source = $gatescore_metrics_source
    gatescore_metrics_source_debug_seen_count = $gsMsSeenCount
    gatescore_metrics_source_debug_top        = $gsMsTop
    gatescore_metrics_source_debug_today      = $gsMsToday
    gatescore_metrics_source_debug_path       = $gsMsPath
    gatescore_metrics_source_debug_exists     = $gsMsExists
    market_closed_today = $marketClosedToday
    ev_hard_not_evaluated_market_closed = $ev_hard_not_evaluated_market_closed
    gatescore_nvda_eligible_zero = $gsNvdaEligibleZero
    date = $today
    phase23_health_ok_today = $phase23Ok
    ev_hard_daily_ok_today  = $evHardOk
    ev_hard_daily_as_of_date = $evHardDailyAsOf
    ev_hard_session_as_of_date = $evSessionAsOf
    ev_hard_as_of_date = $evSessionAsOf
    ev_hard_session_ok = $evSessionOk
    phase4_ok_today         = $phase4Ok

    gatescore_fresh_today   = (($gsAsOf -ne "") -and ($gsAsOf -eq $today))

    gatescore_as_of_date = $gsAsOf
    gatescore_age_days = $gsAgeDays
    gatescore_recent_enough = $gsRecentEnough
    gatescore_fresh_for_session = [bool]$gsRecentEnough
gatescore_samples_ok    = $gsSamplesOk
    gatescore_daily_samples_ok   = $gatescore_daily_samples_ok
    gatescore_rolling_samples_ok = $gatescore_rolling_samples_ok
    min_samples_ok_today   = $gsSamplesOk
    gatescore_threshold_ok_today = $gsThreshOk
    gatescore_ok_today      = $gsOkToday

    # Per-symbol GateScore detail (audit/Notion-friendly)
    gatescore_by_symbol = [ordered]@{
        NVDA = [ordered]@{
            fresh=$gsNVDA.fresh; samples_ok=$gsNVDA.samplesOk; threshold_ok=$gsNVDA.threshOk; ok_today=$gsNVDA.okLiveToday;
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
    gatescore_ok_live_today      = ([bool]$gsNVDA.okLiveToday)

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
    gatescore_mean_micro_score = $gsMicro
    gatescore_min_edge_ratio   = $minEdge
    gatescore_min_micro_score  = $minMicro

    nvda_blockg_ready = $nvdaReady
    spy_blockg_ready  = $spyReady
    qqq_blockg_ready  = $qqqReady

    reasons_not_ready = @($reasons)
}
# --- PATCH1: micro diagnostics persisted into payload (guaranteed) ---
try {
  $evPath = ($payload["gatescore_metrics_source_debug_path"] + "")
  $ev = Get-GSEventsObjects $evPath
  if($ev -and $ev.Count -gt 0){
    $microSrcKey   = Find-FirstMatchingKey $ev[0] '(?i)micro.*(source|src)'
    $microScoreKey = Find-FirstMatchingKey $ev[0] '(?i)^micro_score$|(?i)micro.*score'

    $payload["micro_source_field_detected"] = ($microSrcKey + "")
    $payload["micro_score_field_detected"]  = ($microScoreKey + "")

    $top=@{}
    if($microSrcKey){
      foreach($e in $ev){
        $v=""
        try { $v = ($e.$microSrcKey + "") } catch { $v="" }
        if(-not $v){ $v="(missing)" }
        if(-not $top.ContainsKey($v)){ $top[$v]=0 }
        $top[$v]++
      }
    }

    if($top.Count -gt 0){
      $payload["micro_score_source_top"] = @(
        $top.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 5 |
          ForEach-Object { "{0}:{1}" -f $_.Name,$_.Value }
      )
      $derived = @($top.Keys | Where-Object { $_ -match '^(?i)derived_' })
      $payload["micro_score_source_disallowed_for_live_detected"] = [bool]($derived.Count -gt 0)
    } else {
      $payload["micro_score_source_top"] = @()
      $payload["micro_score_source_disallowed_for_live_detected"] = $true
    }
  } else {
    $payload["micro_source_field_detected"] = ""
    $payload["micro_score_field_detected"]  = ""
    $payload["micro_score_source_top"] = @()
    $payload["micro_score_source_disallowed_for_live_detected"] = $true
  }
} catch {
  $payload["micro_source_field_detected"] = ""
  $payload["micro_score_field_detected"]  = ""
  $payload["micro_score_source_top"] = @()
  $payload["micro_score_source_disallowed_for_live_detected"] = $true
}
# --- END PATCH1 ---

$payloadJson = $payload | ConvertTo-Json -Depth 6
Write-Host "[BLOCK-G] Writing Block-G status stub to $statusPath" -ForegroundColor Cyan

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($statusPath, $payloadJson, $utf8NoBom)

Write-Host "[BLOCK-G] Status snapshot:" -ForegroundColor Yellow
$payload.GetEnumerator() | Format-Table -AutoSize

exit 0
