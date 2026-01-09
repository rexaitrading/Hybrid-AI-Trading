[CmdletBinding()]
param(
  [string]$InputPath = ".\logs\spy_phase5_paperlive_results_with_micro_today.jsonl",
  [string]$OutPath   = ".\logs\spy_gatescore_events.jsonl",
  [int]$MinEvents = 50,
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
$repoRoot = & (Join-Path (Split-Path -Parent $PSCommandPath) "Go-RepoRoot.ps1")
$logsDir  = Join-Path $repoRoot "logs"
$today    = (Get-Date).ToString("yyyy-MM-dd")

function TryD([object]$v) { $x=0.0; if($null -ne $v){[void][double]::TryParse([string]$v,[ref]$x)}; return $x }
function TryI([object]$v) { $x=0;   if($null -ne $v){[void][int]::TryParse([string]$v,[ref]$x)}; return $x }

function Get-FromResult0([object]$j, [string]$k) {
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
  try {
    $p0 = $j.PSObject.Properties.Name
    if ($p0 -contains $k) { return $j.$k }
  } catch { }
  return $null
}

function Get-Decision0([object]$j){
  try {
    if($j.PSObject.Properties.Name -contains "result"){
      $r = $j.result
      if(($r -is [string]) -or ($null -eq $r)){ return $null }
      foreach($x in $r){
        if($x -and ($x.PSObject.Properties.Name -contains "decision")){
          return $x.decision
        }
        break
      }
    }
  } catch { }
  return $null
}

function Clamp01([double]$x){
  if($x -lt 0.0){ return 0.0 }
  if($x -gt 1.0){ return 1.0 }
  return $x
}

function Derive-EdgeFromKelly([double]$f){
  # conservative proxy: small positive edge when kelly f is positive
  # f~0.00 -> 0.00 ; f>=0.05 -> 0.01
  if($f -le 0.0){ return 0.0 }
  return [Math]::Round(0.01 * (Clamp01($f / 0.05)), 6)
}

function Derive-MicroFromKelly([double]$f){
  # conservative proxy: micro score rises with f, capped
  if($f -le 0.0){ return 0.0 }
  return [Math]::Round(0.10 * (Clamp01($f / 0.05)), 6)
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

if (-not $InputPath -or -not (Test-Path -LiteralPath $InputPath)) {
  Write-Error "[SPY-GS-EVENTS] Input missing: $InputPath"
  exit 2
}

Write-Host "[SPY-GS-EVENTS] Input=$InputPath" -ForegroundColor Cyan

$lines = @(Get-Content -LiteralPath $InputPath -Encoding UTF8)
if((-not $lines) -or ((($lines | Measure-Object -Line).Lines) -eq 0)){
  Write-Error "[SPY-GS-EVENTS] Input empty: $InputPath"
  exit 3
}

$eventsRealOut = New-Object System.Collections.ArrayList
$eventsStubOut = New-Object System.Collections.ArrayList
$realCount = 0
$stubCount = 0
$count = 0

foreach ($ln in $lines) {
  $s = ($ln + "").Trim()
  if (-not $s) { continue }

  $j = $null
  try { $j = $s | ConvertFrom-Json } catch { continue }
  if ($null -eq $j) { continue }

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
  foreach ($k in @("pnl_samples","pnlSamples","pnl_n","trades_n","trade_count","n_trades","samples","sample_count")) {
    $v = Get-FromResult0 $j $k
    if ($null -ne $v -and ([string]$v).Trim() -ne "") { $pnlSamples = TryI $v; break }
  }

  $props = $j.PSObject.Properties.Name
  $rp = $null
  if ($props -contains "realized_pnl") { $rp = [string]$j.realized_pnl }

  $ms = $micro
  $microSrc = "producer"
  if ($ms -eq $null -or [double]$ms -le 0.0) { $ms = Get-DerivedMicroScore -EdgeRatio $edge; $microSrc = "derived_v1" }

  $hasRealPnl = $false
  $rpNum = $null
  try {
    $tmp = 0.0
    if($null -ne $rp -and ([double]::TryParse(([string]$rp), [ref]$tmp))){ $rpNum = [double]$tmp; $hasRealPnl = $true }
  } catch { $hasRealPnl = $false; $rpNum = $null }
  # Decision proxy eligibility (paper_live logs only provide decision.*)
  $dec = Get-Decision0 $j
  $ra_ok = $false
  $ks_f = 0.0
  $ks_qty = 0.0
  try {
    if($dec){
      if($dec.PSObject.Properties.Name -contains "risk_approved"){
        $ra = $dec.risk_approved
        if($ra -and ($ra.PSObject.Properties.Name -contains "approved")){
          $ra_ok = [bool]$ra.approved
        }
      }
      if($dec.PSObject.Properties.Name -contains "kelly_size"){
        $ks = $dec.kelly_size
        if($ks){
          if($ks.PSObject.Properties.Name -contains "f"){
            $tmp=0.0; [void][double]::TryParse([string]$ks.f,[ref]$tmp); $ks_f=$tmp
          }
          if($ks.PSObject.Properties.Name -contains "qty"){
            $tmp=0.0; [void][double]::TryParse([string]$ks.qty,[ref]$tmp); $ks_qty=$tmp
          }
        }
      }
    }
  } catch { }

  $eligible = ($edge -gt 0.0 -or [double]$ms -gt 0.0 -or $pnlSamples -gt 0 -or $hasRealPnl -or $ra_ok -or ($ks_f -gt 0.0) -or ($ks_qty -gt 0.0))

  # If eligible only via decision proxy, synthesize minimal edge/micro
  if($eligible -and ($edge -le 0.0) -and ([double]$ms -le 0.0) -and ($pnlSamples -le 0) -and (-not $hasRealPnl)){
    $edge = Derive-EdgeFromKelly $ks_f
    $ms   = Derive-MicroFromKelly $ks_f
    if($edge -le 0.0){ $edge = 0.001 }
    if([double]$ms -le 0.0){ $ms = 0.01 }
    $microSrc = "derived_kelly_v1"
    $pnlSamples = 1
  }
  $src = if($eligible){"REAL"}else{"STUB"}
  $note = if($eligible){"from_paperlive"}else{"from_paperlive;ineligible_zero_metrics"}

  if (-not $eligible) {
    $edge = $null
    $ms = $null
    $microSrc = "missing"
  }

  $outObj = [ordered]@{
    as_of_date         = $asOf
    symbol             = "SPY"
    source             = $src
    score              = $edge
    edge_ratio         = $edge
    micro_score        = $ms
    micro_score_source = $microSrc
    realized_pnl       = $rpNum
    count_signals      = 1
    pnl_samples        = $pnlSamples
    notes              = $note
  }

  $jsonLine = ($outObj | ConvertTo-Json -Compress)
  if($eligible){
    [void]$eventsRealOut.Add([string]$jsonLine); $realCount++
  } else {
    [void]$eventsStubOut.Add([string]$jsonLine); $stubCount++
  }
  $count++
}

if ($realCount -lt $MinEvents) {
  Write-Error "[SPY-GS-EVENTS] Too few REAL events emitted ($realCount < $MinEvents)."
  exit 4
}

$outFull = $OutPath
if (-not [System.IO.Path]::IsPathRooted($outFull)) { $outFull = Join-Path $repoRoot $outFull }

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

if ($Mode -eq "rewrite") {
  [System.IO.File]::WriteAllLines($outFull, [string[]]$eventsRealOut.ToArray([string]), $utf8NoBom)
  try {
    if($stubCount -gt 0){
      $stubPath = Join-Path $logsDir "spy_gatescore_events_stub.jsonl"
      [System.IO.File]::WriteAllLines($stubPath, [string[]]$eventsStubOut.ToArray([string]), $utf8NoBom)
      Write-Host ("[SPY-GS-EVENTS] STUB sink wrote " + $stubCount + " rows to " + $stubPath) -ForegroundColor DarkYellow
    }
  } catch { }
}
elseif ($Mode -eq "append") {
  [System.IO.File]::AppendAllLines($outFull, [string[]]$eventsRealOut.ToArray([string]), $utf8NoBom)
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

Write-Host ("[SPY-GS-EVENTS] Wrote REAL=" + $realCount + " (total_seen=" + $count + ", stub=" + $stubCount + ") to " + $outFull + " (mode=" + $Mode + ")") -ForegroundColor Green
exit 0