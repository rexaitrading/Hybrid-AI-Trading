[CmdletBinding()]
param(
[string]$InputPath = ".\logs\trades.jsonl",
  [string]$OutPath   = ".\logs\nvda_phase5_paperlive_results_today.jsonl"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Utf8NoBom([string]$Path, [string]$Text) {
  $enc = New-Object System.Text.UTF8Encoding($false)
  $full = (Resolve-Path $Path -ErrorAction SilentlyContinue)
  if ($null -eq $full) {
    $dir = Split-Path -Parent $Path
    if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
    $full = (Resolve-Path (Split-Path -Parent $Path)).Path + "\" + (Split-Path -Leaf $Path)
  } else {
    $full = $full.Path
  }
  [System.IO.File]::WriteAllText($full, $Text, $enc)
}

if (-not (Test-Path -LiteralPath $InputPath)) {
  Write-Host "[NVDA-TODAY] Input not found: $InputPath" -ForegroundColor Yellow
  exit 2
}
$today = (Get-Date).ToString("yyyy-MM-dd")

# Prefer NVDA paper-live ledger for today (equities). Do NOT silently reuse prior days.
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$nvLedger = Join-Path $repoRoot ("logs\paper_live_NVDA_" + $today + ".jsonl")
if(Test-Path -LiteralPath $nvLedger){
  $InputPath = $nvLedger
} else {
  Write-Host ("[NVDA-TODAY] MISSING_TODAY_LEDGER: " + $nvLedger) -ForegroundColor Yellow
  Write-Host ("[NVDA-TODAY] FALLBACK_INPUTPATH: " + $InputPath) -ForegroundColor Yellow
  # Continue with InputPath (default trades.jsonl). Still fail-closed later if no today rows.
}
Write-Host "[NVDA-TODAY] Filtering for today=$today from $InputPath" -ForegroundColor Cyan

$keep = New-Object System.Collections.ArrayList
$lines = Get-Content -LiteralPath $InputPath -Encoding UTF8

foreach($ln in $lines){
  $s = ($ln + "").Trim()
  if(-not $s){ continue }
  if($s -notmatch '"NVDA"'){ continue }  # fast prefilter

  $j = $null
  try { $j = $s | ConvertFrom-Json } catch { continue }
  if($null -eq $j){ continue }

  $props = $j.PSObject.Properties.Name
  $d = $null

  # Prefer explicit as_of_date if present (authoritative local trading day)
if($props -contains "as_of_date"){
  $v = (""+$j.as_of_date).Trim()
  if($v.Length -ge 10){ $d = $v.Substring(0,10) }
}

# Else derive local date from ts_utc (handles UTC midnight crossing)
if((-not $d) -and ($props -contains "ts_utc")){
  $v = (""+$j.ts_utc).Trim()
  if($v){
    try {
      $dto = [datetimeoffset]::Parse($v)
      $d = $dto.ToLocalTime().ToString("yyyy-MM-dd")
    } catch { }
  }
}

# Else fallback legacy keys
if(-not $d){
  foreach($k in @("ts_trade","entry_ts")){
    if($props -contains $k){
      $v = (""+$j.$k).Trim()
      if($v.Length -ge 10){ $d = $v.Substring(0,10); break }
    }
  }
}

if($d -eq $today){
  # Normalize to a paperlive-results style row so downstream GateScore writer can consume it.
  # (paper_runner ledger schema has `symbols:[...]` and `ts_utc` in UTC; we enforce local as_of_date)
  $outObj = [ordered]@{
    as_of_date = $today
    symbol = "NVDA"
    source = "paper_runner"
    ts_utc = (""+$j.ts_utc).Trim()
    status = (""+$j.status).Trim()
    price_source = (""+$j.price_source).Trim()
    # minimal deterministic metrics (provider-only stubs should never arm live)
    edge_ratio = 0.0
    micro_score = 0.0
    micro_score_source = "derived"
    realized_pnl = 0.0
    count_signals = 1
    pnl_samples = 1
    notes = "from_paper_live_ledger;provider_only_stub"
  }
  $lineOut = ($outObj | ConvertTo-Json -Compress -Depth 6)
  [void]$keep.Add($lineOut)
}
}

if($keep.Count -eq 0){
  Write-Host "[NVDA-TODAY] No today rows found -> fail-closed." -ForegroundColor Yellow
  # still write empty file for determinism? we prefer not to create misleading artifacts

  # deterministic hygiene: overwrite OutPath to empty so downstream cannot read stale content
  $enc = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText((Resolve-Path $OutPath).Path, "", $enc)
    exit 2
}

$enc = New-Object System.Text.UTF8Encoding($false)
$outFull = $OutPath
if(-not [System.IO.Path]::IsPathRooted($outFull)){
  $repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
  $outFull = Join-Path $repoRoot $OutPath
}
[System.IO.File]::WriteAllLines($outFull, [string[]]$keep.ToArray([string]), $enc)
Write-Host "[NVDA-TODAY] Wrote $($keep.Count) rows to $outFull" -ForegroundColor Green
exit 0
