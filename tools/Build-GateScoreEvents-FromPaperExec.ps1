[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "NVDA",
  [ValidateSet("rewrite","append")]
  [string]$Mode = "rewrite"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
$logsDir  = Join-Path $repoRoot "logs"

function SliceDate([string]$d){
  if(-not $d){ return "" }
  if($d.Length -ge 10){ return $d.Substring(0,10) }
  return $d
}
function TryD([object]$v){
  $x = 0.0
  if($null -eq $v){ return $null }
  if([double]::TryParse([string]$v,[ref]$x)){ return [double]$x }
  return $null
}

$wanted = switch($Symbol.ToUpperInvariant()){
  "NVDA" { @("NVDA") }
  "SPY"  { @("SPY") }
  "QQQ"  { @("QQQ") }
  default { @("NVDA","SPY","QQQ") }
}

foreach($sym in $wanted){
  $inPath = Join-Path $logsDir ("{0}_phase5_paperexec_results.jsonl" -f $sym.ToLower())
  if(-not (Test-Path -LiteralPath $inPath)){
    Write-Host ("[GS-REAL] {0}: missing input {1}" -f $sym,$inPath) -ForegroundColor Yellow
    continue
  }

  $buf = New-Object System.Collections.Generic.List[string]
  foreach($ln in (Get-Content -LiteralPath $inPath -Encoding utf8)){
    $s = ($ln + "").Trim()
    if(-not $s){ continue }
    $j = $null
    try { $j = $s | ConvertFrom-Json } catch { continue }
    if($null -eq $j){ continue }

    # Determine as_of_date
    $asOf = ""
    foreach($k in @("as_of_date","date","trading_day","day","ts_utc","ts","timestamp")){
      if($j.PSObject.Properties.Name -contains $k){
        $asOf = SliceDate ([string]$j.$k)
        if($asOf){ break }
      }
    }
    if(-not $asOf){ $asOf = (Get-Date).ToString("yyyy-MM-dd") }

    # realized pnl
    $rp = $null
    foreach($k in @("realized_pnl","pnl","net_pnl","pnl_usd")){
      if($j.PSObject.Properties.Name -contains $k){
        $rp = TryD $j.$k
        break
      }
    }
    if($null -eq $rp){ continue }

    $obj = [ordered]@{
      as_of_date = $asOf
      symbol = $sym
      source = "REAL_PAPEREXEC"
      eligible = $true
      realized_pnl = [double]$rp
      pnl_samples = 1
      edge_ratio = $null
      edge_source = "missing"
      micro_score = $null
      micro_score_source = "missing"
      notes = "from_paperexec"
    }
    $buf.Add(($obj | ConvertTo-Json -Compress)) | Out-Null
  }

  if($buf.Count -eq 0){
    Write-Host ("[GS-REAL] {0}: no eligible realized_pnl rows in paperexec results" -f $sym) -ForegroundColor Yellow
    continue
  }

  $outPath = Join-Path $logsDir ("{0}_gatescore_events_real.jsonl" -f $sym.ToLower())
  $all = @()
  if($Mode -eq "append" -and (Test-Path -LiteralPath $outPath)){
    $all = @((Get-Content -LiteralPath $outPath -Encoding utf8) + $buf.ToArray())
  } else {
    $all = @($buf.ToArray())
  }

  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllLines($outPath, $all, $utf8NoBom)
  Write-Host ("[GS-REAL] {0}: wrote {1} lines -> {2}" -f $sym,$buf.Count,$outPath) -ForegroundColor Cyan
}

exit 0
