[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "ALL",
  [switch]$StrictToday
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
$logsDir  = Join-Path $repoRoot "logs"

$today   = (Get-Date).ToString("yyyy-MM-dd")
$outPath = Join-Path $logsDir "gatescore_pnl_summary.csv"

function Slice-Date([string]$d){
  if(-not $d){ return "" }
  if($d.Length -ge 10){ return $d.Substring(0,10) }
  return $d
}

function TryD([object]$v){
  $x=0.0
  if($null -eq $v){ return $null }
  if([double]::TryParse([string]$v,[ref]$x)){ return [double]$x }
  return $null
}

function TryS([object]$v){
  if($null -eq $v){ return "" }
  return ([string]$v)
}

function Read-Jsonl([string]$Path){
  if(-not (Test-Path -LiteralPath $Path)){ return @() }
  $out=@()
  foreach($ln in @(Get-Content -LiteralPath $Path -Encoding UTF8)){
    $s = ($ln + "").Trim()
    if(-not $s){ continue }
    try{ $out += ($s | ConvertFrom-Json) } catch {}
  }
  return @($out)
}

function Get-EventDate($e){
  $props = $e.PSObject.Properties.Name
  foreach($k in @("as_of_date","date","trading_day")){
    if($props -contains $k){
      $v = Slice-Date (TryS $e.$k)
      if($v){ return $v }
    }
  }
  foreach($k in @("ts_utc","ts","timestamp")){
    if($props -contains $k){
      $t = TryS $e.$k
      if($t.Length -ge 10){ return $t.Substring(0,10) }
    }
  }
  return ""
}

function Mean($arr){
  $vals = @($arr)
  if($null -eq $vals -or $vals.Count -eq 0){ return 0.0 }
  $sum=0.0
  foreach($v in $vals){ $sum += [double]$v }
  return $sum / [double]$vals.Count
}

function Get-PnlSamples($events){
  $sum = 0
  foreach($e in @($events)){
    try{
      $props = $e.PSObject.Properties.Name
      foreach($k in @("pnl_samples","pnlSamples","sample_count","samples","count_signals")){
        if($props -contains $k){
          $n=0
          if([int]::TryParse([string]$e.$k,[ref]$n)){ $sum += $n; break }
        }
      }
    } catch {}
  }
  return [int]$sum
}

$eventFiles = @(
  @{ sym="NVDA"; path=(Join-Path $logsDir "nvda_gatescore_events.jsonl") },
  @{ sym="SPY";  path=(Join-Path $logsDir "spy_gatescore_events.jsonl")  },
  @{ sym="QQQ";  path=(Join-Path $logsDir "qqq_gatescore_events.jsonl")  }
)

$wanted = switch($Symbol.ToUpperInvariant()){
  "NVDA" { @("NVDA") }
  "SPY"  { @("SPY")  }
  "QQQ"  { @("QQQ")  }
  default { @("NVDA","SPY","QQQ") }
}

$rowsOut = @()

foreach($it in $eventFiles){
  $sym = [string]$it.sym
  if($wanted -notcontains $sym){ continue }

  $path = [string]$it.path
  if(-not (Test-Path -LiteralPath $path)){ continue }

  $events = @(Read-Jsonl $path)
  if(-not $events -or $events.Count -eq 0){ continue }

  $latest=""
  foreach($e in $events){
    $d = Get-EventDate $e
    if($d -and ($latest -eq "" -or $d -gt $latest)){ $latest = $d }
  }
  if(-not $latest){ continue }

  $targetDate = if($StrictToday){ $today } else { $latest }

  $dayEvents = @()
  foreach($e in $events){
    if((Get-EventDate $e) -eq $targetDate){ $dayEvents += $e }
  }
  if($dayEvents.Count -eq 0){ continue }

  # Fail-closed: skip degenerate_constant_metrics tagged days
  $deg=$false
  foreach($e in $dayEvents){
    try{
      $props = $e.PSObject.Properties.Name
      if($props -contains "notes"){
        $n = (TryS $e.notes)
        if($n -match "degenerate_constant_metrics"){ $deg=$true; break }
      }
    } catch {}
  }
  if($deg){
    Write-Host ("GateScore PnL summary: FAIL-CLOSED {0} degenerate_constant_metrics for date={1} (skip row)" -f $sym,$targetDate) -ForegroundColor Yellow
    continue
  }

  $edgeVals=@()
  $microVals=@()
  $pnlVals=@()

  foreach($e in $dayEvents){
    $props = $e.PSObject.Properties.Name
    $edge  = $null
    $micro = $null
    $pnl   = $null

    foreach($k in @("edge_ratio","mean_edge_ratio","edge","ev_edge_ratio")){
      if($props -contains $k){ $edge = TryD $e.$k; break }
    }
    foreach($k in @("micro_score","mean_micro_score","micro","micro_score_today")){
      if($props -contains $k){ $micro = TryD $e.$k; break }
    }
    foreach($k in @("realized_pnl","pnl","net_pnl","pnl_usd")){
      if($props -contains $k){ $pnl = TryD $e.$k; break }
    }

    if($null -ne $edge){  $edgeVals += $edge }
    if($null -ne $micro){ $microVals += $micro }
    if($null -ne $pnl){   $pnlVals += $pnl }
  }

  $pnlSamples = [int]$pnlVals.Count
  if($pnlSamples -le 0){
    $pnlSamples = Get-PnlSamples $dayEvents
  }
  if($pnlSamples -le 0){ $pnlSamples = [int]$dayEvents.Count }

  $rowsOut += [pscustomobject]@{
    as_of_date       = $targetDate
    symbol           = $sym
    count_signals    = [int]$dayEvents.Count
    pnl_samples      = [int]$pnlSamples
    mean_edge_ratio  = [double](Mean $edgeVals)
    mean_micro_score = [double](Mean $microVals)
    mean_pnl         = [double](Mean $pnlVals)
  }
}

if(-not $rowsOut -or $rowsOut.Count -eq 0){
  Write-Error "GateScore PnL summary: no usable events found (fail-closed)."
  exit 2
}

Write-Host "GateScore PnL summary: writing $outPath" -ForegroundColor Cyan
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$csv = $rowsOut | Sort-Object symbol | ConvertTo-Csv -NoTypeInformation
[System.IO.File]::WriteAllLines($outPath, $csv, $utf8NoBom)

Write-Host "GateScore PnL summary: sample rows:" -ForegroundColor Yellow
$rowsOut | Format-Table -AutoSize
exit 0
