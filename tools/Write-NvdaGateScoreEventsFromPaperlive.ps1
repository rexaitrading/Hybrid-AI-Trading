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

# --- deterministic rewrite semantics: truncate output FIRST (prevents stale PLACEHOLDER persistence) ---
if($Mode -eq "rewrite"){
  $enc = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText((Resolve-Path $OutPath).Path, "", $enc)
}
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$logsDir  = Join-Path $repoRoot "logs"
$today    = (Get-Date).ToString("yyyy-MM-dd")

function Pick-LatestPaperlive([string]$dir) {
    $all = @(Get-ChildItem -LiteralPath $dir -File -Force -ErrorAction SilentlyContinue)
    if (-not $all -or $all.Length -eq 0) { return "" }

    $matches = @(
        $all | Where-Object { $_.Name -match 'nvda.*paperlive.*jsonl' -or $_.Name -match 'nvda.*phase5.*jsonl' }
    )
    if (-not $matches -or $matches.Length -eq 0) { return "" }

    ($matches | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
}

function TryD([object]$v) { $x=0.0; if($null -ne $v){[void][double]::TryParse([string]$v,[ref]$x)}; return $x }
function TryI([object]$v) { $x=0;   if($null -ne $v){[void][int]::TryParse([string]$v,[ref]$x)}; return $x }

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

$lines = @(Get-Content -LiteralPath $InputPath -Encoding UTF8)
if (-not $lines -or $lines.Count -eq 0) {
  # rewrite-mode should never leave stale outputs behind
  if($Mode -eq "rewrite"){
    $enc = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText((Resolve-Path $OutPath).Path, "", $enc)
  }
  Write-Host ("[NVDA-GS-EVENTS] INPUT_EMPTY: mode={0} input={1} -> fail-closed (rc=4)" -f $Mode,$InputPath) -ForegroundColor Yellow
  exit 4
}

$eventsOut = New-Object System.Collections.ArrayList
$count = 0

# --- StrictMode-safe realized_pnl evidence defaults ---
$rpOk = $false
$rpNum = 0.0
foreach ($ln in $lines) {
    $s = ($ln + "").Trim()
    if (-not $s) { continue }

    $j = $null
    try { $j = $s | ConvertFrom-Json } catch { continue }
    if ($null -eq $j) { continue }

    $props = $j.PSObject.Properties.Name
    $asOf = Pick-Date $j @("as_of_date","date","trading_day","day","ts","timestamp","ts_utc") $today
    # rewrite-mode is "today-only": never manufacture today from stale rows
    if ($Mode -eq "rewrite") {
        if ($asOf -ne $today) { continue }
    }
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
$rp = $null; $rpOk = $false
if ($props -contains "realized_pnl") {
  $s = [string]$j.realized_pnl
  if([double]::TryParse($s, [ref]$rpNum)){
    $rp = [double]$rpNum
    $rpOk = $true
  } else {
    $rp = $null
    $rpOk = $false
  }
}
# pnl_samples evidence-based: 1 only when realized_pnl parsed numeric; else 0
$pnlSamples = if($rpOk){ 1 } else { 0 }

$ms = $micro
    $microSrc = "producer"
    if ($ms -eq $null -or [double]$ms -le 0.0) { $ms = Get-DerivedMicroScore -EdgeRatio $edge; $microSrc = "derived_v1" }

    $outObj = [ordered]@{
        as_of_date         = $asOf
        symbol             = "NVDA"
        source             = "REAL"
        score              = $edge
        edge_ratio         = $edge
        micro_score        = [double]$ms
        micro_score_source = $microSrc
        realized_pnl       = $rp
        count_signals      = 1
        pnl_samples        = $pnlSamples
        notes              = "from_paperlive"
    }

    # Tighten-only: deny synthetic producer rows from becoming OFFICIAL GateScore events.
    $isSynth = $false
    try { if($props -contains "is_synthetic"){ $isSynth = [bool]$j.is_synthetic } } catch {}
    $noteS = ""
    try { if($props -contains "notes"){ $noteS = ("" + $j.notes) } } catch {}
    $srcS = ""
    try { if($props -contains "source"){ $srcS = ("" + $j.source) } } catch {}
    if($isSynth -or ($noteS -match "synthetic_metrics=true") -or ($srcS -match "paper_runner_stub")){
      # keep for stub audit only, not official events
      $outObj.source = "paper_runner_stub"
      $outObj.notes  = (([string]$outObj.notes) + ";synthetic_row_denied")
      $eventsOut.Add(($outObj | ConvertTo-Json -Compress)) | Out-Null
      continue
    }

    [void]$eventsOut.Add(($outObj | ConvertTo-Json -Compress))
    $count++
}
# NO_TODAY_ROWS_FOR_REWRITE
if ($Mode -eq "rewrite" -and $count -lt $MinEvents) {
    Write-Host ("[NVDA-GS-EVENTS] NO_TODAY_ROWS: emitted={0} MinEvents={1} today={2} input={3}" -f $count,$MinEvents,$today,$InputPath) -ForegroundColor Red
    exit 4
}

# --- Institutional guard: degenerate constant metrics => FAIL-CLOSED (do not pollute official events) ---
try {
  $edgeSet = New-Object System.Collections.Generic.HashSet[string]
  $microSet = New-Object System.Collections.Generic.HashSet[string]
  foreach($ln2 in $eventsOut){
    $o=$null; try{$o=($ln2|ConvertFrom-Json)}catch{$o=$null}
    if($null -eq $o){ continue }
    $edgeSet.Add([string]$o.edge_ratio) | Out-Null
    $microSet.Add([string]$o.micro_score) | Out-Null
  }
  if(($edgeSet.Count -le 1) -and ($microSet.Count -le 1)){
    # Write stub-only file for debugging; keep official file clean.
    $stubPath = Join-Path $logsDir "nvda_gatescore_events_stub.jsonl"
    $utf8NoBom2 = New-Object System.Text.UTF8Encoding($false)
    $tmp = New-Object System.Collections.Generic.List[string]
    for($i=0; $i -lt $eventsOut.Count; $i++){
      $o = $eventsOut[$i] | ConvertFrom-Json
      $o.source = "paper_runner_stub"
      $o.notes = (([string]$o.notes) + ";degenerate_constant_metrics")
      $tmp.Add(($o | ConvertTo-Json -Compress)) | Out-Null
    }
    [System.IO.File]::WriteAllLines([System.IO.Path]::GetFullPath($stubPath), $tmp.ToArray(), $utf8NoBom2)
    Write-Host "[NVDA-GS-EVENTS] FAIL-CLOSED: degenerate_constant_metrics -> wrote STUB file only (no official events)" -ForegroundColor Yellow

    # rewrite-mode must not leave stale outputs behind
    if($Mode -eq "rewrite"){
      $enc3 = New-Object System.Text.UTF8Encoding($false)
      [System.IO.File]::WriteAllText((Resolve-Path $OutPath).Path, "", $enc3)
    }
    exit 4
  }
} catch { }
# --- end institutional guard ---


Write-Host "[NVDA-GS-EVENTS] Wrote $count events to $outFull (mode=$Mode)" -ForegroundColor Green
exit 0
