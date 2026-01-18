[CmdletBinding()]
param(
  [string]$InPath = ".\logs\execution\slippage_events.jsonl",
  [string]$OutJson = ".\logs\execution\slippage_attrib_daily.json",
  [string]$OutCsv  = ".\logs\execution\slippage_attrib_daily.csv",
  [int]$MaxLines = 200000,
  [switch]$NoConsole
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

try {
  $utf8 = New-Object System.Text.UTF8Encoding($false)
  [Console]::OutputEncoding = $utf8
  [Console]::InputEncoding  = $utf8
  $global:OutputEncoding    = $utf8
} catch { }

function Write-Utf8NoBomLf([string]$Path,[string]$Text){
  $t = ($Text -replace "`r`n","`n" -replace "`r","`n")
  if($t.Length -eq 0 -or $t[-1] -ne "`n"){ $t += "`n" }
  $parent = Split-Path -Parent $Path
  if($parent){ New-Item -ItemType Directory -Force -Path $parent | Out-Null }
  [System.IO.File]::WriteAllText($Path, $t, (New-Object System.Text.UTF8Encoding($false)))
}
function Read-LinesBounded([string]$Path,[int]$Limit){
  if(-not (Test-Path -LiteralPath $Path)){ return @() }
  $lines = @(Get-Content -LiteralPath $Path -Encoding UTF8 -ErrorAction Stop)
  if($Limit -gt 0 -and $lines.Count -gt $Limit){
    # keep tail (most recent)
    return @($lines[($lines.Count-$Limit)..($lines.Count-1)])
  }
  return $lines
}
function ToDoubleOrNull($v){
  try {
    if($null -eq $v){ return $null }
    if($v -is [double] -or $v -is [single] -or $v -is [decimal] -or $v -is [int] -or $v -is [long]){
      return [double]$v
    }
    $s = (($v + "")).Trim()
    if(-not $s){ return $null }
    return [double]::Parse($s, [System.Globalization.CultureInfo]::InvariantCulture)
  } catch { return $null }
}
function Quantile([double[]]$arr,[double]$q){
  if(-not $arr -or $arr.Count -eq 0){ return $null }
  $s = @($arr | Sort-Object)
  if($s.Count -eq 1){ return $s[0] }
  $pos = ($s.Count - 1) * $q
  $lo = [int][Math]::Floor($pos)
  $hi = [int][Math]::Ceiling($pos)
  if($lo -eq $hi){ return $s[$lo] }
  $w = $pos - $lo
  return ($s[$lo] * (1.0 - $w)) + ($s[$hi] * $w)
}
function StatPack([object[]]$rows){
  $bps = @()
  $abs = @()
  foreach($r in $rows){
    $b = ToDoubleOrNull $r.slip_bps
    if($null -ne $b){ $bps += $b }
    $a = ToDoubleOrNull $r.slip_abs
    if($null -ne $a){ $abs += $a }
  }
  $out = [ordered]@{
    n = $rows.Count
    slip_bps_mean = $null
    slip_bps_median = $null
    slip_bps_p95 = $null
    slip_bps_max = $null
    slip_abs_mean = $null
    slip_abs_median = $null
  }
  if($bps.Count -gt 0){
    $out.slip_bps_mean = [Math]::Round((($bps | Measure-Object -Average).Average), 6)
    $out.slip_bps_median = [Math]::Round((Quantile $bps 0.5), 6)
    $out.slip_bps_p95 = [Math]::Round((Quantile $bps 0.95), 6)
    $out.slip_bps_max = [Math]::Round((($bps | Measure-Object -Maximum).Maximum), 6)
  }
  if($abs.Count -gt 0){
    $out.slip_abs_mean = [Math]::Round((($abs | Measure-Object -Average).Average), 6)
    $out.slip_abs_median = [Math]::Round((Quantile $abs 0.5), 6)
  }
  return $out
}

# Resolve absolute paths
$inAbs = $InPath; if(-not [System.IO.Path]::IsPathRooted($inAbs)){ $inAbs = Join-Path (Get-Location).Path $inAbs }
$outJsonAbs = $OutJson; if(-not [System.IO.Path]::IsPathRooted($outJsonAbs)){ $outJsonAbs = Join-Path (Get-Location).Path $outJsonAbs }
$outCsvAbs  = $OutCsv;  if(-not [System.IO.Path]::IsPathRooted($outCsvAbs)){  $outCsvAbs  = Join-Path (Get-Location).Path $outCsvAbs }

$rawLines = Read-LinesBounded -Path $inAbs -Limit $MaxLines

$rows = @()
$bad = 0
foreach($ln in $rawLines){
  $s = ($ln + "").Trim()
  if(-not $s){ continue }
  try {
    $o = $s | ConvertFrom-Json -ErrorAction Stop
    # Extract hour_utc from ts (best-effort). If parse fails, set null.
    $hour = $null
    try {
      $dt = [DateTimeOffset]::Parse(($o.ts + ""), [System.Globalization.CultureInfo]::InvariantCulture)
      $hour = [int]$dt.UtcDateTime.Hour
    } catch { $hour = $null }

    $rows += [pscustomobject]@{
      ts = ($o.ts + "")
      hour_utc = $hour
      symbol = (($o.symbol + "")).ToUpperInvariant()
      side = (($o.side + "")).ToUpperInvariant()
      slip_bps = ToDoubleOrNull $o.slip_bps
      slip_abs = ToDoubleOrNull $o.slip_abs
      expected_px = ToDoubleOrNull $o.expected_px
      actual_px = ToDoubleOrNull $o.actual_px
      broker = ($o.broker + "")
      strategy = ($o.strategy + "")
      order_id = ($o.order_id + "")
    }
  } catch {
    $bad += 1
  }
}

$nowUtc = (Get-Date).ToUniversalTime().ToString("o")

$out = [ordered]@{
  ts_utc = $nowUtc
  in_path = $inAbs
  out_json = $outJsonAbs
  out_csv = $outCsvAbs
  parsed = $rows.Count
  bad_lines = $bad
  note = $null
  overall = $null
  by_hour_utc = @()
  by_symbol = @()
  by_symbol_side = @()
}

if($rows.Count -eq 0){
  $out.note = "no slippage events found"
  $out.overall = (StatPack @())
  Write-Utf8NoBomLf -Path $outJsonAbs -Text ($out | ConvertTo-Json -Depth 10)

  $csv = "bucket_type,bucket_key,n,slip_bps_mean,slip_bps_median,slip_bps_p95,slip_bps_max,slip_abs_mean,slip_abs_median`n"
  Write-Utf8NoBomLf -Path $outCsvAbs -Text $csv

  if(-not $NoConsole){
    Write-Host "[SLIPATTR] samples=0 (no slippage events found)"
  }
  exit 0
}

$out.overall = (StatPack $rows)

# group by hour_utc (skip null hour)
$hours = $rows | Where-Object { $null -ne $_.hour_utc } | Group-Object hour_utc
foreach($g in $hours){
  $k = [string]$g.Name
  $out.by_hour_utc += [ordered]@{ hour_utc = [int]$g.Name; stats = (StatPack $g.Group) }
}

# group by symbol
$syms = $rows | Group-Object symbol
foreach($g in $syms){
  $out.by_symbol += [ordered]@{ symbol = [string]$g.Name; stats = (StatPack $g.Group) }
}

# group by symbol+side
$ss = $rows | Group-Object { $_.symbol + "|" + $_.side }
foreach($g in $ss){
  $parts = ([string]$g.Name).Split("|")
  $out.by_symbol_side += [ordered]@{ symbol = $parts[0]; side = $parts[1]; stats = (StatPack $g.Group) }
}

# Write JSON
Write-Utf8NoBomLf -Path $outJsonAbs -Text ($out | ConvertTo-Json -Depth 12)

# Write CSV (flat)
$csvLines = @()
$csvLines += "bucket_type,bucket_key,n,slip_bps_mean,slip_bps_median,slip_bps_p95,slip_bps_max,slip_abs_mean,slip_abs_median"

function AddCsv([string]$type,[string]$key,[hashtable]$stats){
  $vals = @(
    $type,
    $key,
    $stats.n,
    $stats.slip_bps_mean,
    $stats.slip_bps_median,
    $stats.slip_bps_p95,
    $stats.slip_bps_max,
    $stats.slip_abs_mean,
    $stats.slip_abs_median
  )
  $csvLines += ($vals -join ",")
}

AddCsv -type "overall" -key "all" -stats $out.overall

foreach($x in $out.by_hour_utc){
  AddCsv -type "hour_utc" -key ([string]$x.hour_utc) -stats $x.stats
}
foreach($x in $out.by_symbol){
  AddCsv -type "symbol" -key ([string]$x.symbol) -stats $x.stats
}
foreach($x in $out.by_symbol_side){
  AddCsv -type "symbol_side" -key ([string]($x.symbol + "|" + $x.side)) -stats $x.stats
}

Write-Utf8NoBomLf -Path $outCsvAbs -Text (($csvLines -join "`n") + "`n")

if(-not $NoConsole){
  Write-Host ("[SLIPATTR] samples=" + $rows.Count + " bad_lines=" + $bad)
  Write-Host ("[SLIPATTR] overall median_bps=" + $out.overall.slip_bps_median + " p95_bps=" + $out.overall.slip_bps_p95 + " max_bps=" + $out.overall.slip_bps_max)
}
