[CmdletBinding()]
param(
    [ValidateSet("NVDA","SPY","QQQ","ALL")]
    [string]$Symbol = "ALL"
)

Set-StrictMode -Version Latest
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

$today = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd")
# ---- GateScore session date (weekend-safe): derive from pnl summary ----
$tsUtc = (Get-Date).ToUniversalTime().ToString("o")
$statusPath = Join-Path $logsDir "blockg_status_stub.json"

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
$pnlPath = Join-Path $logsDir "gatescore_pnl_summary.csv"
$gsAsOf = ""
if (Test-Path $pnlPath) {
  try {
    $pnlRows = @(Import-Csv $pnlPath)
    $dates = @($pnlRows | ForEach-Object { Slice-Date ([string]$_.as_of_date) } | Where-Object { $_ })
    if ($dates.Count -gt 0) { $gsAsOf = ($dates | Sort-Object | Select-Object -Last 1) }
  } catch { $gsAsOf = "" }
}
if (-not $gsAsOf) { $gsAsOf = $today }
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
$gsPath = $pnlPath  # source-of-truth: gatescore_pnl_summary.csv
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
$nvdaReady = $phase23Ok -and $evHardOk -and $phase4Ok -and $gsNVDA.okToday -and $gsRecentEnough
$spyReady  = $phase23Ok -and $evHardOk -and $phase4Ok -and $gsSPY.okToday
$qqqReady  = $phase23Ok -and $evHardOk -and $phase4Ok -and $gsQQQ.okToday
$reasons = New-Object System.Collections.Generic.List[string]

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
if (-not $gsFresh)   { $reasons.Add("gatescore_fresh_today=false") }
if (-not $gsSamplesOk) { $reasons.Add("gatescore_samples_not_ok") }
if (-not $gsThreshOk)  { $reasons.Add("gatescore_below_threshold") }

# Recompute per-symbol readiness AFTER GateScore age policy (StrictMode-safe)
$nvdaReady = $phase23Ok -and $evHardOk -and $phase4Ok -and $gsNVDA.okToday -and $gsRecentEnough
$spyReady  = $phase23Ok -and $evHardOk -and $phase4Ok -and $gsSPY.okToday -and $gsRecentEnough
$qqqReady  = $phase23Ok -and $evHardOk -and $phase4Ok -and $gsQQQ.okToday -and $gsRecentEnough

$payload = [ordered]@{
    ts_utc = $tsUtc
    as_of_date = $today

    phase23_health_ok_today = $phase23Ok
    ev_hard_daily_ok_today  = $evHardOk
    ev_hard_as_of_date = $evSessionAsOf
    ev_hard_session_ok = $evSessionOk
    phase4_ok_today         = $phase4Ok

    gatescore_fresh_today   = (($gsAsOf -eq $today) -and $gsFresh)

    gatescore_as_of_date = $gsAsOf
    gatescore_age_days = $gsAgeDays
    gatescore_recent_enough = $gsRecentEnough
    gatescore_fresh_for_session = $gsFresh
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

$payloadJson = $payload | ConvertTo-Json -Depth 6
Write-Host "[BLOCK-G] Writing Block-G status stub to $statusPath" -ForegroundColor Cyan

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($statusPath, $payloadJson, $utf8NoBom)

Write-Host "[BLOCK-G] Status snapshot:" -ForegroundColor Yellow
$payload.GetEnumerator() | Format-Table -AutoSize

exit 0
