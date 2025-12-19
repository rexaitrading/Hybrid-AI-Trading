[CmdletBinding()]
param(
    # Input paperlive jsonl (defaults to newest matching file under logs/)
    [string]$InputPath = "",
    # Output events jsonl
    [string]$OutPath = ".\logs\nvda_gatescore_events.jsonl"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$logsDir  = Join-Path $repoRoot "logs"
$today    = (Get-Date).ToString("yyyy-MM-dd")

function _PickLatestPaperlive([string]$logsDir) {
    $cands = @(Get-ChildItem $logsDir -File -Force -ErrorAction SilentlyContinue |
        Where-Object { [CmdletBinding()]
param(
    # Input paperlive jsonl (defaults to newest matching file under logs/)
    [string]$InputPath = "",
    # Output events jsonl
    [string]$OutPath = ".\logs\nvda_gatescore_events.jsonl"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$logsDir  = Join-Path $repoRoot "logs"
$today    = (Get-Date).ToString("yyyy-MM-dd")

function _PickLatestPaperlive([string]$logsDir) {
    $cands = Get-ChildItem $logsDir -File -Force -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match 'nvda.*paperlive.*jsonl|nvda.*phase5.*jsonl' } |
        Sort-Object LastWriteTime -Descending
    if ($cands -and $cands.Count -gt 0) { return $cands[0].FullName }
    return ""
}

if (-not $InputPath) {
    $InputPath = _PickLatestPaperlive $logsDir
}

if (-not $InputPath -or -not (Test-Path $InputPath)) {
    Write-Error "[NVDA-GS-EVENTS] No input paperlive jsonl found. Provide -InputPath explicitly."
    exit 2
}

Write-Host "[NVDA-GS-EVENTS] Input=$InputPath" -ForegroundColor Cyan

# Parse jsonl (best-effort)
$lines = Get-Content $InputPath -Encoding UTF8
if (-not $lines -or $lines.Count -eq 0) {
    Write-Error "[NVDA-GS-EVENTS] Input jsonl is empty: $InputPath"
    exit 3
}

# Minimal extraction helpers
function _TryD([object]$v) { $x=0.0; if($null -ne $v){[void][double]::TryParse([string]$v,[ref]$x)}; return $x }
function _TryI([object]$v) { $x=0;   if($null -ne $v){[void][int]::TryParse([string]$v,[ref]$x)}; return $x }

$eventsOut = New-Object System.Collections.Generic.List[string]
$count = 0

foreach ($ln in $lines) {
    $s = $ln.Trim()
    if (-not $s) { continue }
    $j = $null
    try { $j = $s | ConvertFrom-Json } catch { continue }
    if ($null -eq $j) { continue }

    # We only emit "signal rows" (best effort). If no clue, still emit but mark notes.
    $edge  = 0.0
    $micro = 0.0
    $pnlSamples = 0

    # prefer keys if present
    $props = $j.PSObject.Properties.Name
    if ($props -contains "edge_ratio")      { $edge  = _TryD $j.edge_ratio }
    elseif ($props -contains "mean_edge_ratio") { $edge = _TryD $j.mean_edge_ratio }

    if ($props -contains "micro_score")     { $micro = _TryD $j.micro_score }
    elseif ($props -contains "mean_micro_score"){ $micro = _TryD $j.mean_micro_score }

    if ($props -contains "pnl_samples")     { $pnlSamples = _TryI $j.pnl_samples }

    # Emit one event row per line (keeps count_signals meaningful)
    $out = [ordered]@{
        as_of_date    = $today
        symbol        = "NVDA"
        source        = "REAL"
        score         = $edge          # keep legacy behavior
        edge_ratio    = $edge
        micro_score   = $micro
        count_signals = 1
        pnl_samples   = $pnlSamples
        notes         = "from_paperlive"
    } | ConvertTo-Json -Compress

    $eventsOut.Add($out) | Out-Null
    $count++
}

if ($count -lt 10) {
    Write-Error "[NVDA-GS-EVENTS] Too few events emitted ($count). Refusing (fail-closed)."
    exit 4
}

# Append-safe write (UTF-8 no BOM), keep file growing
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
# Resolve output path safely (supports relative .\logs\.. or absolute paths)
$outFull = $OutPath
if (-not [System.IO.Path]::IsPathRooted($outFull)) {
    $outFull = Join-Path $repoRoot $outFull
}
[System.IO.File]::AppendAllLines($outFull, $eventsOut, $utf8NoBom)

Write-Host "[NVDA-GS-EVENTS] Appended $count events to $OutPath (as_of_date=$today)" -ForegroundColor Green
exit 0.Name -match 'nvda.*paperlive.*jsonl|nvda.*phase5.*jsonl' } |
        Sort-Object LastWriteTime -Descending)
    if ($cands -and $cands.Length -gt 0) { return $cands[0].FullName }
    return ""
} |
        Sort-Object LastWriteTime -Descending
    if ($cands -and $cands.Count -gt 0) { return $cands[0].FullName }
    return ""
}

if (-not $InputPath) {
    $InputPath = _PickLatestPaperlive $logsDir
}

if (-not $InputPath -or -not (Test-Path $InputPath)) {
    Write-Error "[NVDA-GS-EVENTS] No input paperlive jsonl found. Provide -InputPath explicitly."
    exit 2
}

Write-Host "[NVDA-GS-EVENTS] Input=$InputPath" -ForegroundColor Cyan

# Parse jsonl (best-effort)
$lines = Get-Content $InputPath -Encoding UTF8
if (-not $lines -or $lines.Count -eq 0) {
    Write-Error "[NVDA-GS-EVENTS] Input jsonl is empty: $InputPath"
    exit 3
}

# Minimal extraction helpers
function _TryD([object]$v) { $x=0.0; if($null -ne $v){[void][double]::TryParse([string]$v,[ref]$x)}; return $x }
function _TryI([object]$v) { $x=0;   if($null -ne $v){[void][int]::TryParse([string]$v,[ref]$x)}; return $x }

$eventsOut = New-Object System.Collections.Generic.List[string]
$count = 0

foreach ($ln in $lines) {
    $s = $ln.Trim()
    if (-not $s) { continue }
    $j = $null
    try { $j = $s | ConvertFrom-Json } catch { continue }
    if ($null -eq $j) { continue }

    # We only emit "signal rows" (best effort). If no clue, still emit but mark notes.
    $edge  = 0.0
    $micro = 0.0
    $pnlSamples = 0

    # prefer keys if present
    $props = $j.PSObject.Properties.Name
    if ($props -contains "edge_ratio")      { $edge  = _TryD $j.edge_ratio }
    elseif ($props -contains "mean_edge_ratio") { $edge = _TryD $j.mean_edge_ratio }

    if ($props -contains "micro_score")     { $micro = _TryD $j.micro_score }
    elseif ($props -contains "mean_micro_score"){ $micro = _TryD $j.mean_micro_score }

    if ($props -contains "pnl_samples")     { $pnlSamples = _TryI $j.pnl_samples }

    # Emit one event row per line (keeps count_signals meaningful)
    $out = [ordered]@{
        as_of_date    = $today
        symbol        = "NVDA"
        source        = "REAL"
        score         = $edge          # keep legacy behavior
        edge_ratio    = $edge
        micro_score   = $micro
        count_signals = 1
        pnl_samples   = $pnlSamples
        notes         = "from_paperlive"
    } | ConvertTo-Json -Compress

    $eventsOut.Add($out) | Out-Null
    $count++
}

if ($count -lt 10) {
    Write-Error "[NVDA-GS-EVENTS] Too few events emitted ($count). Refusing (fail-closed)."
    exit 4
}

# Append-safe write (UTF-8 no BOM), keep file growing
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
# Resolve output path safely (supports relative .\logs\.. or absolute paths)
$outFull = $OutPath
if (-not [System.IO.Path]::IsPathRooted($outFull)) {
    $outFull = Join-Path $repoRoot $outFull
}
[System.IO.File]::AppendAllLines($outFull, $eventsOut, $utf8NoBom)

Write-Host "[NVDA-GS-EVENTS] Appended $count events to $OutPath (as_of_date=$today)" -ForegroundColor Green
exit 0