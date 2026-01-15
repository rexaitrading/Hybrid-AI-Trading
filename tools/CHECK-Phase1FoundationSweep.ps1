[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

$psExe="$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"

# fs-truth repoRoot
$repoRoot=(Resolve-Path -LiteralPath ".").Path
while($repoRoot -and -not (Test-Path -LiteralPath (Join-Path $repoRoot ".git"))){ $repoRoot=Split-Path -Parent $repoRoot }
if(-not $repoRoot){ throw "[FAIL-CLOSED] repoRoot not found (.git missing)" }
Set-Location -LiteralPath $repoRoot; [System.Environment]::CurrentDirectory=$repoRoot

function Slice10([string]$d){
  $s = ([string]$d).Trim()
  if($s.Length -ge 10){ return $s.Substring(0,10) }
  return $s
}
function Get-TodayLocal([string]$Market){
  $rcRaw = (& $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File ".\tools\Resolve-RunContext.ps1" -Market $Market -Symbol NVDA | Out-String).Trim()
  $i0=$rcRaw.IndexOf("{"); $i1=$rcRaw.LastIndexOf("}")
  if($i0 -lt 0 -or $i1 -le $i0){ throw "[FAIL-CLOSED] Resolve-RunContext did not return JSON for Market=$Market" }
  $rc = ($rcRaw.Substring($i0, ($i1-$i0+1))) | ConvertFrom-Json
  return (Slice10 ([string]$rc.as_of_date))
}
function Get-LogsDir([string]$Market){
  $ld = (& $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File ".\tools\Get-MarketLogRoot.ps1" -Market $Market | Out-String).Trim()
  if(-not $ld){ $ld = Join-Path (Join-Path $repoRoot "logs") $Market }
  return $ld
}

$markets = @("US","HK","SG","JP","KR","TW")

"=== PHASE-1 FOUNDATION SWEEP (CHECK ONLY) ===" | Out-Host
("repoRoot=" + $repoRoot) | Out-Host
git --no-pager log -n 1 --oneline | Out-Host

$anyFail = $false

foreach($m in $markets){
  "================================================================" | Out-Host
  ("MARKET=" + $m) | Out-Host

  $todayLocal = Get-TodayLocal -Market $m
  $ld = Get-LogsDir -Market $m
  ("todayLocal=" + $todayLocal) | Out-Host
  ("logsDir=" + $ld) | Out-Host

  # Required Phase-1 evidence
  $pnl   = Join-Path $ld "gatescore_pnl_summary.csv"
  $daily = Join-Path $ld "gatescore_daily_summary.csv"
  $evN   = Join-Path $ld "nvda_gatescore_events.jsonl"

  $reasons = New-Object System.Collections.Generic.List[string]

  if(-not (Test-Path -LiteralPath $pnl)){   $reasons.Add("missing:gatescore_pnl_summary.csv") | Out-Null }
  if(-not (Test-Path -LiteralPath $daily)){ $reasons.Add("missing:gatescore_daily_summary.csv") | Out-Null }
  if(-not (Test-Path -LiteralPath $evN)){   $reasons.Add("missing:nvda_gatescore_events.jsonl") | Out-Null }

  # Hard proof: NVDA todayLocal row in daily
  $hit = 0
  if(Test-Path -LiteralPath $daily){
    try{
      $rows = @(Import-Csv -LiteralPath $daily)
      $hit = @($rows | Where-Object {
        ([string]$_.symbol).ToUpperInvariant() -eq "NVDA" -and
        (Slice10 ([string]$_.as_of_date)) -eq $todayLocal
      } | Measure-Object).Count
    } catch { $hit = 0 }
    ("NVDA_today_row_count=" + $hit) | Out-Host
    if($hit -lt 1){ $reasons.Add("daily_summary_missing_today_row:NVDA") | Out-Null }
  }

  # No stamp proof (true readiness/arming artifacts ONLY; exclude paperlive outputs)
  $stampHits = @()
  if(Test-Path -LiteralPath $ld){
    $stampHits = @(Get-ChildItem -LiteralPath $ld -File -ErrorAction SilentlyContinue |
      Where-Object {
        $n = $_.Name
        ($n -notmatch '(?i)paperlive') -and (
          $n -match '(?i)ready|arm|stamp' -or
          $n -match '(?i)(^|[^a-z])live([^a-z]|$)'
        )
      } |
      Select-Object -ExpandProperty Name)
  }
  if($stampHits.Count -gt 0){
    ("STAMP_HITS=" + ($stampHits -join ",")) | Out-Host
    $reasons.Add("stamp_files_present") | Out-Null
  } else {
    "STAMP_HITS=NONE" | Out-Host
  }

  if($reasons.Count -eq 0){
    "PHASE1_OK=TRUE" | Out-Host
  } else {
    $anyFail = $true
    ("PHASE1_OK=FALSE reasons=" + ($reasons -join ";")) | Out-Host
  }
}

"================================================================" | Out-Host
if($anyFail){
  throw "[FAIL-CLOSED] Phase-1 foundation sweep FAILED for at least one market."
} else {
  "PHASE1_SWEEP_OK=TRUE (all markets passed)" | Out-Host
}
