[CmdletBinding()]
param(
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","HK_SH","HK_SZ")]
  [string]$Market = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location -LiteralPath $repoRoot
[System.Environment]::CurrentDirectory = $repoRoot

function Write-Utf8NoBomLf([string]$Path,[string]$Text){
  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  $t = ($Text + "") -replace "`r`n","`n"
  if($t.Length -gt 0 -and $t[-1] -ne "`n"){ $t += "`n" }
  $full = [System.IO.Path]::GetFullPath($Path)
  $dir = Split-Path -Parent $full
  if($dir -and -not (Test-Path -LiteralPath $dir)){ New-Item -ItemType Directory -Force -Path $dir | Out-Null }
  [System.IO.File]::WriteAllText($full, $t, $utf8NoBom)
}

function Slice10([string]$d){
  $s = ([string]$d).Trim()
  if($s.Length -ge 10){ return $s.Substring(0,10) }
  return $s
}

# ---- Market normalize (env-first) ----
$m = (($Market + "")).Trim().ToUpperInvariant()
if(-not $m){ $m = (($env:HAT_MARKET + "")).Trim().ToUpperInvariant() }
if(-not $m){ $m = "US" }
$Market = $m

# ---- Market-aware logs dir (A3) ----
$gm = Join-Path $repoRoot "tools\Get-MarketLogRoot.ps1"
# A3_GS_DAILY_SUMMARY_BEGIN
$logs = (($env:HAT_LOGS_DIR + "")).Trim()
if($env:HAT_MARKET -and (-not $logs)){ throw "[FAIL-CLOSED] HAT_MARKET set but HAT_LOGS_DIR missing (A3 wiring required)" }
if(-not $logs){ $logs = Join-Path $repoRoot "logs" }
# A3_GS_DAILY_SUMMARY_END
if(Test-Path -LiteralPath $gm){
  $ld = (& "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $gm -Market $Market | Out-String).Trim()
  if($ld){ $logs = $ld } else { $logs = Join-Path (Join-Path $repoRoot "logs") $Market }
} else {
  $logs = Join-Path (Join-Path $repoRoot "logs") $Market
}
New-Item -ItemType Directory -Force -Path $logs | Out-Null

$src = Join-Path $logs "gatescore_pnl_summary.csv"
$out = Join-Path $logs "gatescore_daily_summary.csv"

# ---- Canonical ASOF (A3 single truth) ----
# A3_GS_ASOF_BEGIN
$asOf = (($env:HAT_AS_OF_DATE + "")).Trim()
if(-not $asOf){ $asOf = (($env:HAT_ASOF_DATE + "")).Trim() }  # legacy fallback
if(-not $asOf){
  # Resolve-RunContext is authoritative
  $rcPath = Join-Path $repoRoot "tools\Resolve-RunContext.ps1"
  if(Test-Path -LiteralPath $rcPath){
    $rcRaw = (& "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $rcPath -Market $Market -Symbol NVDA | Out-String).Trim()
    $i0=$rcRaw.IndexOf("{"); $i1=$rcRaw.LastIndexOf("}")
    if($i0 -ge 0 -and $i1 -gt $i0){ $rc = ($rcRaw.Substring($i0, ($i1-$i0+1))) | ConvertFrom-Json }
    if($rc -and $rc.as_of_date){ $asOf = Slice10 ([string]$rc.as_of_date) }
  }
}
if(-not $asOf -and $env:HAT_MARKET){ throw "[FAIL-CLOSED] missing as_of_date for market context" }
if($asOf.Length -ge 10){ $asOf = $asOf.Substring(0,10) }
$env:HAT_AS_OF_DATE = $asOf
# A3_GS_ASOF_END
try{
  $rcPath = Join-Path $repoRoot "tools\Resolve-RunContext.ps1"
  if(Test-Path -LiteralPath $rcPath){
    $rcRaw = (& "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $rcPath -Market $Market -Symbol NVDA | Out-String).Trim()
    $i0 = $rcRaw.IndexOf("{"); $i1 = $rcRaw.LastIndexOf("}")
    if($i0 -ge 0 -and $i1 -gt $i0){
      $rc = ($rcRaw.Substring($i0, ($i1-$i0+1))) | ConvertFrom-Json
      if($rc -and $rc.as_of_date){
        $d = Slice10 ([string]$rc.as_of_date)
        if($d -match '^\d{4}-\d{2}-\d{2}$'){ $asOf = $d }
      }
    }
  }
} catch { }

# Optional: Phase4/BlockG can override if present (same market log root)
try{
  $p4 = Join-Path $logs "phase4_validation_passed.json"
  if(Test-Path -LiteralPath $p4){
    $j = Get-Content -LiteralPath $p4 -Raw -Encoding utf8 | ConvertFrom-Json
    $d = Slice10 (($j.as_of_date) + "")
    if($d -match '^\d{4}-\d{2}-\d{2}$'){ $asOf = $d }
  }
} catch { }
try{
  $bg = Join-Path $logs "blockg_status_stub.json"
  if(Test-Path -LiteralPath $bg){
    $b = Get-Content -LiteralPath $bg -Raw -Encoding utf8 | ConvertFrom-Json
    $d2 = Slice10 (($b.as_of_date) + "")
    if($d2 -match '^\d{4}-\d{2}-\d{2}$'){ $asOf = $d2 }
  }
} catch { }

$header = "symbol,count_signals,mean_edge_ratio,mean_micro_score,pnl_samples,mean_pnl,as_of_date"

if(-not (Test-Path -LiteralPath $src)){
  Write-Utf8NoBomLf -Path $out -Text $header
  Write-Host "[GS-DAILY] FAIL-CLOSED: missing gatescore_pnl_summary.csv (header only)" -ForegroundColor Yellow
  exit 2
}

# Fast bounded load: header + last 5000 rows
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
  Write-Host "[GS-DAILY] FAIL-CLOSED: empty gatescore_pnl_summary.csv (header only)" -ForegroundColor Yellow
  exit 2
}

$rows = @((@($headerLine) + @($q.ToArray())) | ConvertFrom-Csv)
if(-not $rows -or $rows.Count -eq 0){
  Write-Utf8NoBomLf -Path $out -Text $header
  Write-Host "[GS-DAILY] FAIL-CLOSED: zero rows in gatescore_pnl_summary.csv (header only)" -ForegroundColor Yellow
  exit 2
}

$latestDate = (($rows | Sort-Object as_of_date -Descending | Select-Object -First 1).as_of_date + "")
$use = @($rows | Where-Object { (($_.as_of_date + "")) -eq $latestDate })
if(-not $use -or $use.Count -eq 0){
  Write-Utf8NoBomLf -Path $out -Text $header
  Write-Host "[GS-DAILY] FAIL-CLOSED: no rows for latestDate=$latestDate (header only)" -ForegroundColor Yellow
  exit 2
}

$lines = New-Object System.Collections.Generic.List[string]
$lines.Add($header) | Out-Null

foreach($r in ($use | Sort-Object symbol)){
  $lines.Add(("{0},{1},{2},{3},{4},{5},{6}" -f
    $r.symbol,$r.count_signals,$r.mean_edge_ratio,$r.mean_micro_score,$r.pnl_samples,$r.mean_pnl,$r.as_of_date
  )) | Out-Null
}

# Carry-forward for canonical ASOF
if(($latestDate + "") -ne ($asOf + "")){
  foreach($r in ($use | Sort-Object symbol)){
    $lines.Add(("{0},{1},{2},{3},{4},{5},{6}" -f
      $r.symbol,$r.count_signals,$r.mean_edge_ratio,$r.mean_micro_score,$r.pnl_samples,$r.mean_pnl,$asOf
    )) | Out-Null
  }
}

Write-Utf8NoBomLf -Path $out -Text ($lines -join "`n")
Write-Host "[GS-DAILY] OK wrote $out rows=$($lines.Count-1) latestDate=$latestDate asOf=$asOf" -ForegroundColor Green
exit 0
