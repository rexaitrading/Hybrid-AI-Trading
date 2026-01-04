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

# REAL_ONLY_SPLIT_BEGIN
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


  # Institutional eligibility: require non-zero metrics OR real pnl samples
  $hasRealPnl = $false
  $rpNum = $null
  try {
    $tmp = 0.0
    if($null -ne $rp -and ([double]::TryParse(([string]$rp), [ref]$tmp))){ $rpNum = [double]$tmp; $hasRealPnl = $true }
  } catch { $hasRealPnl = $false; $rpNum = $null }
  $eligible = ($edge -gt 0.0 -or [double]$micro -gt 0.0 -or $pnlSamples -gt 0 -or $hasRealPnl)
  $src = if($eligible){"REAL"}else{"STUB"}

  $outObj = [ordered]@{
    as_of_date         = $asOf
    symbol             = "SPY"
    source             = $src
    score              = $edge
    edge_ratio         = $edge
    micro_score        = [double]$micro
    micro_score_source = "producer"
    realized_pnl       = $rpNum
    count_signals      = 1
    pnl_samples        = $pnlSamples
    eligible           = [bool]$eligible
    notes              = "from_paperlive_with_micro"
  }

  $jsonLine = ($outObj | ConvertTo-Json -Compress)
  if($eligible){
    [void]$eventsRealOut.Add([string]$jsonLine); $realCount++
  } else {
    [void]$eventsStubOut.Add([string]$jsonLine); $stubCount++
  }
  $count++
}

if ($realCount -lt $MinEvents) { Write-Error "[SPY-GS-EVENTS] Too few REAL events ($realCount < $MinEvents)."; exit 4 }

$outFull = $OutPath
if (-not [System.IO.Path]::IsPathRooted($outFull)) { $outFull = Join-Path $repoRoot $outFull }
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

if ($Mode -eq "rewrite") {
  [System.IO.File]::WriteAllLines($outFull, [string[]]$eventsRealOut.ToArray([string]), $utf8NoBom)
  # STUB_SINK_BEGIN
  try {
    if($stubCount -gt 0){
      $stubPath = Join-Path $logsDir "spy_gatescore_events_stub.jsonl"
      [System.IO.File]::WriteAllLines($stubPath, [string[]]$eventsStubOut.ToArray([string]), $utf8NoBom)
      Write-Host ("[SPY-GS-EVENTS] STUB sink wrote " + $stubCount + " rows to " + $stubPath) -ForegroundColor DarkYellow
    }
  } catch { }
  # STUB_SINK_END
} else {
  [System.IO.File]::AppendAllLines($outFull, [string[]]$eventsRealOut.ToArray([string]), $utf8NoBom)
}

Write-Host ("[SPY-GS-EVENTS] Wrote REAL=" + $realCount + " (total_seen=" + $count + ", stub=" + $stubCount + ") to " + $outFull + " (mode=" + $Mode + ")") -ForegroundColor Green
exit 0
