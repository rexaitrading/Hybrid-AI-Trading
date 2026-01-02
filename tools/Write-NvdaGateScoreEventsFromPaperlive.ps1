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

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$logsDir  = Join-Path $repoRoot "logs"
$today    = (Get-Date).ToString("yyyy-MM-dd")

function Pick-LatestPaperlive([string]$dir) {
    $all = @(Get-ChildItem -LiteralPath $dir -File -Force -ErrorAction SilentlyContinue)
    if (-not $all -or $all.Length -eq 0) { return "" }

    $matches = @(
        $all | Where-Object {
            $_.Name -match '(?i)^paper_live_nvda_.*\.jsonl$' -or
            $_.Name -match '(?i)nvda.*paperlive.*\.jsonl$' -or
            $_.Name -match '(?i)nvda.*phase5.*\.jsonl$'
        }
    )
    if (-not $matches -or $matches.Length -eq 0) { return "" }

    ($matches | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
}

function TryD([object]$v) { $x=0.0; if($null -ne $v){[void][double]::TryParse([string]$v,[ref]$x)}; return $x }
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

if (-not $InputPath) { $InputPath = Pick-LatestPaperlive $logsDir }
if (-not $InputPath -or -not (Test-Path -LiteralPath $InputPath)) { Write-Error "[NVDA-GS-EVENTS] No input paperlive jsonl found."; exit 2 }

Write-Host "[NVDA-GS-EVENTS] Input=$InputPath" -ForegroundColor Cyan

$lines = Get-Content -LiteralPath $InputPath -Encoding UTF8
if (-not $lines -or $lines.Count -eq 0) { Write-Error "[NVDA-GS-EVENTS] Input jsonl is empty: $InputPath"; exit 3 }

$eventsOut = New-Object System.Collections.ArrayList
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
        if ($props -contains $k) { $edge = TryD (Get-FromResult0 $j $k); break }
    }

    $micro = 0.0
    foreach ($k in @("micro_score","mean_micro_score","micro","micro_mean","gatescore_micro","microValue","micro_score_mean")) {
        if ($props -contains $k) { $micro = TryD (Get-FromResult0 $j $k); break }
    }

    $pnlSamples = 0
    foreach ($k in @("pnl_samples","pnlSamples","pnl_n","trades_n","trade_count","n_trades","samples","sample_count")) {
        if ($props -contains $k) { $pnlSamples = TryI (Get-FromResult0 $j $k); break }
    }

    $rp = $null
    if ($props -contains "realized_pnl") { $rp = [string]$j.realized_pnl }

    $ms = $micro
    $microSrc = "producer"
    if ($ms -eq $null -or [double]$ms -le 0.0) { $ms = Get-DerivedMicroScore -EdgeRatio $edge; $microSrc = "derived_v1" }

    # Fail-closed eligibility: require non-zero metrics OR real pnl samples
    $eligible = ($edge -gt 0.0 -or [double]$ms -gt 0.0 -or $pnlSamples -gt 0)
    $src = if($eligible){"REAL"}else{"STUB"}
    $note = if($eligible){"from_paperlive"}else{"from_paperlive;ineligible_zero_metrics"}
    $outObj = [ordered]@{
        as_of_date         = $asOf
        symbol             = "NVDA"
        source             = $src
        score              = $edge
        edge_ratio         = $edge
        micro_score        = [double]$ms
        micro_score_source = $microSrc
        realized_pnl       = $rp
        count_signals      = 1
        pnl_samples        = $pnlSamples
        eligible           = [bool]$eligible
        notes              = $note
    }

    [void]$eventsOut.Add(($outObj | ConvertTo-Json -Compress))
    $count++
}

if ($count -lt $MinEvents) { Write-Error "[NVDA-GS-EVENTS] Too few events emitted ($count < $MinEvents)."; exit 4 }

$outFull = $OutPath
if (-not [System.IO.Path]::IsPathRooted($outFull)) { $outFull = Join-Path $repoRoot $outFull }

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

if ($Mode -eq "rewrite") {
    [System.IO.File]::WriteAllLines($outFull, [string[]]$eventsOut.ToArray([string]), $utf8NoBom)
}
elseif ($Mode -eq "append") {
    [System.IO.File]::AppendAllLines($outFull, [string[]]$eventsOut.ToArray([string]), $utf8NoBom)
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
    foreach ($n in $eventsOut) { [void]$merged.Add($n) }
    [System.IO.File]::WriteAllLines($outFull, [string[]]$merged.ToArray([string]), $utf8NoBom)
}

Write-Host "[NVDA-GS-EVENTS] Wrote $count events to $outFull (mode=$Mode)" -ForegroundColor Green
exit 0

