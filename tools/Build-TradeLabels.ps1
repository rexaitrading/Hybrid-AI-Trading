[CmdletBinding()]
param(
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","HK_SH","HK_SZ")]
  [string]$Market = "US",

  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol = "NVDA",

  [ValidateSet("PAPER","PAPERLIVE","LIVE")]
  [string]$Mode = "PAPERLIVE"
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

function Fail([string]$m){ throw ("[FAIL-CLOSED] " + $m) }
function Write-Utf8NoBomLf([string]$Path,[string]$Text){
  $t = ($Text -replace "`r`n","`n" -replace "`r","`n")
  if($t.Length -eq 0 -or $t[-1] -ne "`n"){ $t += "`n" }
  [System.IO.File]::WriteAllText($Path, $t, (New-Object System.Text.UTF8Encoding($false)))
}
function Read-JsonLines([string]$Path){
  $out=@()
  if(-not (Test-Path -LiteralPath $Path)){ return $out }
  foreach($ln in Get-Content -LiteralPath $Path -Encoding UTF8){
    $s = ($ln + "").Trim()
    if(-not $s){ continue }
    try { $out += ($s | ConvertFrom-Json -ErrorAction Stop) } catch {}
  }
  return $out
}
function Parse-IsoDate([string]$ts){
  try {
    # accept Z or +00:00Z weirdness; take first 10 chars if iso
    $t = ($ts + "").Trim()
    if($t.Length -ge 10){ return $t.Substring(0,10) }
  } catch {}
  return ""
}

# Repo root
$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
try { $repoRoot = (Resolve-Path -LiteralPath $repoRoot -ErrorAction Stop).Path } catch {}
Set-Location -LiteralPath $repoRoot
[System.Environment]::CurrentDirectory = $repoRoot

# RunContext
$rcPath = Join-Path $toolsDir "Resolve-RunContext.ps1"
if(-not (Test-Path -LiteralPath $rcPath)){ Fail ("missing tool: " + $rcPath) }

$mk = ($Market + "").Trim().ToUpperInvariant()
$sy = ($Symbol + "").Trim().ToUpperInvariant()

$rcRaw = (& $rcPath -Market $mk -Symbol $sy 2>&1 | Out-String).Trim()
$i0 = $rcRaw.IndexOf('{'); $i1 = $rcRaw.LastIndexOf('}')
if($i0 -lt 0 -or $i1 -le $i0){ Fail ("Resolve-RunContext did not return JSON market=" + $mk) }
$rcObj = ($rcRaw.Substring($i0, ($i1-$i0+1)) | ConvertFrom-Json -ErrorAction Stop)

$logsDirOut = ([string]$rcObj.logs_dir_out).Trim()
if(-not $logsDirOut){ Fail "RunContext logs_dir_out empty" }

$outPath = Join-Path $logsDirOut "trade_labels.jsonl"
$ordersPath = Join-Path $logsDirOut "orders.jsonl"
$slipPath   = Join-Path $logsDirOut "execution\slippage_events.jsonl"
$simPath    = Join-Path $logsDirOut "fill_sim_report.json"
$regPath    = Join-Path $logsDirOut "regime_status.json"
$gsPath     = Join-Path $logsDirOut (($sy.ToLowerInvariant()) + "_gatescore_events.jsonl")

# Inputs
$orders = @(Read-JsonLines $ordersPath)
if(@($orders).Count -eq 0){ Fail ("no orders found: " + $ordersPath) }

$slips = @(Read-JsonLines $slipPath)
$sim = $null
try { if(Test-Path -LiteralPath $simPath){ $sim = (Get-Content -LiteralPath $simPath -Raw -Encoding UTF8 | ConvertFrom-Json) } } catch {}
$reg = $null
try { if(Test-Path -LiteralPath $regPath){ $reg = (Get-Content -LiteralPath $regPath -Raw -Encoding UTF8 | ConvertFrom-Json) } } catch {}
$gs = @(Read-JsonLines $gsPath)

# Helper: find best slip_bps for order by symbol + closest date match (MVP)
function Pick-SlipBps([string]$sym,[string]$day){
  $best = $null
  foreach($e in $slips){
    try{
      if((($e.symbol + "")).ToUpperInvariant() -ne $sym.ToUpperInvariant()){ continue }
      $d = Parse-IsoDate ($e.ts)
      if($d -and $day -and $d -ne $day){ continue }
      $best = [double]$e.slip_bps
    } catch {}
  }
  return $best
}

# Helper: pick last gatescore row for day
function Pick-GS([string]$sym,[string]$day){
  $best = $null
  $bestDay = ""
  foreach($e in $gs){
    try{
      if((($e.symbol + "")).ToUpperInvariant() -ne $sym.ToUpperInvariant()){ continue }
      $d = ($e.as_of_date + "")
      if(-not $d){ continue }
      # exact match preferred
      if($day -and $d -eq $day){ $best = $e; $bestDay = $d; continue }
      # fallback: pick latest <= day (string compare safe for YYYY-MM-DD)
      if($day -and ($d -le $day)){
        if(-not $bestDay -or $d -gt $bestDay){ $best = $e; $bestDay = $d }
      }
      # if no day provided, just keep last seen
      if(-not $day){ $best = $e; $bestDay = $d }
    } catch {}
  }
  return $best
}

# Entry quality: compare observed slip to sim avg_slippage_bps (MVP)
function EntryQuality([double]$slipBps, $simObj){
  if($null -eq $slipBps){ return $null }
  $base = $null
  try { $base = [double]$simObj.summary.avg_slippage_bps } catch { $base = $null }
  if($null -eq $base -or $base -le 0){ $base = 10.0 }
  $score = 1.0 - ([Math]::Abs($slipBps) / [Math]::Max(1.0, (2.0 * $base)))
  return [Math]::Round([Math]::Max(0.0, [Math]::Min(1.0, $score)), 4)
}

# Exit quality: use gatescore micro_score if available (MVP)
function ExitQuality($gsObj){
  try {
    if($gsObj -and ($gsObj.PSObject.Properties.Name -contains "micro_score")){
      return [Math]::Round([double]$gsObj.micro_score, 4)
    }
  } catch {}
  return $null
}

$rows = New-Object System.Collections.Generic.List[string]
foreach($o in $orders){
  $day = Parse-IsoDate ($o.ts_utc)
  $sym = ($o.symbol + "").ToUpperInvariant()
  $gsObj = Pick-GS $sym $day

  # Setup mapping (deterministic, no guessing): replay pipeline is ORB; REAL paperlive -> "PAPERLIVE_REAL"
  $setup = "UNKNOWN"
  try {
    if($gsObj -and ($gsObj.PSObject.Properties.Name -contains "notes") -and (($gsObj.notes + "") -like "*from_paperlive*")){ $setup = "PAPERLIVE_REAL" }
    elseif($gsObj -and ($gsObj.PSObject.Properties.Name -contains "source") -and (($gsObj.source + "") -like "*BARS_EDGE_V0*")){ $setup = "ORB_LONG_V1" }
  } catch {}

  $slipBps = Pick-SlipBps $sym $day
  $eq = EntryQuality $slipBps $sim
  $xq = ExitQuality $gsObj

  $regime = $null
  $session = $null
  try { if($reg){ $regime = ($reg.regime + ""); $session = ($reg.session_name + "") } } catch {}

  $label = [ordered]@{
    schema = "trade_label.v1"
    ts_utc = ($o.ts_utc + "")
    as_of_date = $day
    market = $mk
    symbol = $sym
    setup = $setup
    regime = $regime
    session_name = $session

    side = ($o.side + "")
    qty = [double]$o.qty
    order_type = ($o.type + "")
    submit_px = $o.submit_px
    fill_px = $o.fill_px
    slip_bps_obs = $slipBps

    entry_quality = $eq
    exit_quality = $xq

    gatescore = [ordered]@{
      missing_exact_day = ($gsObj -eq $null)
      source = $(if($gsObj -and ($gsObj.PSObject.Properties.Name -contains "source")){ ($gsObj.source + "") } else { "" })
      notes = $(if($gsObj -and ($gsObj.PSObject.Properties.Name -contains "notes")){ ($gsObj.notes + "") } else { "" })
      edge_ratio = $(if($gsObj -and ($gsObj.PSObject.Properties.Name -contains "edge_ratio")){ $gsObj.edge_ratio } else { $null })
      micro_score = $(if($gsObj -and ($gsObj.PSObject.Properties.Name -contains "micro_score")){ $gsObj.micro_score } else { $null })
      realized_pnl = $(if($gsObj -and ($gsObj.PSObject.Properties.Name -contains "realized_pnl")){ $gsObj.realized_pnl } else { $null })
    }

    inputs = [ordered]@{
      orders_jsonl = $ordersPath
      slippage_events_jsonl = $slipPath
      fill_sim_report_json = $simPath
      regime_status_json = $regPath
      gatescore_events_jsonl = $gsPath
    }
  }

  $rows.Add(($label | ConvertTo-Json -Compress -Depth 10)) | Out-Null
}

Write-Utf8NoBomLf $outPath (($rows -join "`n") + "`n")
Write-Host ("[OK] wrote " + $outPath + " lines=" + $rows.Count)
