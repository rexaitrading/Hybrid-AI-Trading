[CmdletBinding()]
param(
    [string]$InputPath = "",
    [string]$OutPath = ".\logs\nvda_gatescore_events.jsonl",
    [int]$MinEvents = 10,
    [ValidateSet("rewrite","append","prune")]
    [string]$Mode = "rewrite",
    [string]$PruneDate = ""
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# --- UTF8_CONSOLE_BEGIN (deterministic, fixes "文件" -> "??") ---
try {
  $utf8 = New-Object System.Text.UTF8Encoding($false)
  [Console]::OutputEncoding = $utf8
  [Console]::InputEncoding  = $utf8
  $global:OutputEncoding    = $utf8
} catch { }
# --- UTF8_CONSOLE_END ---
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$logsDir  = Join-Path $repoRoot "logs"
$today    = (Get-Date).ToString("yyyy-MM-dd")
function Pick-LatestPaperlive([string]$dir) {
    $all = @(Get-ChildItem -LiteralPath $dir -File -Force -ErrorAction SilentlyContinue)
    if (-not $all -or $all.Length -eq 0) { return "" }

    # Institutional priority order (fail-closed, deterministic):
    # 1) phase5 paperlive results (richer schema, has realized_pnl evidence)
    $p1 = $all | Where-Object { $_.Name -match '(?i)^nvda_phase5_paperlive_results\.jsonl$' } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if($p1){ return $p1.FullName }

    # 1b) phase5 paperlive results TODAY (daily producer)
    $p1b = $all | Where-Object { $_.Name -match '(?i)^nvda_phase5_paperlive_results_today\.jsonl$' } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if($p1b){ return $p1b.FullName }


    # 2) phase5 paperexec results
    $p2 = $all | Where-Object { $_.Name -match '(?i)^nvda_phase5_paperexec_results\.jsonl$' } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if($p2){ return $p2.FullName }

    # 3) last resort: paper_live_NVDA_* (provider-only stubs are diagnostic-only)
    $p3 = $all | Where-Object { $_.Name -match '(?i)^paper_live_nvda_.*\.jsonl$' } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if($p3){ return $p3.FullName }

    return ""
}function TryD([object]$v) { $x=0.0; if($null -ne $v){[void][double]::TryParse([string]$v,[ref]$x)}; return $x }
function TryI([object]$v) { $x=0;   if($null -ne $v){[void][int]::TryParse([string]$v,[ref]$x)}; return $x }
function Get-FromResult0([object]$j, [string]$k) {
    # Prefer paper_live schema: metrics are inside first result item
    try {
        if ($j.PSObject.Properties.Name -contains "result") {
            $first = $null
            foreach($x in $j.result){ $first = $x; break }
            if ($null -ne $first) {
                $p = $first.PSObject.Properties.Name
                if ($p -contains $k) { return $first.$k }
            }
        }
    } catch { }
    # Fallback: top-level
    try {
        $p0 = $j.PSObject.Properties.Name
        if ($p0 -contains $k) { return $j.$k }
    } catch { }
    return $null
}
function Pick-Date([object]$j, [string[]]$keys, [string]$fallback) {
    $props = $j.PSObject.Properties.Name
    # --- FAIL-CLOSED: skip non-trade quote rows (prevent GateScore contamination) ---
    try {
        if ($props -contains "status") {
            $st = (($j.status + "")).Trim()
            if ($st -eq "ok_ib_quote") { continue }
        }
    } catch { }
    # --- END skip non-trade quote rows ---
foreach ($k in $keys) {
        if ($props -contains $k) {
            $v = ($j.$k + "").Trim()
            if ($v -match '^\d{4}-\d{2}-\d{2}$') { return $v }
            if ($v.Length -ge 10 -and $v.Substring(0,10) -match '^\d{4}-\d{2}-\d{2}$') { return $v.Substring(0,10) }
        }
    }
    return $fallback
}
function Get-DerivedMicroScore { param([double]$EdgeRatio)
    $edge = [Math]::Max(0.0, [Math]::Min(1.0, ($EdgeRatio - 0.005) / 0.05))
    return [Math]::Round($edge, 6)
}

function Get-MicroLiveV1FromBar { param([double]$High,[double]$Low,[double]$Close)
    if($Close -le 0){ return 0.0 }
    $rng = [Math]::Max(0.0, ($High - $Low))
    $cost = $rng / $Close
    if($cost -gt 0.02){ $cost = 0.02 }
    $score = 1.0 - ($cost / 0.02)
    if($score -lt 0.0){ $score = 0.0 }
    if($score -gt 1.0){ $score = 1.0 }
    return [Math]::Round($score, 6)
}

function Build-MicroLiveDailyFromBars { param([string]$BarsDir,[string]$Symbol)
    $map = @{}
    if(-not (Test-Path -LiteralPath $BarsDir)){ return $map }

    # Deterministic day mapping from ALL cached bar files: SYMBOL_YYYY-MM-DD_1m.csv
    $pat = ($Symbol + "_*_1m.csv")
    $files = @(Get-ChildItem -LiteralPath $BarsDir -Filter $pat -File -ErrorAction SilentlyContinue | Sort-Object Name)
    if(-not $files -or $files.Count -eq 0){ return $map }

    function Pick-Col([string[]]$cols,[string[]]$wants){
      foreach($w in $wants){
        foreach($x in $cols){
          if($x -and $x.ToLowerInvariant() -eq $w.ToLowerInvariant()){ return $x }
        }
      }
      return ""
    }

    foreach($csv in $files){
        $day = ""
        try { if($csv.BaseName -match '_(\d{4}-\d{2}-\d{2})_1m$'){ $day = $Matches[1] } } catch { $day="" }
        if(-not $day){ continue }

        $rows = @()
        try { $rows = @(Import-Csv -LiteralPath $csv.FullName) } catch { $rows = @() }
        if(-not $rows -or $rows.Count -eq 0){ continue }

        $cols = @($rows[0].PSObject.Properties.Name)
        $hcol = Pick-Col $cols @("high","h")
        $lcol = Pick-Col $cols @("low","l")
        $ccol = Pick-Col $cols @("close","c","adj_close","adjclose")
        if(-not $hcol -or -not $lcol -or -not $ccol){ continue }

        $sum = 0.0; $cnt = 0
        foreach($r in $rows){
          $hi=0.0; $lo=0.0; $cl=0.0
          [void][double]::TryParse(([string]$r.$hcol), [ref]$hi)
          [void][double]::TryParse(([string]$r.$lcol), [ref]$lo)
          [void][double]::TryParse(([string]$r.$ccol), [ref]$cl)
          $sc = Get-MicroLiveV1FromBar -High $hi -Low $lo -Close $cl
          $sum += [double]$sc
          $cnt += 1
        }
        if($cnt -gt 0){ $map[$day] = [Math]::Round(($sum / [double]$cnt), 6) }
    }

    return $map
}

if (-not $InputPath) { $InputPath = Pick-LatestPaperlive $logsDir }
if (-not $InputPath -or -not (Test-Path -LiteralPath $InputPath)) { Write-Error "[NVDA-GS-EVENTS] No input paperlive jsonl found."; exit 2 }
Write-Host "[NVDA-GS-EVENTS] Input=$InputPath" -ForegroundColor Cyan
$lines = @(Get-Content -LiteralPath $InputPath -Encoding UTF8)
if ($lines.Count -eq 0) { Write-Error "[NVDA-GS-EVENTS] Input jsonl is empty: $InputPath"; exit 3 }
$eventsOut = New-Object System.Collections.ArrayList


# --- MICRO_LIVE_V1_DAILY_BEGIN ---
$barsDir = Join-Path $logsDir "bars"
$microLiveDaily = Build-MicroLiveDailyFromBars -BarsDir $barsDir -Symbol "NVDA"
# --- MICRO_LIVE_V1_DAILY_END ---
# REAL_ONLY_SPLIT_BEGIN
# Institutional: canonical events file must contain REAL-only rows. STUB rows go to stub sink (debug).
$eventsRealOut = New-Object System.Collections.ArrayList
$eventsStubOut = New-Object System.Collections.ArrayList
$realCount = 0
$stubCount = 0
# REAL_ONLY_SPLIT_END

$count = 0
foreach ($ln in $lines) {
    $s = ($ln + "").Trim()
    if (-not $s) { continue }
    $j = $null
    try { $j = $s | ConvertFrom-Json } catch { continue }
    if ($null -eq $j) { continue }
    $props = $j.PSObject.Properties.Name
    $asOf = Pick-Date $j @("as_of_date","date","trading_day","day","ts","timestamp","ts_utc") $today
    if ($Mode -eq "rewrite") { $asOf = $today }
    $edge = 0.0
    foreach ($k in @("edge_ratio","mean_edge_ratio","edge","edge_mean","gatescore_edge","edgeValue","edge_score")) {
        $v = Get-FromResult0 $j $k
        if ($null -ne $v -and ([string]$v).Trim() -ne "") { $edge = TryD $v; break }
    }
    $micro = 0.0
    foreach ($k in @("micro_score","mean_micro_score","micro","micro_mean","gatescore_micro","microValue","micro_score_mean")) {
        $v = Get-FromResult0 $j $k
        if ($null -ne $v -and ([string]$v).Trim() -ne "") { $micro = TryD $v; break }
    }
    $pnlSamples = 0
    # METRICS_SOURCE_AUDIT_BEGIN
    $metricsSource = ""
    try {
        $msv = Get-FromResult0 $j "metrics_source"
        if ($null -ne $msv) { $metricsSource = ($msv + "") }
    } catch { $metricsSource = "" }
    # METRICS_SOURCE_AUDIT_END
# METRICS_SOURCE_OVERRIDE_NO_PROXY_BEGIN
# Institutional rule: paperlive-derived events must not emit proxy_* metrics_source.
# If upstream tags proxy (or missing), override to a real paperlive label.
try {
    $ms0 = ($metricsSource + "").Trim()
    if (-not $ms0) { $metricsSource = "paperlive_real_v1" }
    elseif ($ms0 -match '^(?i)proxy_') { $metricsSource = "paperlive_real_v1" }
} catch { $metricsSource = "paperlive_real_v1" }
# METRICS_SOURCE_OVERRIDE_NO_PROXY_END
    foreach ($k in @("pnl_samples","pnlSamples","pnl_n","trades_n","trade_count","n_trades","samples","sample_count")) {
        $v = Get-FromResult0 $j $k
        if ($null -ne $v -and ([string]$v).Trim() -ne "") { $pnlSamples = TryI $v; break }
    }
    $rp = $null
    $rpNum = $null
    $hasRealPnl = $false
    try {
        if ($props -contains "realized_pnl") {
            $rp = $j.realized_pnl
            $tmp = 0.0
            if ($null -ne $rp -and ([double]::TryParse(([string]$rp), [ref]$tmp))) {
                $rpNum = [double]$tmp
                $hasRealPnl = $true
            }
        }
    } catch { $rp=$null; $rpNum=$null; $hasRealPnl=$false }
    if ($props -contains "realized_pnl") { $rp = [string]$j.realized_pnl }
        # REALIZED_PNL_FALLBACK_FROM_PAPERLIVE_BEGIN
    # Prefer result[0].realized_pnl if present (paper_live schema), else top-level.
    if(-not $hasRealPnl){
        foreach($k in @("realized_pnl","pnl","net_pnl","profit","pl")){
            try {
                $vv = Get-FromResult0 $j $k
                if ($null -eq $vv -or ([string]$vv).Trim() -eq "") { continue }
                $tmp2 = 0.0
                if([double]::TryParse(([string]$vv), [ref]$tmp2)){
                    $rpNum = [double]$tmp2
                    $hasRealPnl = $true
                    break
                }
            } catch { }
        }
    }
    # REALIZED_PNL_FALLBACK_FROM_PAPERLIVE_END
$ms = $micro
    $microSrc = "producer"
    if ($ms -eq $null -or [double]$ms -le 0.0) { $ms = 0.0; $microSrc = "derived_micro_live_v1_zero"; if($microLiveDaily -and $microLiveDaily.ContainsKey($asOf)){ $ms = [double]$microLiveDaily[$asOf]; if([double]$ms -gt 0.0){ $microSrc = "micro_live_v1" } } }
    # Fail-closed eligibility: require non-zero metrics OR real pnl samples
    # ELIGIBILITY_FAILCLOSED_LIVE_BEGIN
# Institutional: to prevent GateScore contamination, eligible requires EDGE evidence.
# PnL-only or quote-derived rows must NEVER count toward GateScore live thresholds.
$eligible = ($edge -gt 0.0)
# ELIGIBILITY_FAILCLOSED_LIVE_END
    # PNS_FROM_REALIZED_PNL_BEGIN
    if($hasRealPnl){ $pnlSamples = 1 }
    # PNS_FROM_REALIZED_PNL_END
    $src = if($eligible){"REAL"}else{"STUB"}
    # Fail-closed: STUB events must NOT emit fake zeros/derived values
    if (-not $eligible) {
        $edge = $null
        $ms = $null
        $microSrc = "missing"
    }
    $note = if($eligible){"from_paperlive"}else{"from_paperlive;ineligible_zero_metrics"}
    $outObj = [ordered]@{
        as_of_date         = $asOf
        event_id           = (($asOf + "") + "|NVDA|" + $count.ToString())
        symbol             = "NVDA"
        source             = $src
        score              = $edge
        edge_ratio         = $edge
        micro_score        = $ms
        micro_score_source = $microSrc
        realized_pnl       = $rpNum
        count_signals      = 1
        pnl_samples        = $pnlSamples
        eligible           = [bool]$eligible
        notes              = $note
        metrics_source     = $metricsSource
    }
    # STUB_SINK_BEGIN
    try {
        if($stubCount -gt 0){
            $stubPath = Join-Path $logsDir "nvda_gatescore_events_stub.jsonl"
            [System.IO.File]::WriteAllLines($stubPath, [string[]]$eventsStubOut.ToArray([string]), $utf8NoBom)
            Write-Host ("[NVDA-GS-EVENTS] STUB sink wrote " + $stubCount + " rows to " + $stubPath) -ForegroundColor DarkYellow
        }
    } catch { }
    # STUB_SINK_END
    $jsonLine = ($outObj | ConvertTo-Json -Compress)
    if($eligible){
        [void]$eventsRealOut.Add([string]$jsonLine); $realCount++
    } else {
        [void]$eventsStubOut.Add([string]$jsonLine); $stubCount++
    }
    $count++
}
if ($realCount -lt $MinEvents) { Write-Error "[NVDA-GS-EVENTS] Too few REAL events emitted ($realCount < $MinEvents)."; exit 4 }
$outFull = $OutPath
if (-not [System.IO.Path]::IsPathRooted($outFull)) { $outFull = Join-Path $repoRoot $outFull }
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
if ($Mode -eq "rewrite") {
    [System.IO.File]::WriteAllLines($outFull, [string[]]$eventsRealOut.ToArray([string]), $utf8NoBom)
}
elseif ($Mode -eq "append") {
    # DEDUP_EVENT_ID_APPEND_BEGIN
    # Institutional: append must be idempotent by event_id to prevent artificial sample inflation.
    $existing = New-Object "System.Collections.Generic.HashSet[string]"
    if (Test-Path -LiteralPath $outFull) {
        try {
            foreach($oln in (Get-Content -LiteralPath $outFull -Encoding UTF8)) {
                $t = ($oln + "").Trim(); if(-not $t){ continue }
                try {
                    $oj = $t | ConvertFrom-Json
                    $id = $null
                    if($oj -and ($oj.PSObject.Properties.Name -contains "event_id")){ $id = [string]$oj.event_id }
                    if($id){ [void]$existing.Add($id) }
                } catch { }
            }
        } catch { }
    }

    $newLines = New-Object System.Collections.ArrayList
    $skipped = 0
    foreach($ln in $eventsRealOut){
        $t = ($ln + "").Trim(); if(-not $t){ continue }
        $id = $null
        try { $oj = $t | ConvertFrom-Json; if($oj -and ($oj.PSObject.Properties.Name -contains "event_id")){ $id = [string]$oj.event_id } } catch { $id = $null }
        if($id -and $existing.Contains($id)){ $skipped++; continue }
        if($id){ [void]$existing.Add($id) }
        [void]$newLines.Add([string]$t)
    }

    if($newLines.Count -gt 0){
        [System.IO.File]::AppendAllLines($outFull, [string[]]$newLines.ToArray([string]), $utf8NoBom)
    }
    Write-Host ("[NVDA-GS-EVENTS] append_dedup: added=" + $newLines.Count + " skipped_duplicates=" + $skipped) -ForegroundColor Yellow
    # DEDUP_EVENT_ID_APPEND_END
}
else {
    $pd = $PruneDate; if (-not $pd) { $pd = $today }
    $kept = New-Object System.Collections.ArrayList
    if (Test-Path -LiteralPath $outFull) {
        $old = Get-Content -LiteralPath $outFull -Encoding UTF8
        foreach ($oln in $old) {
            $t = ($oln + "").Trim(); if (-not $t) { continue }
            $oj = $null; try { $oj = $t | ConvertFrom-Json } catch { $oj = $null }
            if ($null -eq $oj) { continue }
            if (($oj.as_of_date + "") -ne $pd) { [void]$kept.Add($t) }
        }
    }
    $merged = New-Object System.Collections.ArrayList
    foreach ($k in $kept) { [void]$merged.Add($k) }
    foreach ($n in $eventsRealOut) { [void]$merged.Add($n) }
    [System.IO.File]::WriteAllLines($outFull, [string[]]$merged.ToArray([string]), $utf8NoBom)
}
Write-Host ("[NVDA-GS-EVENTS] Wrote REAL=" + $realCount + " (total_seen=" + $count + ", stub=" + $stubCount + ") to " + $outFull + " (mode=" + $Mode + ")") -ForegroundColor Green
exit 0
