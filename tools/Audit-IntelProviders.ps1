[CmdletBinding()]
param(
  [string]$AsOfDate = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null

function Fail([string]$m){ Write-Host ("[INTEL-AUDIT] FAIL-CLOSED: " + $m) -ForegroundColor Red; exit 2 }
function Ok([string]$m){ Write-Host ("[INTEL-AUDIT] OK: " + $m) -ForegroundColor Green }

$repoRoot = & (Join-Path $PSScriptRoot "Go-RepoRoot.ps1")
if(-not $repoRoot){ Fail "Go-RepoRoot returned empty" }
$repoRoot = [System.IO.Path]::GetFullPath($repoRoot)

$today = if($AsOfDate){ $AsOfDate } else { (Get-Date).ToString("yyyy-MM-dd") }
$feed  = Join-Path $repoRoot "logs\intel_feed.jsonl"
if(-not (Test-Path -LiteralPath $feed)){ Fail ("Missing " + $feed) }

# Required providers for "perfect coverage"
$requiredKinds = @(
  "intel_news_run",
  "intel_youtube_run",
  "intel_earnings_run"
)

# Read last ~5000 lines, pick latest per kind for TODAY
$latest = @{}
$lines = @(Get-Content -LiteralPath $feed -Encoding utf8)
$tail  = $lines | Select-Object -Last ([Math]::Min(5000, $lines.Count))

foreach($ln in $tail){
  $s = ($ln + "").Trim(); if(-not $s){ continue }
  try {
    $j = $s | ConvertFrom-Json
    $k = (($j.kind + "")).Trim()
    $d = (($j.as_of_date + "")).Trim()
    if(($k) -and ($d -eq $today)){
      $latest[$k] = $j
    }
  } catch { }
}

$missing = @()
$bad     = @()

foreach($k in $requiredKinds){
  if(-not $latest.ContainsKey($k)){
    $missing += $k
    continue
  }
  $j = $latest[$k]
  $ok = $false
  if($j.PSObject.Properties.Name -contains "ok"){ $ok = [bool]$j.ok }
  if(-not $ok){
    $reason = ""
    if($j.PSObject.Properties.Name -contains "reason"){ $reason = ($j.reason + "") }
    $bad += ("{0} ok=false reason={1}" -f $k,$reason)
  }
}

if($missing.Count -gt 0){ Fail ("Missing today pulses: " + ($missing -join ", ")) }
if($bad.Count -gt 0){ Fail ("Provider failures: " + ($bad -join " | ")) }

Ok ("All required providers OK for today=" + $today)
exit 0
