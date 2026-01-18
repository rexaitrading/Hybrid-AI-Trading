[CmdletBinding()]
param(
  [string]$InputPath = ".\logs\nvda_phase5_paperlive_results.jsonl",
  [string]$OutPath   = ".\logs\nvda_phase5_paperlive_results_today.jsonl",

  [ValidateSet("US","JP","HK","SG","IN","KR","TW")]
  [string]$Market = ((($env:HAT_MARKET + "")).Trim().ToUpperInvariant()),

  [string]$AsOfDate = ((($env:HAT_ASOF_DATE + "")).Trim())
)


Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# --- MARKET-FIRST INPUT/OUTPUT (env-first; fail-closed for non-US) ---
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
if(-not $Market){ $Market = "US" }
$Market = ($Market + "").Trim().ToUpperInvariant()

$logsRoot = Join-Path $repoRoot "logs"
$logsMkt  = Join-Path $logsRoot $Market
$inMkt    = Join-Path $logsMkt "nvda_phase5_paperlive_results.jsonl"
$outMkt   = Join-Path $logsMkt "nvda_phase5_paperlive_results_today.jsonl"

$todayMkt = Join-Path $logsMkt "nvda_phase5_paperlive_results_today.jsonl"

# Prefer TODAY input when present (canonical can be stale per market).
# If caller left default/global input OR points to canonical, use today file.
if(Test-Path -LiteralPath $todayMkt){
  if($InputPath -eq ".\logs\nvda_phase5_paperlive_results.jsonl" -or $InputPath -eq $inMkt){
    $InputPath = $todayMkt
  }
}

# Prefer market-scoped input when caller left default + file exists
if($InputPath -eq ".\logs\nvda_phase5_paperlive_results.jsonl" -and (Test-Path -LiteralPath $inMkt)){
  $InputPath = $inMkt
}
# Default output to market-scoped when caller left default
if($OutPath -eq ".\logs\nvda_phase5_paperlive_results_today.jsonl"){
  $OutPath = $outMkt
}


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

$today = (($AsOfDate + "")).Trim()
if($today){
  if($today.Length -ge 10){ $today = $today.Substring(0,10) }
  if($today -notmatch '^\d{4}-\d{2}-\d{2}$'){ throw "[FAIL-CLOSED] AsOfDate not yyyy-MM-dd: '$today'" }
}else{
  if($Market -ne "US"){ throw "[FAIL-CLOSED] missing AsOfDate for Market=$Market (set env:HAT_ASOF_DATE)" }
  $today = (Get-Date).ToString("yyyy-MM-dd")
}
Write-Host "[NVDA-TODAY] Filtering for today=$today from $InputPath" -ForegroundColor Cyan

$keep = New-Object System.Collections.ArrayList
$lines = Get-Content -LiteralPath $InputPath -Encoding UTF8

foreach($ln in $lines){
  $s = ($ln + "").Trim()
  if(-not $s){ continue }
  $j = $null
  try { $j = $s | ConvertFrom-Json } catch { continue }
  if($null -eq $j){ continue }

  $props = $j.PSObject.Properties.Name
  $d = $null

  # Prefer explicit as_of_date when present (market-day truth).
  if($props -contains "as_of_date"){
    $ad = ((($j.as_of_date) + "")).Trim()
    if($ad.Length -ge 10){
      $ad = $ad.Substring(0,10)
      if($ad -match '^\d{4}-\d{2}-\d{2}$'){ $d = $ad }
    }
  }


  if($null -eq $d){
  foreach($k in @("ts_trade","entry_ts","ts_utc")){
    if($props -contains $k){
      $v = (($j.$k) + "").Trim()
      if($v.Length -ge 10){ $d = $v.Substring(0,10); break }
    }
  }
  }

  if($d -eq $today){
    [void]$keep.Add($s)
  }
}

if($keep.Count -eq 0){
  Write-Host "[NVDA-TODAY] No today rows found -> fail-closed." -ForegroundColor Yellow
  # still write empty file for determinism? we prefer not to create misleading artifacts
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
