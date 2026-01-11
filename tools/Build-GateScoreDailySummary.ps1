[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$logs = Join-Path $repoRoot "logs"
$src  = Join-Path $logs "gatescore_pnl_summary.csv"
$out  = Join-Path $logs "gatescore_daily_summary.csv"

function Write-Utf8NoBomLf([string]$Path,[string]$Text){
  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  $t = $Text.TrimStart([char]0xFEFF) -replace "`r`n","`n"
  if ($t.Length -gt 0 -and $t[-1] -ne "`n") { $t += "`n" }
  $full = [System.IO.Path]::GetFullPath($Path)
  $dir = Split-Path -Parent $full
  if($dir -and -not (Test-Path $dir)){ New-Item -ItemType Directory -Force -Path $dir | Out-Null }
  [System.IO.File]::WriteAllText($full, $t, $utf8NoBom)
}

# Canonical ASOF: Phase4 stamp wins; else BlockG wins; else local date
$asOf = (Get-Date).ToString("yyyy-MM-dd")
$p4 = Join-Path $logs "phase4_validation_passed.json"
if(Test-Path -LiteralPath $p4){
  try{
    $j = Get-Content -LiteralPath $p4 -Raw -Encoding utf8 | ConvertFrom-Json
    $d = (($j.as_of_date) + "").Trim()
    if($d){ $asOf = $d }
  } catch {}
}
$bg = Join-Path $logs "blockg_status_stub.json"
if(Test-Path -LiteralPath $bg){
  try{
    $b = Get-Content -LiteralPath $bg -Raw -Encoding utf8 | ConvertFrom-Json
    $d2 = (($b.as_of_date) + "").Trim()
    if($d2){ $asOf = $d2 }
  } catch {}
}

$header = "symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date"

if (-not (Test-Path -LiteralPath $src)) {
  Write-Utf8NoBomLf -Path $out -Text $header
  Write-Host "[GS-DAILY] FAIL-CLOSED: missing gatescore_pnl_summary.csv (header only)" -ForegroundColor Yellow
  exit 2
}

# BOUNDED LOAD: header + tail (fast)
# BOUNDED LOAD (FAST): stream tail lines via .NET (no Get-Content)
$first = $true
$headerLine = ""
$q = New-Object System.Collections.Generic.Queue[string]
foreach($ln in [System.IO.File]::ReadLines([System.IO.Path]::GetFullPath($src))){
  if($first){ $headerLine = $ln; $first = $false; continue }
  if($q.Count -ge 5000){ [void]$q.Dequeue() }
  $q.Enqueue($ln) | Out-Null
}
if(-not $headerLine){
  Write-Utf8NoBomLf -Path $out -Text $header
  Write-Host "[GS-DAILY] FAIL-CLOSED: empty csv file (header only)" -ForegroundColor Yellow
  exit 2
}
$rows = @((@($headerLine) + @($q.ToArray())) | ConvertFrom-Csv)
if (-not $rows -or $rows.Count -eq 0) {
  Write-Utf8NoBomLf -Path $out -Text $header
  Write-Host "[GS-DAILY] FAIL-CLOSED: zero rows in gatescore_pnl_summary.csv (header only)" -ForegroundColor Yellow
  exit 2
}

# Latest available session date (YYYY-MM-DD string sort OK)
$latestDate = ($rows | Sort-Object as_of_date -Descending | Select-Object -First 1).as_of_date
$use = @($rows | Where-Object { ($_.as_of_date + "") -eq ($latestDate + "") })

if (-not $use -or $use.Count -eq 0) {
  Write-Utf8NoBomLf -Path $out -Text $header
  Write-Host "[GS-DAILY] FAIL-CLOSED: no rows for latestDate=$latestDate (header only)" -ForegroundColor Yellow
  exit 2
}

$lines = New-Object System.Collections.Generic.List[string]
$lines.Add($header) | Out-Null

foreach ($r in ($use | Sort-Object symbol)) {
  $lines.Add(("{0},{1},{2},{3},{4},{5},{6}" -f
    $r.symbol,$r.count_signals,$r.mean_edge_ratio,$r.mean_micro_score,$r.pnl_samples,$r.mean_pnl,$r.as_of_date
  )) | Out-Null
}

# Carry-forward row for canonical ASOF (holiday/weekend / midnight-boundary safe)
if(($latestDate + "") -ne ($asOf + "")){
  foreach ($r in ($use | Sort-Object symbol)) {
    $lines.Add(("{0},{1},{2},{3},{4},{5},{6}" -f
      $r.symbol,$r.count_signals,$r.mean_edge_ratio,$r.mean_micro_score,$r.pnl_samples,$r.mean_pnl,$asOf
    )) | Out-Null
  }
}

Write-Utf8NoBomLf -Path $out -Text ($lines -join "`n")
Write-Host "[GS-DAILY] OK wrote $out rows=$($lines.Count-1) latestDate=$latestDate asOf=$asOf" -ForegroundColor Green
exit 0