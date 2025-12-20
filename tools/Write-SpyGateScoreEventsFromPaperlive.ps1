[CmdletBinding()]
param(
  [string]$InputPath = ".\logs\spy_phase5_paperlive_results_with_micro_today.jsonl",
  [string]$OutPath   = ".\logs\spy_gatescore_events.jsonl",
  [int]$MinEvents = 50,
  [ValidateSet("rewrite","append")]
  [string]$Mode = "rewrite"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Set-Location $repoRoot

$today = (Get-Date).ToString("yyyy-MM-dd")
if (-not (Test-Path -LiteralPath $InputPath)) { Write-Error "[SPY-GS-EVENTS] Input missing: $InputPath"; exit 2 }

function TryD([object]$v) { $x=0.0; if($null -ne $v){[void][double]::TryParse([string]$v,[ref]$x)}; return $x }
function TryI([object]$v) { $x=0;   if($null -ne $v){[void][int]::TryParse([string]$v,[ref]$x)}; return $x }

$lines = Get-Content -LiteralPath $InputPath -Encoding UTF8
if (-not $lines -or $lines.Count -eq 0) { Write-Error "[SPY-GS-EVENTS] Input empty: $InputPath"; exit 3 }

$eventsOut = New-Object System.Collections.ArrayList
$count = 0

foreach ($ln in $lines) {
  $s = ($ln + "").Trim()
  if (-not $s) { continue }

  $j = $null
  try { $j = $s | ConvertFrom-Json } catch { continue }
  if ($null -eq $j) { continue }

  $props = $j.PSObject.Properties.Name

  # Force today stamp in rewrite mode (prevents stale carry)
  $asOf = $today

  $edge = 0.0
  foreach ($k in @("edge_ratio","mean_edge_ratio","edge","edge_mean","gatescore_edge")) {
    if ($props -contains $k) { $edge = TryD ($j.$k); break }
  }

  $micro = 0.0
  foreach ($k in @("micro_score","mean_micro_score","micro","micro_mean","gatescore_micro")) {
    if ($props -contains $k) { $micro = TryD ($j.$k); break }
  }

  $pnlSamples = 0
  foreach ($k in @("pnl_samples","pnlSamples","samples","sample_count","n_trades")) {
    if ($props -contains $k) { $pnlSamples = TryI ($j.$k); break }
  }

  $rp = $null
  if ($props -contains "realized_pnl") { $rp = [string]$j.realized_pnl }

  $outObj = [ordered]@{
    as_of_date         = $asOf
    symbol             = "SPY"
    source             = "PAPERLIVE"
    score              = $edge
    edge_ratio         = $edge
    micro_score        = [double]$micro
    micro_score_source = "producer"
    realized_pnl       = $rp
    count_signals      = 1
    pnl_samples        = $pnlSamples
    notes              = "from_paperlive_with_micro"
  }

  [void]$eventsOut.Add(($outObj | ConvertTo-Json -Compress))
  $count++
}

if ($count -lt $MinEvents) { Write-Error "[SPY-GS-EVENTS] Too few events ($count < $MinEvents)."; exit 4 }

$outFull = $OutPath
if (-not [System.IO.Path]::IsPathRooted($outFull)) { $outFull = Join-Path $repoRoot $outFull }
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

if ($Mode -eq "rewrite") {
  [System.IO.File]::WriteAllLines($outFull, [string[]]$eventsOut.ToArray([string]), $utf8NoBom)
} else {
  [System.IO.File]::AppendAllLines($outFull, [string[]]$eventsOut.ToArray([string]), $utf8NoBom)
}

Write-Host "[SPY-GS-EVENTS] Wrote $count events to $outFull (mode=$Mode)" -ForegroundColor Green
exit 0