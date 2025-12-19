[CmdletBinding()]
param(
    [string]$InputPath = "",
    [string]$OutPath = ".\logs\nvda_gatescore_events.jsonl",
    [int]$MinEvents = 10
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
            $_.Name -match 'nvda.*paperlive.*jsonl' -or $_.Name -match 'nvda.*phase5.*jsonl'
        }
    )
    if (-not $matches -or $matches.Length -eq 0) { return "" }

    ($matches | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
}

function TryD([object]$v) { $x=0.0; if($null -ne $v){[void][double]::TryParse([string]$v,[ref]$x)}; return $x }
function TryI([object]$v) { $x=0;   if($null -ne $v){[void][int]::TryParse([string]$v,[ref]$x)}; return $x }

if (-not $InputPath) { $InputPath = Pick-LatestPaperlive $logsDir }

if (-not $InputPath -or -not (Test-Path -LiteralPath $InputPath)) {
    Write-Error "[NVDA-GS-EVENTS] No input paperlive jsonl found. Provide -InputPath explicitly."
    exit 2
}

Write-Host "[NVDA-GS-EVENTS] Input=$InputPath" -ForegroundColor Cyan

$lines = Get-Content -LiteralPath $InputPath -Encoding UTF8
if (-not $lines -or $lines.Count -eq 0) {
    Write-Error "[NVDA-GS-EVENTS] Input jsonl is empty: $InputPath"
    exit 3
}

# Use ArrayList to avoid += coercion and generic overload weirdness
$eventsOut = New-Object System.Collections.ArrayList
$count = 0

foreach ($ln in $lines) {
    $s = ($ln + "").Trim()
    if (-not $s) { continue }

    $j = $null
    try { $j = $s | ConvertFrom-Json } catch { continue }
    if ($null -eq $j) { continue }

    $props = $j.PSObject.Properties.Name

    # Expanded key-map (no guessing; safe fallbacks)
    $edge = 0.0
    foreach ($k in @("edge_ratio","mean_edge_ratio","edge","edge_mean","gatescore_edge","edgeValue","edge_score")) {
        if ($props -contains $k) { $edge = TryD ($j.$k); break }
    }

    $micro = 0.0
    foreach ($k in @("micro_score","mean_micro_score","micro","micro_mean","gatescore_micro","microValue","micro_score_mean")) {
        if ($props -contains $k) { $micro = TryD ($j.$k); break }
    }

    $pnlSamples = 0
    foreach ($k in @("pnl_samples","pnlSamples","pnl_n","trades_n","trade_count","n_trades","samples","sample_count")) {
        if ($props -contains $k) { $pnlSamples = TryI ($j.$k); break }
    }

    $rp = $null
    if ($props -contains "realized_pnl") { $rp = _TryString $j.realized_pnl }

    $outObj = [ordered]@{
        as_of_date    = $today
        symbol        = "NVDA"
        source        = "REAL"
        score         = $edge
        edge_ratio    = $edge
        micro_score   = $micro
        realized_pnl  = $rp
        count_signals = 1
        pnl_samples   = $pnlSamples
        notes         = "from_paperlive"
    }

    [void]$eventsOut.Add(($outObj | ConvertTo-Json -Compress))
    $count++
}

if ($count -lt $MinEvents) {
    Write-Error "[NVDA-GS-EVENTS] Too few events emitted ($count < $MinEvents). Refusing (fail-closed)."
    exit 4
}

$outFull = $OutPath
if (-not [System.IO.Path]::IsPathRooted($outFull)) {
    $outFull = Join-Path $repoRoot $outFull
}

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::AppendAllLines($outFull, [string[]]$eventsOut.ToArray([string]), $utf8NoBom)

Write-Host "[NVDA-GS-EVENTS] Appended $count events to $outFull (as_of_date=$today)" -ForegroundColor Green
exit 0