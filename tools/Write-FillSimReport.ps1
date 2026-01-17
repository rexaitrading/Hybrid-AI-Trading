[CmdletBinding()]
param(
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","HK_SH","HK_SZ")]
  [string]$Market = "US",

  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol = "NVDA",

  [ValidateSet("PAPER","PAPERLIVE","LIVE")]
  [string]$Mode = "PAPERLIVE",

  # Model knobs (deterministic)
  [int]$CancelLatencyMs = 250,
  [int]$BaseFillDelayMs = 120,
  [int]$MaxFillDelayMs  = 2500,

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
  [System.IO.File]::WriteAllText($Path, $t, (New-Object System.Text.UTF8Encoding($false)))
}
function Fail([string]$m){
  if(-not $NoConsole){ Write-Host ("[FAIL-CLOSED] " + $m) -ForegroundColor Red }
  exit 2
}
function Slice10([string]$d){
  $s = ([string]$d).Trim()
  if($s.Length -ge 10){ return $s.Substring(0,10) }
  return $s
}
function Read-JsonFromStdout([string]$raw){
  $r = (($raw + "")).Trim()
  $i0 = $r.IndexOf('{'); $i1 = $r.LastIndexOf('}')
  if($i0 -lt 0 -or $i1 -le $i0){ return $null }
  try { return ($r.Substring($i0, ($i1-$i0+1)) | ConvertFrom-Json -ErrorAction Stop) } catch { return $null }
}
function Read-JsonLines([string]$Path){
  $out = @()
  if(-not (Test-Path -LiteralPath $Path)){ return $out }
  $lines = Get-Content -LiteralPath $Path -Encoding UTF8 -ErrorAction Stop
  foreach($ln in $lines){
    $s = ($ln + "").Trim()
    if(-not $s){ continue }
    try { $out += ($s | ConvertFrom-Json -ErrorAction Stop) } catch { }
  }
  return $out
}
function ShaFrac01([string]$s){
  # deterministic pseudo-random in [0,1)
  $b = [System.Text.Encoding]::UTF8.GetBytes(($s + ""))
  $sha = [System.Security.Cryptography.SHA256]::Create()
  $h = $sha.ComputeHash($b)
  # take first 8 bytes -> UInt64
  $u = [BitConverter]::ToUInt64($h, 0)
  # divide by 2^64
  return ([double]$u) / ([Math]::Pow(2,64))
}
function ToDoubleOrNull($v){
  try {
    if($null -eq $v){ return $null }
    $s = ($v + "").Trim()
    if(-not $s){ return $null }
    return [double]$s
  } catch { return $null }
}
function ToIntOrNull($v){
  try {
    if($null -eq $v){ return $null }
    $s = ($v + "").Trim()
    if(-not $s){ return $null }
    return [int]$s
  } catch { return $null }
}

$mk = (($Market + "")).Trim().ToUpperInvariant()
$sy = (($Symbol + "")).Trim().ToUpperInvariant()
$rm = (($Mode + "")).Trim().ToUpperInvariant()
if($rm -notin @("PAPER","PAPERLIVE","LIVE")){ Fail ("invalid -Mode=" + $Mode) }

# Policy A: non-US markets only support NVDA
if($mk -ne "US" -and $sy -in @("SPY","QQQ")){
  Fail ("PolicyA symbol_not_applicable_for_market market=" + $mk + " symbol=" + $sy)
}

# Repo root
$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
try { $repoRoot = (Resolve-Path -LiteralPath $repoRoot -ErrorAction Stop).Path } catch { }
Set-Location -LiteralPath $repoRoot
[System.Environment]::CurrentDirectory = $repoRoot

$rcPath = Join-Path $toolsDir "Resolve-RunContext.ps1"
if(-not (Test-Path -LiteralPath $rcPath)){ Fail ("missing tool: " + $rcPath) }

# Resolve RunContext
$rcRaw = (& $rcPath -Market $mk -Symbol $sy 2>&1 | Out-String)
$rcObj = Read-JsonFromStdout $rcRaw
if(-not $rcObj){ Fail ("Resolve-RunContext did not return JSON market=" + $mk) }

if(-not ($rcObj.PSObject.Properties.Name -contains "logs_dir_out")){ Fail "RunContext missing logs_dir_out" }
if(-not ($rcObj.PSObject.Properties.Name -contains "as_of_date")){ Fail "RunContext missing as_of_date" }

$logsDirOut = ([string]$rcObj.logs_dir_out).Trim()
if(-not $logsDirOut){ Fail "RunContext logs_dir_out empty" }
if(-not (Test-Path -LiteralPath $logsDirOut)){ New-Item -ItemType Directory -Force -Path $logsDirOut | Out-Null }

$asOf = Slice10 ([string]$rcObj.as_of_date)
$outPath = Join-Path $logsDirOut "fill_sim_report.json"

# Candidate input files (best-effort)
$candOrders = @(
  (Join-Path $logsDirOut "nvda_phase5_paperlive_results_today.jsonl"),
  (Join-Path $logsDirOut "nvda_phase5_paperlive_results.jsonl"),
  (Join-Path $logsDirOut "nvda_gatescore_events.jsonl"),
  (Join-Path $logsDirOut "paperlive_orders.jsonl"),
  (Join-Path $logsDirOut "orders.jsonl"),
  (Join-Path $logsDirOut "paper_orders.jsonl"),
  (Join-Path $logsDirOut "order_events.jsonl"),
  (Join-Path $logsDirOut "orders_raw.jsonl")
)

$candQuotes = @(
  (Join-Path $logsDirOut "quotes.jsonl"),
  (Join-Path $logsDirOut "l1_quotes.jsonl"),
  (Join-Path $logsDirOut "book_top.jsonl"),
  (Join-Path $logsDirOut "market_quotes.jsonl")
)

$ordersPath = ($candOrders | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1)
$quotesPath = ($candQuotes | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1)

$orders = @()
$quotes = @()

if($ordersPath){ $orders = Read-JsonLines $ordersPath }
if($quotesPath){ $quotes = Read-JsonLines $quotesPath }

# Quote lookup: simplest MVP — use last quote in file as static (deterministic)
$bid = $null; $ask = $null; $mid = $null
if($quotes.Count -gt 0){
  $q = $quotes[-1]
  $bid = ToDoubleOrNull $q.bid
  $ask = ToDoubleOrNull $q.ask
  if($bid -ne $null -and $ask -ne $null -and $ask -gt 0){ $mid = ($bid + $ask) / 2.0 }
}

# If no quotes, we use per-order submit/limit/price as pseudo-mid.
$results = @()
$summary = [pscustomobject]@{
  orders_total = $orders.Count
  orders_simulated = 0
  fill_rate = 0.0
  partial_fill_rate = 0.0
  avg_slippage_bps = $null
  avg_fill_delay_ms = $null
}

$deny = @()
$ok = $true
$reason = "ok"

if($orders.Count -eq 0){
  $ok = $false
  $reason = "no_orders_found"
  $deny += "missing_orders_jsonl"
}

# Simulate
$slips = @()
$delays = @()
$filledCount = 0
$partialCount = 0

foreach($o in $orders){
  # expected fields (best-effort):
  # id/order_id, side (BUY/SELL), qty, type (MKT/LMT), limit_px, submit_px, submit_ts, cancel_ts
  $oid = ""
  if($o.PSObject.Properties.Name -contains "order_id"){ $oid = [string]$o.order_id }
  elseif($o.PSObject.Properties.Name -contains "id"){ $oid = [string]$o.id }
  if(-not $oid){ $oid = ([Guid]::NewGuid().ToString("N")) } # deterministic not required for missing id; but rare

  $side = ""
  if($o.PSObject.Properties.Name -contains "side"){ $side = ([string]$o.side).ToUpperInvariant() }
  $qty = 0
  if($o.PSObject.Properties.Name -contains "qty"){ $qty = [int]$o.qty }
  elseif($o.PSObject.Properties.Name -contains "quantity"){ $qty = [int]$o.quantity }
  if($qty -le 0){ continue }

  $limitPx = $null
  if($o.PSObject.Properties.Name -contains "limit_px"){ $limitPx = ToDoubleOrNull $o.limit_px }
  elseif($o.PSObject.Properties.Name -contains "limitPrice"){ $limitPx = ToDoubleOrNull $o.limitPrice }

  $submitPx = $null
  if($o.PSObject.Properties.Name -contains "submit_px"){ $submitPx = ToDoubleOrNull $o.submit_px }
  elseif($o.PSObject.Properties.Name -contains "price"){ $submitPx = ToDoubleOrNull $o.price }

  # Determine reference mid
  $refMid = $mid
  if($refMid -eq $null){
    if($submitPx -ne $null){ $refMid = $submitPx }
    elseif($limitPx -ne $null){ $refMid = $limitPx }
    else { $refMid = 0.0 }
  }

  # Spread model: if bid/ask known, use them, else assume spread = 2 bps of mid (min tick-ish)
  $refBid = $bid
  $refAsk = $ask
  if($refBid -eq $null -or $refAsk -eq $null -or $refAsk -le $refBid){
    $spr = [Math]::Max(0.01, $refMid * 0.0002) # 2 bps
    $refBid = $refMid - ($spr/2.0)
    $refAsk = $refMid + ($spr/2.0)
  }

  # Queue position percentile
  $qpos = ShaFrac01 ($mk + "|" + $sy + "|" + $oid) # 0..1
  $fillDelay = [int]([Math]::Round($BaseFillDelayMs + ($MaxFillDelayMs - $BaseFillDelayMs) * $qpos))

  # Cancel window
  $cancelTs = $null
  if($o.PSObject.Properties.Name -contains "cancel_ts"){ $cancelTs = [string]$o.cancel_ts }
  $cancelEffectiveMs = $null
  if($cancelTs){
    # If cancel exists, allow only partial fill proportionally (MVP)
    $cancelEffectiveMs = $fillDelay - 1 + $CancelLatencyMs
  }

  # Fill probability and partials (deterministic)
  $pFill = 1.0 - (0.55 * $qpos) # worse queue -> lower fill
  if($rm -eq "LIVE"){ $pFill = [Math]::Min(1.0, $pFill * 0.9) }

  $u = ShaFrac01 ("p|" + $oid)
  $fillQty = 0
  if($u -le $pFill){
    # partial amount: 40%..100% based on another hash
    $u2 = ShaFrac01 ("q|" + $oid)
    $frac = 0.4 + 0.6 * $u2
    $fillQty = [int][Math]::Max(1, [Math]::Floor($qty * $frac))
    if($fillQty -gt $qty){ $fillQty = $qty }
  }

  # If cancel effective is "too soon", reduce further (MVP)
  if($cancelEffectiveMs -ne $null -and $fillQty -gt 0){
    $fillQty = [int][Math]::Max(0, [Math]::Floor($fillQty * 0.5))
  }

  # Price model: market crosses half spread + extra impact proportional to qpos
  $impact = ($refAsk - $refBid) * (0.5 + 0.75*$qpos)
  $fillPx = $refMid
  if($side -eq "BUY"){ $fillPx = $refMid + $impact }
  elseif($side -eq "SELL"){ $fillPx = $refMid - $impact }

  # Respect limit orders (MVP)
  if($limitPx -ne $null -and $fillQty -gt 0){
    if($side -eq "BUY" -and $fillPx -gt $limitPx){ $fillQty = 0 }
    if($side -eq "SELL" -and $fillPx -lt $limitPx){ $fillQty = 0 }
  }

  $filled = ($fillQty -gt 0)
  if($filled){ $filledCount++ }
  if($filled -and $fillQty -lt $qty){ $partialCount++ }

  $slipBps = $null
  if($refMid -gt 0 -and $filled){
    $slipBps = (($fillPx - $refMid) / $refMid) * 10000.0
    if($side -eq "SELL"){ $slipBps = (($refMid - $fillPx) / $refMid) * 10000.0 } # positive = worse
    $slips += $slipBps
    $delays += $fillDelay
  }

  $results += [pscustomobject]@{
    order_id = $oid
    side = $side
    qty = $qty
    filled_qty = $fillQty
    fill_delay_ms = $fillDelay
    ref_mid = [Math]::Round($refMid, 6)
    ref_bid = [Math]::Round($refBid, 6)
    ref_ask = [Math]::Round($refAsk, 6)
    fill_px = [Math]::Round($fillPx, 6)
    slippage_bps = if($slipBps -ne $null){ [Math]::Round($slipBps, 2) } else { $null }
    queue_pos_pct = [Math]::Round($qpos, 4)
    limit_px = $limitPx
    submit_px = $submitPx
    used_quotes = [bool]($quotes.Count -gt 0)
  }
}

$summary.orders_simulated = $results.Count
if($summary.orders_total -gt 0){
  $summary.fill_rate = [Math]::Round(($filledCount / [double]$summary.orders_total), 4)
  $summary.partial_fill_rate = [Math]::Round(($partialCount / [double]$summary.orders_total), 4)
}
if($slips.Count -gt 0){
  $summary.avg_slippage_bps = [Math]::Round((($slips | Measure-Object -Average).Average), 2)
  $summary.avg_fill_delay_ms = [int][Math]::Round((($delays | Measure-Object -Average).Average))
}

# Artifact
$artifact = [pscustomobject]@{
  ts_utc = (Get-Date).ToUniversalTime().ToString("o")
  market = $mk
  symbol = $sy
  run_mode = $rm
  as_of_date = $asOf
  logs_dir_out = $logsDirOut

  ok = $ok
  reason = $reason
  deny_reasons = @($deny)

  inputs = [pscustomobject]@{
    orders_path = [string]$ordersPath
    quotes_path = [string]$quotesPath
    quotes_count = $quotes.Count
  }

  model = [pscustomobject]@{
    cancel_latency_ms = $CancelLatencyMs
    base_fill_delay_ms = $BaseFillDelayMs
    max_fill_delay_ms = $MaxFillDelayMs
    spread_fallback_bps = 2
    deterministic = $true
  }

  summary = $summary
  results = @($results)
}

Write-Utf8NoBomLf $outPath ($artifact | ConvertTo-Json -Depth 10)

if(-not $NoConsole){
  $c = if($artifact.ok){ "Green" } else { "Red" }
  Write-Host ("[FILLSIM] wrote " + $outPath + " ok=" + $artifact.ok + " orders=" + $summary.orders_total + " sim=" + $summary.orders_simulated) -ForegroundColor $c
  if($artifact.ok -and $summary.avg_slippage_bps -ne $null){
    Write-Host ("[FILLSIM] fill_rate=" + $summary.fill_rate + " avg_slip_bps=" + $summary.avg_slippage_bps + " avg_delay_ms=" + $summary.avg_fill_delay_ms) -ForegroundColor Cyan
  }
}

if($artifact.ok){ exit 0 }
exit 2
