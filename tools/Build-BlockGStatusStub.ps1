[CmdletBinding()]
param(
    [ValidateSet("NVDA","SPY","QQQ","ALL")]
    [string]$Symbol = "ALL"
)

function WantSym([string]$sym){
  $s = $Symbol.ToUpperInvariant()
  return ($s -eq "ALL" -or $s -eq $sym.ToUpperInvariant())
}


Set-StrictMode -Version Latest
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
  $path = Join-Path $logsDir ("{0}_gatescore_events_real.jsonl" -f $sym.ToLower())
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
    if($null -ne $e.realized_pnl){ $pnlCount += 1 }
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
if (-not (Test-Path $logsDir)) { New-Item -ItemType Directory -Path $logsDir -Force | Out-Null }

# Session date (single source of truth): prefer Phase4 stamp as_of_date; fallback to local date
$today = (Get-Date).ToString("yyyy-MM-dd")
$p4Path = Join-Path $logsDir "phase4_validation_passed.json"
if (Test-Path -LiteralPath $p4Path) {
  try {
    $p4 = (Get-Content -LiteralPath $p4Path -Raw -Encoding utf8 | ConvertFrom-Json)
    $d = [string]$p4.as_of_date
    if ($d -and $d.Length -ge 10) { $today = $d.Substring(0,10) }
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
if (Test-Path $evPath) {
    $rows = @(Import-Csv $evPath)
    foreach ($r in $rows) {
        if ((Slice-Date ([string]$r.date)) -eq $today) {
            if ($r.PSObject.Properties.Name -contains "ok") { $evHardOk = To-Bool $r.ok } else { $evHardOk = $true }
        }
    }
}


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
    $fresh=$false; $cnt=0; $pnl=0; $edge=0.0; $micro=0.0
    foreach ($r in $gsRows) {
        if (($r.symbol + "").ToUpperInvariant() -ne $sym.ToUpperInvariant()) { continue }
        if ((Slice-Date ([string]$r.as_of_date)) -ne $gsAsOf) { continue }
        $fresh = $true
        [void][int]::TryParse([string]$r.count_signals, [ref]$cnt)
        if ($cnt -le 0) { $fresh = $false }
        [void][int]::TryParse([string]$r.pnl_samples, [ref]$pnl)
        [void][double]::TryParse([string]$r.mean_edge_ratio, [ref]$edge)
        [void][double]::TryParse([string]$r.mean_micro_score, [ref]$micro)
    }
    return [pscustomobject]@{ fresh=$fresh; cnt=$cnt; pnl=$pnl; edge=$edge; micro=$micro }
}

function Eval-GS([string]$sym) {
    $thr = Get-ThresholdsFor $sym
    $gs  = Get-GSFor $sym
    $samplesOk = ($gs.cnt -ge $thr.minSignals -and $gs.pnl -ge $thr.minPnl)
    $threshOk  = (($gs.edge + 1e-9) -ge $thr.minEdge -and ($gs.micro + 1e-9) -ge $thr.minMicro)
    $okToday   = ($gs.fresh -and $samplesOk -and $threshOk)
    return [pscustomobject]@{
        fresh=$gs.fresh; samplesOk=$samplesOk; threshOk=$threshOk; okToday=$okToday;
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
# --- Policy metrics should prefer rolling when available ---
$gsCountPolicy = if($null -ne $gatescore_samples_rolling -and [int]$gatescore_samples_rolling -gt 0){ [int]$gatescore_samples_rolling } else { [int]$gsCountPolicy }
$gsPnlPolicy   = if($null -ne $gatescore_pnl_samples_rolling -and [int]$gatescore_pnl_samples_rolling -gt 0){ [int]$gatescore_pnl_samples_rolling } else { [int]$gsPnlPolicy }
$gsEdgePolicy  = if($null -ne $gatescore_mean_edge_ratio_rolling){ [double]$gatescore_mean_edge_ratio_rolling } else { [double]$gsEdgePolicy }
$gsMicroPolicy = if($null -ne $gatescore_mean_micro_score_rolling){ [double]$gatescore_mean_micro_score_rolling } else { [double]$gsMicroPolicy }
# --- end policy metrics ---

# --- FIXED policy metrics + booleans (rolling-first) ---
$gsCountPolicy = if([int]$gatescore_samples_rolling -gt 0){ [int]$gatescore_samples_rolling } else { [int]$gsCount }
$gsPnlPolicy   = if([int]$gatescore_pnl_samples_rolling -gt 0){ [int]$gatescore_pnl_samples_rolling } else { [int]$gsPnl }
$gsEdgePolicy  = [double]$gatescore_mean_edge_ratio_rolling
$gsMicroPolicy = [double]$gatescore_mean_micro_score_rolling

$gsSamplesOk = ($gsCountPolicy -ge [int]$minSignals -and $gsPnlPolicy -ge [int]$minPnl)
$gsThreshOk  = (($gsEdgePolicy + 1e-9) -ge [double]$minEdge -and ($gsMicroPolicy + 1e-9) -ge [double]$minMicro)
$gsOkToday   = ([bool]$gsFresh -and $gsSamplesOk -and $gsThreshOk)
# NOTE: gsPolicyOk depends on gsRecentEnough, computed later (age policy); we will recompute it after age check.
# --- END FIXED policy metrics + booleans ---


# ---- Legacy GateScore vars (NVDA-based) for backward-compatible payload/reasons ----
$gsFresh     = [bool]$gsNVDA.fresh
$gsSamplesOk = [bool]$gsNVDA.samplesOk
$gsThreshOk  = [bool]$gsNVDA.threshOk
$gsOkToday   = [bool]$gsNVDA.okToday

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
$nvdaReady = $phase23Ok -and $evHardOk -and $phase4Ok -and $gsPolicyOk -and $gsNVDA.okToday -and ($gsAsOf -ne "" -and $gsAsOf -eq $today) -and [bool]$evNVDA.ok
$spyReady = $phase23Ok -and $evHardOk -and $phase4Ok -and $gsPolicyOk -and $gsSPY.okToday -and ($gsAsOf -ne "" -and $gsAsOf -eq $today) -and [bool]$evSPY.ok
$qqqReady = $phase23Ok -and $evHardOk -and $phase4Ok -and $gsPolicyOk -and $gsQQQ.okToday -and ($gsAsOf -ne "" -and $gsAsOf -eq $today) -and [bool]$evQQQ.ok
$reasons = New-Object System.Collections.Generic.List[string]
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
if (-not $phase4Ok)  { $reasons.Add("phase4_ok_today=false") }
if (-not $gsAsOf -or $gsAsOf -ne $today) { $reasons.Add("gatescore_fresh_today=false") }
if (-not $gsSamplesOk) { $reasons.Add("gatescore_samples_not_ok") }
if (-not $gsThreshOk)  { $reasons.Add("gatescore_below_threshold") }

# Recompute per-symbol readiness AFTER GateScore age policy (StrictMode-safe)
$nvdaReady = $phase23Ok -and $evHardOk -and $phase4Ok -and $gsPolicyOk -and $gsNVDA.okToday -and ($gsAsOf -ne "" -and $gsAsOf -eq $today) -and [bool]$evNVDA.ok
$spyReady = $phase23Ok -and $evHardOk -and $phase4Ok -and $gsPolicyOk -and $gsSPY.okToday -and ($gsAsOf -ne "" -and $gsAsOf -eq $today) -and [bool]$evSPY.ok
$qqqReady = $phase23Ok -and $evHardOk -and $phase4Ok -and $gsPolicyOk -and $gsQQQ.okToday -and ($gsAsOf -ne "" -and $gsAsOf -eq $today) -and [bool]$evQQQ.ok


# Audit: include per-symbol not-ready flags (even if NVDA is ready)
if (WantSym "NVDA" -and -not $nvdaReady) { $reasons.Add("nvda_blockg_ready=false") | Out-Null }
if (WantSym "SPY" -and -not $spyReady) { $reasons.Add("spy_blockg_ready=false") | Out-Null }
if (WantSym "QQQ" -and -not $qqqReady) { $reasons.Add("qqq_blockg_ready=false") | Out-Null }
$payload = [ordered]@{
    ts_utc = $tsUtc
    as_of_date = $today

    phase23_health_ok_today = $phase23Ok
    ev_hard_daily_ok_today  = $evHardOk
    ev_hard_as_of_date = $evSessionAsOf
    ev_hard_session_ok = $evSessionOk
    phase4_ok_today         = $phase4Ok

    gatescore_fresh_today   = (($gsAsOf -ne "") -and ($gsAsOf -eq $today))

    gatescore_as_of_date = $gsAsOf
    gatescore_age_days = $gsAgeDays
    gatescore_recent_enough = $gsRecentEnough
    gatescore_fresh_for_session = [bool]$gsRecentEnough
gatescore_samples_ok    = $gsSamplesOk
    min_samples_ok_today   = $gsSamplesOk
    gatescore_threshold_ok_today = $gsThreshOk
    gatescore_ok_today      = $gsOkToday

    # Per-symbol GateScore detail (audit/Notion-friendly)
    gatescore_by_symbol = [ordered]@{
        NVDA = [ordered]@{
            fresh=$gsNVDA.fresh; samples_ok=$gsNVDA.samplesOk; threshold_ok=$gsNVDA.threshOk; ok_today=$gsNVDA.okToday;
            count_signals=$gsNVDA.cnt; pnl_samples=$gsNVDA.pnl; mean_edge_ratio=$gsNVDA.edge; mean_micro_score=$gsNVDA.micro;
            min_signals=$gsNVDA.minSignals; min_pnl_samples=$gsNVDA.minPnl; min_edge_ratio=$gsNVDA.minEdge; min_micro_score=$gsNVDA.minMicro
        }
        SPY = [ordered]@{
            fresh=$gsSPY.fresh; samples_ok=$gsSPY.samplesOk; threshold_ok=$gsSPY.threshOk; ok_today=$gsSPY.okToday;
            count_signals=$gsSPY.cnt; pnl_samples=$gsSPY.pnl; mean_edge_ratio=$gsSPY.edge; mean_micro_score=$gsSPY.micro;
            min_signals=$gsSPY.minSignals; min_pnl_samples=$gsSPY.minPnl; min_edge_ratio=$gsSPY.minEdge; min_micro_score=$gsSPY.minMicro
        }
        QQQ = [ordered]@{
            fresh=$gsQQQ.fresh; samples_ok=$gsQQQ.samplesOk; threshold_ok=$gsQQQ.threshOk; ok_today=$gsQQQ.okToday;
            count_signals=$gsQQQ.cnt; pnl_samples=$gsQQQ.pnl; mean_edge_ratio=$gsQQQ.edge; mean_micro_score=$gsQQQ.micro;
            min_signals=$gsQQQ.minSignals; min_pnl_samples=$gsQQQ.minPnl; min_edge_ratio=$gsQQQ.minEdge; min_micro_score=$gsQQQ.minMicro
        }
    }
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

$payloadJson = $payload | ConvertTo-Json -Depth 6
Write-Host "[BLOCK-G] Writing Block-G status stub to $statusPath" -ForegroundColor Cyan

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($statusPath, $payloadJson, $utf8NoBom)

Write-Host "[BLOCK-G] Status snapshot:" -ForegroundColor Yellow
$payload.GetEnumerator() | Format-Table -AutoSize

exit 0



