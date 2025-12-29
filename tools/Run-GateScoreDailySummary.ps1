[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol="ALL",
  [switch]$Quiet
)
Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$root = (Resolve-Path ".").Path
Set-Location $root

$today = (Get-Date).ToString("yyyy-MM-dd")
$tsUtc  = (Get-Date).ToUniversalTime().ToString("o")

$logDir = Join-Path $root "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$outCsv = Join-Path $logDir "gatescore_daily_summary.csv"

# Canonical schema expected by Build-BlockGStatusStub.ps1
$header = "as_of_date,symbol,count_signals,pnl_samples,mean_edge_ratio,mean_micro_score"

$syms = @("NVDA","SPY","QQQ")
if ($Symbol -ne "ALL") { $syms = @($Symbol.ToUpperInvariant()) }

# Load existing rows safely (handle missing file)
$rows = @()
if (Test-Path $outCsv) {
  try { $rows = @(Import-Csv $outCsv) } catch { $rows = @() }
} else {
  Set-Content -LiteralPath $outCsv -Encoding utf8 -Value $header
}

# Keep rows that are NOT (today + target symbol)
$kept = New-Object System.Collections.Generic.List[object]
foreach($r in $rows){
  $d = ""
  if ($r.PSObject.Properties.Name -contains "as_of_date") { $d = [string]$r.as_of_date }
  if ($d.Length -ge 10) { $d = $d.Substring(0,10) }

  $sym = ""
  if ($r.PSObject.Properties.Name -contains "symbol") { $sym = ([string]$r.symbol).ToUpperInvariant() }

  if ($d -eq $today -and ($syms -contains $sym)) { continue }

  # Normalize into canonical shape (ignore extra columns)
  $kept.Add([pscustomobject]@{
    as_of_date = $d
    symbol = $sym
    count_signals = [int]($r.count_signals -as [int])
    pnl_samples = [int]($r.pnl_samples -as [int])
    mean_edge_ratio = [double]($r.mean_edge_ratio -as [double])
    mean_micro_score = [double]($r.mean_micro_score -as [double])
  }) | Out-Null
}

function Get-TodaysMetricsFor([string]$sym,[string]$today,[string]$logDir){
  $path = Join-Path $logDir (("{0}_gatescore_events.jsonl" -f $sym.ToLowerInvariant()))
  $cnt = 0
  $pnlCnt = 0
  $edgeSum = 0.0
  $edgeN = 0
  $microSum = 0.0
  $microN = 0

  if(-not (Test-Path -LiteralPath $path)){
    return [pscustomobject]@{ count_signals=0; pnl_samples=0; mean_edge_ratio=0.0; mean_micro_score=0.0; reason="missing_events_jsonl" }
  }

  $reason = "ok"
  try{
    foreach($ln in Get-Content -LiteralPath $path -Encoding utf8){
      if([string]::IsNullOrWhiteSpace($ln)){ continue }
      $j = $null
      try { $j = $ln | ConvertFrom-Json } catch { continue }

      # Date extraction (best-effort)
      $d = ""
      foreach($k in @("as_of_date","date","session_date","ts","ts_utc","timestamp","time_utc","time")){
        if($j.PSObject.Properties.Name -contains $k){
          $d = [string]($j.$k)
          break
        }
      }
      if($d.Length -ge 10){ $d = $d.Substring(0,10) }
      if($d -ne $today){ continue }

      $cnt++

      # PnL sample extraction (best-effort)
      $pnlVal = $null
      foreach($k in @("pnl","realized_pnl","pnl_usd","pnl_realized","net_pnl","realizedPnL")){
        if($j.PSObject.Properties.Name -contains $k){
          $pnlVal = $j.$k
          break
        }
      }
      if($null -ne $pnlVal){
        $tmp = 0.0
        if([double]::TryParse([string]$pnlVal, [ref]$tmp)){ $pnlCnt++ }
      }

      # Edge ratio
      $edgeVal = $null
      foreach($k in @("edge_ratio","mean_edge_ratio","edge","edgeRatio")){
        if($j.PSObject.Properties.Name -contains $k){ $edgeVal = $j.$k; break }
      }
      if($null -ne $edgeVal){
        $tmp = 0.0
        if([double]::TryParse([string]$edgeVal, [ref]$tmp)){
          $edgeSum += $tmp; $edgeN++
        }
      }

      # Micro score
      $microVal = $null
      foreach($k in @("micro_score","mean_micro_score","micro","microScore")){
        if($j.PSObject.Properties.Name -contains $k){ $microVal = $j.$k; break }
      }
      if($null -ne $microVal){
        $tmp = 0.0
        if([double]::TryParse([string]$microVal, [ref]$tmp)){
          $microSum += $tmp; $microN++
        }
      }
    }
  } catch {
    $reason = "parse_loop_failed"
  }

  $edgeMean = 0.0
  if($edgeN -gt 0){ $edgeMean = $edgeSum / [double]$edgeN }

  $microMean = 0.0
  if($microN -gt 0){ $microMean = $microSum / [double]$microN }

  return [pscustomobject]@{
    count_signals=$cnt
    pnl_samples=$pnlCnt
    mean_edge_ratio=[double]$edgeMean
    mean_micro_score=[double]$microMean
    reason=$reason
  }
}

# Real daily metrics from per-symbol jsonl event streams (fail-closed if missing/unparseable)
foreach($sym in $syms){
  $m = Get-TodaysMetricsFor -sym $sym -today $today -logDir $logDir

  if((-not $Quiet) -and ($m.reason -ne "ok")){
    Write-Host ("[GS] WARN symbol={0} reason={1}" -f $sym, $m.reason) -ForegroundColor Yellow
  }

  $kept.Add([pscustomobject]@{
    as_of_date = $today
    symbol = $sym
    count_signals = [int]$m.count_signals
    pnl_samples = [int]$m.pnl_samples
    mean_edge_ratio = [double]$m.mean_edge_ratio
    mean_micro_score = [double]$m.mean_micro_score
  }) | Out-Null
}

# Write canonical CSV (UTF-8 no-BOM)
$lines = New-Object System.Collections.Generic.List[string]
$lines.Add($header) | Out-Null
foreach($r in $kept){
  $lines.Add(("{0},{1},{2},{3},{4},{5}" -f $r.as_of_date,$r.symbol,$r.count_signals,$r.pnl_samples,$r.mean_edge_ratio,$r.mean_micro_score)) | Out-Null
}
[System.IO.File]::WriteAllLines($outCsv, $lines, (New-Object System.Text.UTF8Encoding($false)))
if(-not $Quiet){ 
Write-Host "[GS] wrote $outCsv today=$today symbols=$($syms -join ',')" -ForegroundColor Green }
$global:LASTEXITCODE = 0; return
