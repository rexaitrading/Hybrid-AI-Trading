[CmdletBinding()]
param(
  [string]$LogsRoot = ".\logs",
  [string]$OutPath = ".\logs\execution\slippage_attribution.jsonl"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

function Write-Utf8NoBomLf([string]$Path,[string]$Text){
  $enc = New-Object System.Text.UTF8Encoding($false)
  $norm = ($Text -replace "`r`n","`n")
  [System.IO.File]::WriteAllText($Path,$norm,$enc)
}

function Read-JsonLine([string]$line){
  try { return ($line | ConvertFrom-Json -ErrorAction Stop) } catch { return $null }
}

function Load-RegimeIndex([string]$logsRoot){
  # market -> regime_status object (best-effort)
  $idx = @{}
  $mkts = @("US","HK","JP","SG","IN","KR","TW")
  foreach($m in $mkts){
    $p = Join-Path $logsRoot (Join-Path $m "regime_status.json")
    if(Test-Path -LiteralPath $p){
      try{
        $o = Get-Content -LiteralPath $p -Raw -Encoding UTF8 | ConvertFrom-Json
        $idx[$m] = $o
      } catch {}
    }
  }
  return $idx
}

function Bucket-TimeOfDay([datetime]$dt){
  $h = $dt.Hour
  if($h -ge 0 -and $h -lt 8){ return "asia_overnight" }
  if($h -ge 8 -and $h -lt 14){ return "eu_mid" }
  if($h -ge 14 -and $h -lt 22){ return "us_rth" }
  return "us_afterhours"
}

function Bucket-Liquidity([double]$slipBps){
  $a = [Math]::Abs($slipBps)
  if($a -lt 2.0){ return "A_tight" }
  if($a -lt 8.0){ return "B_normal" }
  if($a -lt 25.0){ return "C_wide" }
  return "D_cliff"
}

function ReasonTag([string]$side,[double]$slipBps,[hashtable]$extra){
  $a = [Math]::Abs($slipBps)
  if($a -ge 50.0){ return "volatility_spike" }
  # heuristic: buys with positive slip or sells with negative slip often reflect spread/urgency
  if(($side -eq "BUY" -and $slipBps -gt 0) -or ($side -eq "SELL" -and $slipBps -lt 0)){
    if($a -ge 10.0){ return "spread_widen" }
  }
  return "momentum_or_noise"
}

$logsRootFull = [System.IO.Path]::GetFullPath($LogsRoot)
$outFull = [System.IO.Path]::GetFullPath($OutPath)
$outDir = Split-Path -Parent $outFull
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$regIdx = Load-RegimeIndex $logsRootFull

# discover slippage_events.jsonl under logs/**/execution/
$files = Get-ChildItem -LiteralPath $logsRootFull -Recurse -File -Filter "slippage_events.jsonl" -ErrorAction SilentlyContinue
if(-not $files -or $files.Count -eq 0){
  throw "[FAIL-CLOSED] no slippage_events.jsonl found under logs"
}

$rows = New-Object System.Collections.Generic.List[string]

foreach($fi in ($files | Sort-Object FullName)){
  $market = ""
  try{
    # infer market from path: logs\<MKT>\execution\slippage_events.jsonl OR logs\execution\slippage_events.jsonl
    $rel = $fi.FullName.Substring($logsRootFull.Length).TrimStart("\","/")
    $parts = $rel -split "[\\/]"
    if($parts.Length -ge 3 -and $parts[1] -eq "execution"){ $market = ($parts[0] + "").ToUpperInvariant() }
  } catch {}

  $reg = $null
  if($market -and $regIdx.ContainsKey($market)){ $reg = $regIdx[$market] }

  $lines = Get-Content -LiteralPath $fi.FullName -Encoding UTF8
  foreach($ln in $lines){
    $ev = Read-JsonLine $ln
    if(-not $ev){ continue }

    $ts = "" + $ev.ts
    $dt = $null
    try { $dt = [datetime]::Parse($ts) } catch { $dt = Get-Date }

    $side = ("" + $ev.side).ToUpperInvariant()
    $slb = 0.0
    try { $slb = [double]$ev.slip_bps } catch { $slb = 0.0 }

    $extra = @{}
    try{
      if($ev.PSObject.Properties.Name -contains "extra"){
        $extraObj = $ev.extra
        if($extraObj){
          foreach($p in $extraObj.PSObject.Properties){ $extra[$p.Name] = $p.Value }
        }
      }
    } catch {}

    $bucket_tod = Bucket-TimeOfDay $dt
    $bucket_liq = Bucket-Liquidity $slb
    $reason = ReasonTag $side $slb $extra

    $regime = ""
    $session = ""
    $reg_ok = $null
    try{
      if($reg){
        $regime = ("" + $reg.regime)
        $session = ("" + $reg.session_name)
        if($reg.PSObject.Properties.Name -contains "regime_ok_today"){ $reg_ok = [bool]$reg.regime_ok_today }
      }
    } catch {}

    $out = [ordered]@{
      ts = $ts
      market = $market
      symbol = ("" + $ev.symbol)
      side = $side
      qty = [double]$ev.qty
      expected_px = [double]$ev.expected_px
      actual_px = [double]$ev.actual_px
      slip_abs = [double]$ev.slip_abs
      slip_bps = $slb
      broker = ("" + $ev.broker)
      strategy = ("" + $ev.strategy)
      order_id = $ev.order_id
      time_bucket = $bucket_tod
      liquidity_bucket = $bucket_liq
      regime = $regime
      session = $session
      regime_ok_today = $reg_ok
      reason_tag = $reason
      reason_model = "heuristic_v1"
      extra = $extra
      source_file = $fi.FullName
    }

    $rows.Add(($out | ConvertTo-Json -Compress -Depth 6)) | Out-Null
  }
}

Write-Utf8NoBomLf -Path $outFull -Text (($rows -join "`n") + "`n")
Write-Host ("[OK] wrote " + $outFull + " lines=" + $rows.Count)