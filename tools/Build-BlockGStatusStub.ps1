# BLOCKG_AUTHORITY_VERSION = 1
# Authority: summary flags ONLY (phase23, ev_hard, phase4, gatescore)
# Do NOT trust per-symbol GateScore internals here

[CmdletBinding()]
param(
    [ValidateSet("NVDA","SPY","QQQ","ALL")]
    [string]$Symbol = "ALL"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# --- Dedup: only build BlockG once per process ---
# Policy: we may SKIP rebuild only if the stub already exists AND parses as JSON.
# If stub is missing/invalid, force rebuild (fail-closed; pytest-safe).

if ($env:HAT_BLOCKG_BUILT_ONCE -eq "1") {
  # stdout marker for pytest subprocess capture (host output is not reliable)
  $toolsDir = $null; $repoRoot = $null; $logsDir = $null; $statusPath = $null
  try {
    $toolsDir = Split-Path -Parent $PSCommandPath
    $repoRoot = Split-Path -Parent $toolsDir
    $logsDir  = Join-Path $repoRoot "logs"
    $statusPath = Join-Path $logsDir "blockg_status_stub.json"
    Write-Output ("blockg_status_stub.json -> " + $statusPath)
  } catch { }

  $reuseOk = $false
  try {
    if($statusPath -and (Test-Path -LiteralPath $statusPath)){
      $raw = Get-Content -LiteralPath $statusPath -Raw -Encoding utf8
      $null = ($raw | ConvertFrom-Json)  # parse check
      $reuseOk = $true
    }
  } catch { $reuseOk = $false }

  if($reuseOk){
    if ($env:HAT_BLOCKG_QUIET -ne "1") {
      Write-Host "[BLOCK-G] Skipping rebuild (HAT_BLOCKG_BUILT_ONCE=1; stub exists+valid)" -ForegroundColor DarkGray
    }
    exit 0
  }

  # Stub missing/invalid -> force rebuild in this process
  if ($env:HAT_BLOCKG_QUIET -ne "1") {
    Write-Host "[BLOCK-G] Dedup set but stub missing/invalid; forcing rebuild" -ForegroundColor Yellow
  }
  Remove-Item Env:HAT_BLOCKG_BUILT_ONCE -ErrorAction SilentlyContinue
}

$env:HAT_BLOCKG_BUILT_ONCE = "1"
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

# --- Effective as_of_date policy (weekend carry-forward) ---
$TODAY_CAL = (Get-Date).ToString("yyyy-MM-dd")
$dow = (Get-Date).DayOfWeek
$isWeekend = ($dow -eq "Saturday" -or $dow -eq "Sunday")
$dates = New-Object System.Collections.Generic.List[string]
try {
  $gs = Join-Path $logsDir "gatescore_daily_summary.csv"
  if(Test-Path -LiteralPath $gs){
    $d = (Import-Csv $gs | ForEach-Object { $_.as_of_date } | Sort-Object | Select-Object -Last 1)
    if($d){ $dates.Add(($d+"").Trim()) }
  }
} catch {}
try {
  $p4 = Join-Path $logsDir "phase4_validation_passed.json"
  if(Test-Path -LiteralPath $p4){
    $j = (Get-Content -LiteralPath $p4 -Raw -Encoding utf8 | ConvertFrom-Json)
    $d = (($j.as_of_date + "").Trim())
    if($d){ $dates.Add($d) }
  }
} catch {}

$EFFECTIVE_ASOF = $TODAY_CAL
if($isWeekend -and $dates.Count -gt 0){
  $EFFECTIVE_ASOF = ($dates | Sort-Object | Select-Object -Last 1)
}
if(-not $EFFECTIVE_ASOF){ $EFFECTIVE_ASOF = $TODAY_CAL }

# IMPORTANT: unify variable names used later in this script
$today = $EFFECTIVE_ASOF
$asOfDate = $today
# --- end effective as_of_date policy ---



if (-not (Test-Path $logsDir)) { New-Item -ItemType Directory -Path $logsDir -Force | Out-Null }

$today = $EFFECTIVE_ASOF  # LOCAL trading day (weekend carry-forward)
$asOfDate = $today
# ---- GateScore session date (weekend-safe): derive from pnl summary ----
$tsUtc = (Get-Date).ToUniversalTime().ToString("o")
$statusPath = Join-Path $logsDir "blockg_status_stub.json"

# --- TEST TOKEN: always print output filename for harness ---
Write-Output ("blockg_status_stub.json -> " + $statusPath)
# -----------------------------------------------------------


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
$pnlPath = Join-Path $logsDir "gatescore_daily_summary.csv"
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
$phase4Path = Join-Path $logsDir "phase4_validation_passed.json"
if (Test-Path $phase4Path) {
    try {
        $j = Get-Content $phase4Path -Raw -Encoding UTF8 | ConvertFrom-Json
    $phase4Ok = Get-Phase4OkToday $repoRoot $today
    } catch { $phase4Ok = $false }
}

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
$gsPath = $pnlPath  # source-of-truth: gatescore_daily_summary.csv
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

# ---- Per-symbol ready (institutional) ----
# NOTE: GateScore global fields remain NVDA-based for compatibility; readiness is per-symbol.
$nvdaReady = $phase23Ok -and $evHardOk -and $phase4Ok -and $gsNVDA.okToday -and ($gsAsOf -ne "" -and $gsAsOf -eq $today)
$spyReady  = $phase23Ok -and $evHardOk -and $phase4Ok -and $gsSPY.okToday  -and ($gsAsOf -ne "" -and $gsAsOf -eq $today)
$qqqReady  = $phase23Ok -and $evHardOk -and $phase4Ok -and $gsQQQ.okToday  -and ($gsAsOf -ne "" -and $gsAsOf -eq $today)
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
$nvdaReady = $phase23Ok -and $evHardOk -and $phase4Ok -and $gsNVDA.okToday -and ($gsAsOf -ne "" -and $gsAsOf -eq $today)
$spyReady  = $phase23Ok -and $evHardOk -and $phase4Ok -and $gsSPY.okToday  -and ($gsAsOf -ne "" -and $gsAsOf -eq $today)
$qqqReady  = $phase23Ok -and $evHardOk -and $phase4Ok -and $gsQQQ.okToday  -and ($gsAsOf -ne "" -and $gsAsOf -eq $today)


# Audit: include per-symbol not-ready flags (even if NVDA is ready)
# --- Target symbols (default NVDA-only). Set HAT_BLOCKG_SYMBOLS="NVDA,SPY,QQQ" to include others ---
$wantNvda = $true
$wantSpy  = $false
$wantQqq  = $false
$symEnv = [System.Environment]::GetEnvironmentVariable("HAT_BLOCKG_SYMBOLS","Process")
if([string]::IsNullOrWhiteSpace($symEnv)){ $symEnv = [System.Environment]::GetEnvironmentVariable("HAT_BLOCKG_SYMBOLS","User") }
if(-not [string]::IsNullOrWhiteSpace($symEnv)){
  $ss = @($symEnv.Split(",") | ForEach-Object { ($_+"").Trim().ToUpperInvariant() } | Where-Object { $_ })
  $wantNvda = $ss -contains "NVDA"
  $wantSpy  = $ss -contains "SPY"
  $wantQqq  = $ss -contains "QQQ"
}

if ($wantSpy -and -not $spyReady) { $reasons.Add("spy_blockg_ready=false") | Out-Null }
if ($wantQqq -and -not $qqqReady) { $reasons.Add("qqq_blockg_ready=false") | Out-Null }

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

    gatescore_samples       = $gsCount
    gatescore_min_samples   = $minSignals
    gatescore_pnl_samples   = $gsPnl
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


# --- LLM advisory gate (tighten-only; never loosens) ---
$llmTool = Join-Path $repoRoot "tools\Get-LLMAdvisoryGate.ps1"
$llm = $null
try {
  if(Test-Path $llmTool){ $llm = & powershell -NoProfile -ExecutionPolicy Bypass -File $llmTool -Symbol "ALL" | ConvertFrom-Json }
} catch { $llm = $null }

if($null -ne $llm){
  $payload["llm_action"] = ($llm.action + "")
  $payload["llm_ok_today"] = [bool]$llm.ok
  if(-not [bool]$llm.ok){
    $rn = @()
    if($payload.Contains("reasons_not_ready") -and $null -ne $payload["reasons_not_ready"]){ $rn = @($payload["reasons_not_ready"]) }
    if($null -ne $llm.reasons){ $rn += @($llm.reasons) }
    $payload["reasons_not_ready"] = $rn
  }
} else {
  $payload["llm_action"] = "none"
  $payload["llm_ok_today"] = $true
}


# --- GateScore midnight-boundary fix (outside hash literal) ---
try {
  if(($status.gatescore_as_of_date) -and ($status.as_of_date)){
    $gs = [datetime]::ParseExact(($status.gatescore_as_of_date+""), "yyyy-MM-dd", $null)
    $as = [datetime]::ParseExact(($status.as_of_date+""), "yyyy-MM-dd", $null)
    $delta = [int]($gs.Date - $as.Date).TotalDays
    if($delta -eq 1 -and ($status.gatescore_fresh_today -eq $false) -and ($status.gatescore_ok_today -eq $true)){
      $status.gatescore_as_of_date = $status.as_of_date
      $status.gatescore_age_days = 0
      $status.gatescore_fresh_today = $true
      $status.reasons_not_ready = @($status.reasons_not_ready | Where-Object { $_ -ne "gatescore_fresh_today=false" })
if ($env:HAT_BLOCKG_QUIET -ne "1") {
      Write-Host "[BLOCK-G] GateScore midnight fix applied (utc+1 -> local)" -ForegroundColor Yellow
}
      # Recompute readiness using local-day gatescore_as_of_date (midnight fix changes it)
      $gsAsOfLocal = ($payload.gatescore_as_of_date + "")
      $nvdaReady = $phase23Ok -and $evHardOk -and $phase4Ok -and $gsNVDA.okToday -and ($gsAsOfLocal -ne "" -and $gsAsOfLocal -eq $today)
      $spyReady  = $phase23Ok -and $evHardOk -and $phase4Ok -and $gsSPY.okToday  -and ($gsAsOfLocal -ne "" -and $gsAsOfLocal -eq $today)
      $qqqReady  = $phase23Ok -and $evHardOk -and $phase4Ok -and $gsQQQ.okToday  -and ($gsAsOfLocal -ne "" -and $gsAsOfLocal -eq $today)
$payload.nvda_blockg_ready =
  [bool]$payload.phase23_health_ok_today -and
  [bool]$payload.ev_hard_daily_ok_today  -and
  [bool]$payload.phase4_ok_today         -and
  [bool]$payload.gatescore_fresh_today   -and
  [bool]$payload.gatescore_recent_enough -and
  [bool]$payload.gatescore_samples_ok    -and
  [bool]$payload.gatescore_threshold_ok_today -and
  [bool]$payload.gatescore_ok_today      -and
  ([bool]$payload.gatescore_by_symbol.NVDA.ok_today)
      $payload.spy_blockg_ready  = [bool]$spyReady
      $payload.qqq_blockg_ready  = [bool]$qqqReady
      # Remove stale reason if present
      if($payload.reasons_not_ready){ $payload.reasons_not_ready = @($payload.reasons_not_ready | Where-Object { $_ -ne "gatescore_fresh_today=false" }) }
    }
  }
} catch { }


# --- GateScore midnight-boundary fix (payload; utc+1 -> local) ---
try {
  if(($payload.gatescore_as_of_date) -and ($payload.as_of_date)){
    $gs = [datetime]::ParseExact(($payload.gatescore_as_of_date+""), "yyyy-MM-dd", $null)
    $as = [datetime]::ParseExact(($payload.as_of_date+""), "yyyy-MM-dd", $null)
    $delta = [int]($gs.Date - $as.Date).TotalDays
    if($delta -eq 1 -and ($payload.gatescore_fresh_today -eq $false) -and ($payload.gatescore_ok_today -eq $true)){
      $payload.gatescore_as_of_date = $payload.as_of_date
      $payload.gatescore_age_days = 0
      $payload.gatescore_fresh_today = $true
if ($env:HAT_BLOCKG_QUIET -ne "1") {
      Write-Host "[BLOCK-G] GateScore midnight fix applied (utc+1 -> local)" -ForegroundColor Yellow
}
    }
  }
} catch { }


# ================= FINAL BLOCK-G READINESS AUTHORITY =================
# Single source of truth. Overrides all earlier derived readiness.

$payload.nvda_blockg_ready =
  [bool]$payload.phase23_health_ok_today -and
  [bool]$payload.ev_hard_daily_ok_today  -and
  [bool]$payload.phase4_ok_today         -and
  [bool]$payload.gatescore_ok_today      -and
  [bool]$payload.gatescore_fresh_today

# SPY / QQQ computed only when explicitly enabled (fail-closed by default)
$enableSpyQqq = ($env:HAT_BLOCKG_ENABLE_SPYQQQ -eq "1")
if($enableSpyQqq){
  $payload.spy_blockg_ready =
    [bool]$payload.phase23_health_ok_today -and
    [bool]$payload.ev_hard_daily_ok_today  -and
    [bool]$payload.phase4_ok_today         -and
    [bool]$payload.gatescore_fresh_today   -and
    [bool]$payload.gatescore_recent_enough -and
    [bool]$payload.gatescore_samples_ok    -and
    [bool]$payload.gatescore_threshold_ok_today -and
    [bool]$payload.gatescore_ok_today      -and
    ([bool]$payload.gatescore_by_symbol.SPY.ok_today)

  $payload.qqq_blockg_ready =
    [bool]$payload.phase23_health_ok_today -and
    [bool]$payload.ev_hard_daily_ok_today  -and
    [bool]$payload.phase4_ok_today         -and
    [bool]$payload.gatescore_fresh_today   -and
    [bool]$payload.gatescore_recent_enough -and
    [bool]$payload.gatescore_samples_ok    -and
    [bool]$payload.gatescore_threshold_ok_today -and
    [bool]$payload.gatescore_ok_today      -and
    ([bool]$payload.gatescore_by_symbol.QQQ.ok_today)
} else {
  $payload.spy_blockg_ready = $false
  $payload.qqq_blockg_ready = $false
}
# --- Institutional NVDA GateScore events integrity (fail-closed) ---
# Contract must NOT arm if NVDA events are missing/empty/insufficient OR degenerate/placeholder.
try {
  $p = Join-Path $repoRoot "logs\nvda_gatescore_events.jsonl"
  $today = (Get-Date).ToString("yyyy-MM-dd")
  $minEvents = 10

  $todayLines = @()
  if(Test-Path -LiteralPath $p){
    $todayLines = @((Get-Content -LiteralPath $p -Encoding utf8) | Where-Object { # BLOCKG_AUTHORITY_VERSION = 1
# Authority: summary flags ONLY (phase23, ev_hard, phase4, gatescore)
# Do NOT trust per-symbol GateScore internals here

[CmdletBinding()]
param(
    [ValidateSet("NVDA","SPY","QQQ","ALL")]
    [string]$Symbol = "ALL"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# --- Dedup: only build BlockG once per process ---
# Policy: we may SKIP rebuild only if the stub already exists AND parses as JSON.
# If stub is missing/invalid, force rebuild (fail-closed; pytest-safe).

if ($env:HAT_BLOCKG_BUILT_ONCE -eq "1") {
  # stdout marker for pytest subprocess capture (host output is not reliable)
  $toolsDir = $null; $repoRoot = $null; $logsDir = $null; $statusPath = $null
  try {
    $toolsDir = Split-Path -Parent $PSCommandPath
    $repoRoot = Split-Path -Parent $toolsDir
    $logsDir  = Join-Path $repoRoot "logs"
    $statusPath = Join-Path $logsDir "blockg_status_stub.json"
    Write-Output ("blockg_status_stub.json -> " + $statusPath)
  } catch { }

  $reuseOk = $false
  try {
    if($statusPath -and (Test-Path -LiteralPath $statusPath)){
      $raw = Get-Content -LiteralPath $statusPath -Raw -Encoding utf8
      $null = ($raw | ConvertFrom-Json)  # parse check
      $reuseOk = $true
    }
  } catch { $reuseOk = $false }

  if($reuseOk){
    if ($env:HAT_BLOCKG_QUIET -ne "1") {
      Write-Host "[BLOCK-G] Skipping rebuild (HAT_BLOCKG_BUILT_ONCE=1; stub exists+valid)" -ForegroundColor DarkGray
    }
    exit 0
  }

  # Stub missing/invalid -> force rebuild in this process
  if ($env:HAT_BLOCKG_QUIET -ne "1") {
    Write-Host "[BLOCK-G] Dedup set but stub missing/invalid; forcing rebuild" -ForegroundColor Yellow
  }
  Remove-Item Env:HAT_BLOCKG_BUILT_ONCE -ErrorAction SilentlyContinue
}

$env:HAT_BLOCKG_BUILT_ONCE = "1"
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

# --- Effective as_of_date policy (weekend carry-forward) ---
$TODAY_CAL = (Get-Date).ToString("yyyy-MM-dd")
$dow = (Get-Date).DayOfWeek
$isWeekend = ($dow -eq "Saturday" -or $dow -eq "Sunday")
$dates = New-Object System.Collections.Generic.List[string]
try {
  $gs = Join-Path $logsDir "gatescore_daily_summary.csv"
  if(Test-Path -LiteralPath $gs){
    $d = (Import-Csv $gs | ForEach-Object { $_.as_of_date } | Sort-Object | Select-Object -Last 1)
    if($d){ $dates.Add(($d+"").Trim()) }
  }
} catch {}
try {
  $p4 = Join-Path $logsDir "phase4_validation_passed.json"
  if(Test-Path -LiteralPath $p4){
    $j = (Get-Content -LiteralPath $p4 -Raw -Encoding utf8 | ConvertFrom-Json)
    $d = (($j.as_of_date + "").Trim())
    if($d){ $dates.Add($d) }
  }
} catch {}

$EFFECTIVE_ASOF = $TODAY_CAL
if($isWeekend -and $dates.Count -gt 0){
  $EFFECTIVE_ASOF = ($dates | Sort-Object | Select-Object -Last 1)
}
if(-not $EFFECTIVE_ASOF){ $EFFECTIVE_ASOF = $TODAY_CAL }

# IMPORTANT: unify variable names used later in this script
$today = $EFFECTIVE_ASOF
$asOfDate = $today
# --- end effective as_of_date policy ---



if (-not (Test-Path $logsDir)) { New-Item -ItemType Directory -Path $logsDir -Force | Out-Null }

$today = $EFFECTIVE_ASOF  # LOCAL trading day (weekend carry-forward)
$asOfDate = $today
# ---- GateScore session date (weekend-safe): derive from pnl summary ----
$tsUtc = (Get-Date).ToUniversalTime().ToString("o")
$statusPath = Join-Path $logsDir "blockg_status_stub.json"

# --- TEST TOKEN: always print output filename for harness ---
Write-Output ("blockg_status_stub.json -> " + $statusPath)
# -----------------------------------------------------------


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
$pnlPath = Join-Path $logsDir "gatescore_daily_summary.csv"
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
$phase4Path = Join-Path $logsDir "phase4_validation_passed.json"
if (Test-Path $phase4Path) {
    try {
        $j = Get-Content $phase4Path -Raw -Encoding UTF8 | ConvertFrom-Json
    $phase4Ok = Get-Phase4OkToday $repoRoot $today
    } catch { $phase4Ok = $false }
}

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
$gsPath = $pnlPath  # source-of-truth: gatescore_daily_summary.csv
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

# ---- Per-symbol ready (institutional) ----
# NOTE: GateScore global fields remain NVDA-based for compatibility; readiness is per-symbol.
$nvdaReady = $phase23Ok -and $evHardOk -and $phase4Ok -and $gsNVDA.okToday -and ($gsAsOf -ne "" -and $gsAsOf -eq $today)
$spyReady  = $phase23Ok -and $evHardOk -and $phase4Ok -and $gsSPY.okToday  -and ($gsAsOf -ne "" -and $gsAsOf -eq $today)
$qqqReady  = $phase23Ok -and $evHardOk -and $phase4Ok -and $gsQQQ.okToday  -and ($gsAsOf -ne "" -and $gsAsOf -eq $today)
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
$nvdaReady = $phase23Ok -and $evHardOk -and $phase4Ok -and $gsNVDA.okToday -and ($gsAsOf -ne "" -and $gsAsOf -eq $today)
$spyReady  = $phase23Ok -and $evHardOk -and $phase4Ok -and $gsSPY.okToday  -and ($gsAsOf -ne "" -and $gsAsOf -eq $today)
$qqqReady  = $phase23Ok -and $evHardOk -and $phase4Ok -and $gsQQQ.okToday  -and ($gsAsOf -ne "" -and $gsAsOf -eq $today)


# Audit: include per-symbol not-ready flags (even if NVDA is ready)
# --- Target symbols (default NVDA-only). Set HAT_BLOCKG_SYMBOLS="NVDA,SPY,QQQ" to include others ---
$wantNvda = $true
$wantSpy  = $false
$wantQqq  = $false
$symEnv = [System.Environment]::GetEnvironmentVariable("HAT_BLOCKG_SYMBOLS","Process")
if([string]::IsNullOrWhiteSpace($symEnv)){ $symEnv = [System.Environment]::GetEnvironmentVariable("HAT_BLOCKG_SYMBOLS","User") }
if(-not [string]::IsNullOrWhiteSpace($symEnv)){
  $ss = @($symEnv.Split(",") | ForEach-Object { ($_+"").Trim().ToUpperInvariant() } | Where-Object { $_ })
  $wantNvda = $ss -contains "NVDA"
  $wantSpy  = $ss -contains "SPY"
  $wantQqq  = $ss -contains "QQQ"
}

if ($wantSpy -and -not $spyReady) { $reasons.Add("spy_blockg_ready=false") | Out-Null }
if ($wantQqq -and -not $qqqReady) { $reasons.Add("qqq_blockg_ready=false") | Out-Null }

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

    gatescore_samples       = $gsCount
    gatescore_min_samples   = $minSignals
    gatescore_pnl_samples   = $gsPnl
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


# --- LLM advisory gate (tighten-only; never loosens) ---
$llmTool = Join-Path $repoRoot "tools\Get-LLMAdvisoryGate.ps1"
$llm = $null
try {
  if(Test-Path $llmTool){ $llm = & powershell -NoProfile -ExecutionPolicy Bypass -File $llmTool -Symbol "ALL" | ConvertFrom-Json }
} catch { $llm = $null }

if($null -ne $llm){
  $payload["llm_action"] = ($llm.action + "")
  $payload["llm_ok_today"] = [bool]$llm.ok
  if(-not [bool]$llm.ok){
    $rn = @()
    if($payload.Contains("reasons_not_ready") -and $null -ne $payload["reasons_not_ready"]){ $rn = @($payload["reasons_not_ready"]) }
    if($null -ne $llm.reasons){ $rn += @($llm.reasons) }
    $payload["reasons_not_ready"] = $rn
  }
} else {
  $payload["llm_action"] = "none"
  $payload["llm_ok_today"] = $true
}


# --- GateScore midnight-boundary fix (outside hash literal) ---
try {
  if(($status.gatescore_as_of_date) -and ($status.as_of_date)){
    $gs = [datetime]::ParseExact(($status.gatescore_as_of_date+""), "yyyy-MM-dd", $null)
    $as = [datetime]::ParseExact(($status.as_of_date+""), "yyyy-MM-dd", $null)
    $delta = [int]($gs.Date - $as.Date).TotalDays
    if($delta -eq 1 -and ($status.gatescore_fresh_today -eq $false) -and ($status.gatescore_ok_today -eq $true)){
      $status.gatescore_as_of_date = $status.as_of_date
      $status.gatescore_age_days = 0
      $status.gatescore_fresh_today = $true
      $status.reasons_not_ready = @($status.reasons_not_ready | Where-Object { $_ -ne "gatescore_fresh_today=false" })
if ($env:HAT_BLOCKG_QUIET -ne "1") {
      Write-Host "[BLOCK-G] GateScore midnight fix applied (utc+1 -> local)" -ForegroundColor Yellow
}
      # Recompute readiness using local-day gatescore_as_of_date (midnight fix changes it)
      $gsAsOfLocal = ($payload.gatescore_as_of_date + "")
      $nvdaReady = $phase23Ok -and $evHardOk -and $phase4Ok -and $gsNVDA.okToday -and ($gsAsOfLocal -ne "" -and $gsAsOfLocal -eq $today)
      $spyReady  = $phase23Ok -and $evHardOk -and $phase4Ok -and $gsSPY.okToday  -and ($gsAsOfLocal -ne "" -and $gsAsOfLocal -eq $today)
      $qqqReady  = $phase23Ok -and $evHardOk -and $phase4Ok -and $gsQQQ.okToday  -and ($gsAsOfLocal -ne "" -and $gsAsOfLocal -eq $today)
      $payload.nvda_blockg_ready = [bool]$nvdaReady
      $payload.spy_blockg_ready  = [bool]$spyReady
      $payload.qqq_blockg_ready  = [bool]$qqqReady
      # Remove stale reason if present
      if($payload.reasons_not_ready){ $payload.reasons_not_ready = @($payload.reasons_not_ready | Where-Object { $_ -ne "gatescore_fresh_today=false" }) }
    }
  }
} catch { }


# --- GateScore midnight-boundary fix (payload; utc+1 -> local) ---
try {
  if(($payload.gatescore_as_of_date) -and ($payload.as_of_date)){
    $gs = [datetime]::ParseExact(($payload.gatescore_as_of_date+""), "yyyy-MM-dd", $null)
    $as = [datetime]::ParseExact(($payload.as_of_date+""), "yyyy-MM-dd", $null)
    $delta = [int]($gs.Date - $as.Date).TotalDays
    if($delta -eq 1 -and ($payload.gatescore_fresh_today -eq $false) -and ($payload.gatescore_ok_today -eq $true)){
      $payload.gatescore_as_of_date = $payload.as_of_date
      $payload.gatescore_age_days = 0
      $payload.gatescore_fresh_today = $true
if ($env:HAT_BLOCKG_QUIET -ne "1") {
      Write-Host "[BLOCK-G] GateScore midnight fix applied (utc+1 -> local)" -ForegroundColor Yellow
}
    }
  }
} catch { }


# ================= FINAL BLOCK-G READINESS AUTHORITY =================
# Single source of truth. Overrides all earlier derived readiness.

$payload.nvda_blockg_ready =
  [bool]$payload.phase23_health_ok_today -and
  [bool]$payload.ev_hard_daily_ok_today  -and
  [bool]$payload.phase4_ok_today         -and
  [bool]$payload.gatescore_fresh_today   -and
  [bool]$payload.gatescore_recent_enough -and
  [bool]$payload.gatescore_samples_ok    -and
  [bool]$payload.gatescore_threshold_ok_today -and
  [bool]$payload.gatescore_ok_today      -and
  ([bool]$payload.gatescore_by_symbol.NVDA.ok_today)

# SPY / QQQ computed only when explicitly enabled (fail-closed by default)
$enableSpyQqq = ($env:HAT_BLOCKG_ENABLE_SPYQQQ -eq "1")
if($enableSpyQqq){
  $payload.spy_blockg_ready =
    [bool]$payload.phase23_health_ok_today -and
    [bool]$payload.ev_hard_daily_ok_today  -and
    [bool]$payload.phase4_ok_today         -and
    [bool]$payload.gatescore_fresh_today   -and
    [bool]$payload.gatescore_recent_enough -and
    [bool]$payload.gatescore_samples_ok    -and
    [bool]$payload.gatescore_threshold_ok_today -and
    [bool]$payload.gatescore_ok_today      -and
    ([bool]$payload.gatescore_by_symbol.SPY.ok_today)

  $payload.qqq_blockg_ready =
    [bool]$payload.phase23_health_ok_today -and
    [bool]$payload.ev_hard_daily_ok_today  -and
    [bool]$payload.phase4_ok_today         -and
    [bool]$payload.gatescore_fresh_today   -and
    [bool]$payload.gatescore_recent_enough -and
    [bool]$payload.gatescore_samples_ok    -and
    [bool]$payload.gatescore_threshold_ok_today -and
    [bool]$payload.gatescore_ok_today      -and
    ([bool]$payload.gatescore_by_symbol.QQQ.ok_today)
} else {
  $payload.spy_blockg_ready = $false
  $payload.qqq_blockg_ready = $false
}
# --- Institutional NVDA GateScore events integrity (fail-closed) ---
# If NVDA events are tagged PLACEHOLDER or degenerate_constant_metrics => contract must NOT arm.
try {
  $p = Join-Path $repoRoot "logs\nvda_gatescore_events.jsonl"
  if(Test-Path -LiteralPath $p){
    $today = (Get-Date).ToString("yyyy-MM-dd")
    $deg = $false

    foreach($ln in Get-Content -LiteralPath $p -Encoding utf8){
      if($ln -notmatch $today){ continue }
      if($ln -match 'degenerate_constant_metrics'){ $deg = $true; break }
      if($ln -match '"source"\s*:\s*"PLACEHOLDER"'){ $deg = $true; break }
    }

    if($deg){
      # 1) flip local vars (best-effort; some older code may still read these)
      $gsSamplesOk = $false
      $gsThreshOk  = $false
      $gsOkToday   = $false
      $nvdaReady   = $false

      # 2) MOST IMPORTANT: flip payload fields (canonical contract output)
      if($null -ne $payload){
        $payload["gatescore_samples_ok"] = $false
        $payload["min_samples_ok_today"] = $false
        $payload["gatescore_threshold_ok_today"] = $false
        $payload["gatescore_ok_today"] = $false
        $payload["nvda_blockg_ready"] = $false
      }

      # 3) add reason into payload.reasons_not_ready (tail will preserve & dedupe)
      try {
        if($null -ne $payload){
          $rn0 = @()
          if($payload.Contains("reasons_not_ready") -and $null -ne $payload["reasons_not_ready"]){ $rn0 = @($payload["reasons_not_ready"]) }
          $rn0 += "gatescore_synthetic_degenerate"
          $payload["reasons_not_ready"] = @($rn0)
        }
      } catch { }

      # 4) also keep legacy list updated if present
      if($null -ne $reasons){ $reasons.Add("gatescore_synthetic_degenerate") | Out-Null }
    }
  }
} catch {
  # If evidence check fails, fail-closed (institutional)
  $gsSamplesOk = $false
  $gsThreshOk  = $false
  $gsOkToday   = $false
  $nvdaReady   = $false
  if($null -ne $payload){
    $payload["gatescore_samples_ok"] = $false
    $payload["min_samples_ok_today"] = $false
    $payload["gatescore_threshold_ok_today"] = $false
    $payload["gatescore_ok_today"] = $false
    $payload["nvda_blockg_ready"] = $false
    try {
      $rn0 = @()
      if($payload.Contains("reasons_not_ready") -and $null -ne $payload["reasons_not_ready"]){ $rn0 = @($payload["reasons_not_ready"]) }
      $rn0 += "gatescore_synthetic_degenerate"
      $payload["reasons_not_ready"] = @($rn0)
    } catch { }
  }
  if($null -ne $reasons){ $reasons.Add("gatescore_synthetic_degenerate") | Out-Null }
}



# Rebuild reasons cleanly (no stale state allowed)
$rn = @()

# Preserve earlier reasons_not_ready (do NOT wipe deep reasons)
try {
if($null -ne $payload -and $payload.Contains("reasons_not_ready") -and $null -ne $payload["reasons_not_ready"]){
    foreach($x in @($payload["reasons_not_ready"])){ $rn += ("" + $x) }
  }
} catch { }

# Canonical tail booleans (still add these)
if(-not $payload.phase23_health_ok_today){ $rn += "phase23_health_ok_today=false" }
if(-not $payload.ev_hard_daily_ok_today){ $rn += "ev_hard_daily_ok_today=false" }
if(-not $payload.phase4_ok_today){ $rn += "phase4_ok_today=false" }
if(-not $payload.gatescore_ok_today){ $rn += "gatescore_ok_today=false" }
if(-not $payload.gatescore_fresh_today){ $rn += "gatescore_fresh_today=false" }
if(-not $payload.nvda_blockg_ready){ $rn += "nvda_blockg_ready=false" }

# Dedupe without scriptblocks (StrictMode-safe)
$hs = New-Object System.Collections.Generic.HashSet[string]
$rn2 = New-Object System.Collections.Generic.List[string]
foreach($x in @($rn)){
  $s = ("" + $x).Trim()
  if([string]::IsNullOrWhiteSpace($s)){ continue }
  if($hs.Add($s)){ [void]$rn2.Add($s) }
}
$payload.reasons_not_ready = @($rn2)
# ====================================================================

$payloadJson = $payload | ConvertTo-Json -Depth 6
if ($env:HAT_BLOCKG_QUIET -ne "1") {
Write-Host "[BLOCK-G] Writing Block-G status stub to $statusPath" -ForegroundColor Cyan
}

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($statusPath, $payloadJson, $utf8NoBom)

if ($env:HAT_BLOCKG_QUIET -ne "1") {
Write-Host "[BLOCK-G] Status snapshot:" -ForegroundColor Yellow
$payload.GetEnumerator() | Format-Table -AutoSize
}

exit 0
 -match $today })
  }

  $fail = $false
  $why  = ""

  if(-not (Test-Path -LiteralPath $p)){
    $fail = $true
    $why = "gatescore_events_missing"
  } elseif(-not $todayLines -or $todayLines.Count -lt $minEvents){
    $fail = $true
    $why = ("gatescore_events_insufficient_today<{0}" -f $minEvents)
  } else {
    # Check for synthetic/degenerate evidence
    foreach($ln in $todayLines){
      if($ln -match 'degenerate_constant_metrics'){ $fail = $true; $why="gatescore_synthetic_degenerate"; break }
      if($ln -match '"source"\s*:\s*"PLACEHOLDER"'){ $fail = $true; $why="gatescore_synthetic_degenerate"; break }
    }
  }

  if($fail){
    # flip payload fields (canonical contract output)
    $payload["gatescore_samples_ok"] = $false
    $payload["min_samples_ok_today"] = $false
    $payload["gatescore_threshold_ok_today"] = $false
    $payload["gatescore_ok_today"] = $false
    $payload["gatescore_fresh_today"] = $false
    $payload["nvda_blockg_ready"] = $false

    # add reason (tail will dedupe)
    $rn0 = @()
    if($payload.Contains("reasons_not_ready") -and $null -ne $payload["reasons_not_ready"]){ $rn0 = @($payload["reasons_not_ready"]) }
    $rn0 += $why
    $payload["reasons_not_ready"] = @($rn0)
  }
} catch {
  # Any error in evidence evaluation => fail-closed
  $payload["gatescore_ok_today"] = $false
  $payload["gatescore_fresh_today"] = $false
  $payload["nvda_blockg_ready"] = $false
  $rn0 = @()
  if($payload.Contains("reasons_not_ready") -and $null -ne $payload["reasons_not_ready"]){ $rn0 = @($payload["reasons_not_ready"]) }
  $rn0 += "gatescore_events_check_error"
  $payload["reasons_not_ready"] = @($rn0)
}

# Rebuild reasons cleanly (no stale state allowed)
$rn = @()

# Preserve earlier reasons_not_ready (do NOT wipe deep reasons)
try {
if($null -ne $payload -and $payload.Contains("reasons_not_ready") -and $null -ne $payload["reasons_not_ready"]){
    foreach($x in @($payload["reasons_not_ready"])){ $rn += ("" + $x) }
  }
} catch { }

# Canonical tail booleans (still add these)
if(-not $payload.phase23_health_ok_today){ $rn += "phase23_health_ok_today=false" }
if(-not $payload.ev_hard_daily_ok_today){ $rn += "ev_hard_daily_ok_today=false" }
if(-not $payload.phase4_ok_today){ $rn += "phase4_ok_today=false" }
if(-not $payload.gatescore_ok_today){ $rn += "gatescore_ok_today=false" }
if(-not $payload.gatescore_fresh_today){ $rn += "gatescore_fresh_today=false" }
if(-not $payload.nvda_blockg_ready){ $rn += "nvda_blockg_ready=false" }

# Dedupe without scriptblocks (StrictMode-safe)
$hs = New-Object System.Collections.Generic.HashSet[string]
$rn2 = New-Object System.Collections.Generic.List[string]
foreach($x in @($rn)){
  $s = ("" + $x).Trim()
  if([string]::IsNullOrWhiteSpace($s)){ continue }
  if($hs.Add($s)){ [void]$rn2.Add($s) }
}
$payload.reasons_not_ready = @($rn2)
# ====================================================================

$payloadJson = $payload | ConvertTo-Json -Depth 6
if ($env:HAT_BLOCKG_QUIET -ne "1") {
Write-Host "[BLOCK-G] Writing Block-G status stub to $statusPath" -ForegroundColor Cyan
}

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($statusPath, $payloadJson, $utf8NoBom)

if ($env:HAT_BLOCKG_QUIET -ne "1") {
Write-Host "[BLOCK-G] Status snapshot:" -ForegroundColor Yellow
$payload.GetEnumerator() | Format-Table -AutoSize
}

exit 0
