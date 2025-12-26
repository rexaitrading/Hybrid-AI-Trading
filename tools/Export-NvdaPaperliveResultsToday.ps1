[CmdletBinding()]
param(
  [string]$InputPath = ".\logs\nvda_phase5_paperlive_results.jsonl",
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

  foreach($k in @("ts_trade","entry_ts","ts_utc")){
    if($props -contains $k){
      $v = (($j.$k) + "").Trim()
      if($v.Length -ge 10){ $d = $v.Substring(0,10); break }
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
