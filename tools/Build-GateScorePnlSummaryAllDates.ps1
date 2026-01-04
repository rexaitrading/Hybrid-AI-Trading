[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "ALL"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
$logsDir  = Join-Path $repoRoot "logs"

$outPath = Join-Path $logsDir "gatescore_pnl_summary_all_dates.csv"

function Resolve-EventFile([string]$logsDir,[string]$sym){
  $std  = Join-Path $logsDir ("{0}_gatescore_events.jsonl" -f $sym.ToLower())
  $real = Join-Path $logsDir ("{0}_gatescore_events_real.jsonl" -f $sym.ToLower())

  # Institutional: std is canonical; real is fallback only.
  if (Test-Path -LiteralPath $std)  { return $std }
  if (Test-Path -LiteralPath $real) { return $real }
  return ""
}

function _SliceDate([string]$d){ if(-not $d){""} elseif($d.Length -ge 10){$d.Substring(0,10)} else {$d} }
function _TryDouble([object]$v){ $x=0.0; if($null -eq $v){return $null}; if([double]::TryParse([string]$v,[ref]$x)){return $x}; return $null }
function _TryString([object]$v){ if($null -eq $v){""} else {[string]$v} }

function Read-Jsonl([string]$Path){
  if(-not (Test-Path $Path)){ return @() }
  $out=@()
  foreach($ln in (Get-Content $Path -Encoding UTF8)){
    $s=$ln.Trim(); if(-not $s){continue}
    try{ $out += ($s | ConvertFrom-Json) } catch {}
  }
  return @($out)
}

function Get-EventDate($e){
  $props=$e.PSObject.Properties.Name
  foreach($k in @("as_of_date","date","trading_day")){
    if($props -contains $k){
      $v=_TryString ($e.$k); if($v){ return _SliceDate $v }
    }
  }
  foreach($k in @("ts_utc","ts","timestamp")){
    if($props -contains $k){
      $t=_TryString ($e.$k); if($t.Length -ge 10){ return $t.Substring(0,10) }
    }
  }
  return ""
}

function Mean($arr){
  if($arr.Count -eq 0){ return 0.0 }
  $sum=0.0; foreach($v in $arr){ $sum += [double]$v }
  return $sum / [double]$arr.Count
}

$eventFiles=@(
  @{ sym="NVDA"; path=(Resolve-EventFile $logsDir "NVDA") },
  @{ sym="SPY";  path=(Resolve-EventFile $logsDir "SPY")  },
  @{ sym="QQQ";  path=(Resolve-EventFile $logsDir "QQQ")  }
)

# GS_ALLDATES_PATH_AUDIT_BEGIN
foreach($t in $eventFiles){
  try {
    $p = [string]$t.path
    if($p -and (Test-Path -LiteralPath $p)){
      $sz = (Get-Item -LiteralPath $p).Length
      Write-Host ("[GS-ALLDATES] " + $t.sym + " path=" + $p + " bytes=" + $sz) -ForegroundColor Yellow
    } else {
      Write-Host ("[GS-ALLDATES] " + $t.sym + " path=MISSING") -ForegroundColor Red
    }
  } catch { }
}
# GS_ALLDATES_PATH_AUDIT_END


$wanted=@()
switch($Symbol.ToUpperInvariant()){
  "NVDA"{ $wanted=@("NVDA") }
  "SPY" { $wanted=@("SPY") }
  "QQQ" { $wanted=@("QQQ") }
  "ALL" { $wanted=@("NVDA","SPY","QQQ") }
}

$rows=@()

foreach($it in $eventFiles){
  $sym=[string]$it.sym
  if($wanted -notcontains $sym){ continue }
  $path=[string]$it.path
  if(-not (Test-Path $path)){ continue }

  $events = @(Read-Jsonl $path)

  # --- Institutional: refuse ALL-STUB canonical event files (signals not computed) ---
  $stubCount = 0
  $nonStubCount = 0
  foreach($e in $events){
    try{
      $src = ""
      if($e.PSObject.Properties.Name -contains "source"){ $src = [string]$e.source }
      if($src -eq "STUB"){ $stubCount++ } else { $nonStubCount++ }
    } catch {}
  }
  if($events.Count -gt 0 -and $nonStubCount -eq 0){
    Write-Error ("[GS-ALLDATES] " + $sym + ": event file is ALL-STUB; refusing. path=" + $path)
    exit 2
  }

  if($events.Count -eq 0){ continue }

  $byDate = @{}
  foreach($e in $events){
    $d = Get-EventDate $e
    if(-not $d){ continue }
    if(-not $byDate.ContainsKey($d)){ $byDate[$d]=@() }
    $byDate[$d] += $e
  }

  foreach($d in ($byDate.Keys | Sort-Object)){
    $es = @($byDate[$d] | Where-Object { -not ($_.PSObject.Properties.Name -contains "eligible") -or [bool]$_.eligible })
    if($es.Count -eq 0){ continue }

    $edge=@(); $micro=@(); $pnl=@()
    foreach($e in $es){
      $ev = _TryDouble $e.edge_ratio
      $mv = _TryDouble $e.micro_score
      $pv = _TryDouble ($e.realized_pnl)
      if($null -ne $ev){ $edge += $ev }
      if($null -ne $mv){ $micro += $mv }
      if($null -ne $pv){ $pnl += $pv }
    }

    $rows += [pscustomobject]@{
      as_of_date       = $d
      symbol           = $sym
      count_signals    = [int]$es.Count
      pnl_samples      = [int]($pnl.Count)
      mean_edge_ratio  = [double](Mean $edge)
      mean_micro_score = [double](Mean $micro)
      mean_pnl         = [double](Mean $pnl)
    }
  }
}

if($rows.Count -eq 0){
  Write-Error "GateScore all-dates: no usable events; refusing to write $outPath"
  exit 2
}

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$csv = $rows | Sort-Object symbol,as_of_date | ConvertTo-Csv -NoTypeInformation
[System.IO.File]::WriteAllLines($outPath, $csv, $utf8NoBom)

Write-Host "GateScore all-dates: wrote $outPath" -ForegroundColor Cyan
$rows | Select-Object -First 10 | Format-Table -AutoSize
exit 0
