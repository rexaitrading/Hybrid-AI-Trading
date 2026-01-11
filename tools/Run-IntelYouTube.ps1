[CmdletBinding()]
param(
  [int]$HoursBack = 72,
  [int]$LimitPerFeed = 30
)

Set-StrictMode -Version Latest
# --- secrets (canonical) ---
# --- repo root bootstrap (canonical) ---
$repoRoot = & (Join-Path $PSScriptRoot "Go-RepoRoot.ps1")
if(-not $repoRoot){ throw "[INTEL] FAIL-CLOSED: Go-RepoRoot returned empty" }
$repoRoot = [System.IO.Path]::GetFullPath($repoRoot)

. (Join-Path $PSScriptRoot "Load-HatSecrets.ps1") -RepoRoot $repoRoot
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null
# $toolsDir = Split-Path -Parent $PSCommandPath   # disabled (use bootstrap repoRoot)
# $repoRoot = Split-Path -Parent $toolsDir        # disabled (use bootstrap repoRoot)
# Set-Location $repoRoot                          # disabled (use bootstrap repoRoot)
$py = Join-Path $repoRoot ".venv\Scripts\python.exe"
if(-not (Test-Path $py)){ throw "Missing venv python: $py" }
$env:PYTHONPATH = Join-Path $repoRoot "src"

$srcIntel  = Join-Path $repoRoot "src\.intel"
$logsDir   = Join-Path $repoRoot "logs"
$logsIntel = Join-Path $logsDir ".intel"
New-Item -ItemType Directory -Force -Path $srcIntel | Out-Null
New-Item -ItemType Directory -Force -Path $logsIntel | Out-Null

$feed = Join-Path $srcIntel "youtube_feed.jsonl"


# --- YT FEEDS FILE: enforce UTF-8 NO-BOM (institutional) ---
try {
  $feedsPath = Join-Path $repoRoot "src\.intel\youtube_feeds.txt"
  if(Test-Path -LiteralPath $feedsPath){
    $raw = Get-Content -LiteralPath $feedsPath -Raw -Encoding utf8
    $raw = $raw -replace "`r`n","`n"
    $raw = $raw.TrimEnd() + "`n"
    [System.IO.File]::WriteAllText($feedsPath, $raw, (New-Object System.Text.UTF8Encoding($false)))
  }
} catch { }
# --- END YT FEEDS FILE ---
$env:HAT_INTEL_HOURS_BACK = "$HoursBack"
$env:HAT_INTEL_LIMIT      = "$LimitPerFeed"


$feedsPath = Join-Path $repoRoot "src\.intel\youtube_feeds.txt"
if(Test-Path -LiteralPath $feedsPath){
  # Provide multiple aliases in case Python expects one of them
  $env:HAT_YOUTUBE_FEEDS_PATH = $feedsPath
  $env:HAT_INTEL_YOUTUBE_FEEDS_PATH = $feedsPath
  $env:YOUTUBE_FEEDS_PATH = $feedsPath
}
$ok=$false; $reason=""; $count=0
try{
  $out = & $py -m hybrid_ai_trading.intel.collectors.collect_cli youtube 2>&1
  $last = ($out | Select-Object -Last 1) + ""
  $j = $last | ConvertFrom-Json -ErrorAction Stop
  $ok = [bool]$j.ok
  $reason = ($j.reason + "")
  $count = [int]$j.count
}catch{
  $ok=$false
  $reason="ps_exception:" + ($_.Exception.Message + "")
  $count=0
}

if(Test-Path $feed){
  Copy-Item -LiteralPath $feed -Destination (Join-Path $logsIntel "youtube_feed.jsonl") -Force
  Copy-Item -LiteralPath $feed -Destination (Join-Path $logsDir  "youtube_feed.jsonl") -Force
}

$pulse = [ordered]@{
  ts_utc    = (Get-Date).ToUniversalTime().ToString("o")
  as_of_date= (Get-Date).ToString("yyyy-MM-dd")
  kind      = "intel_youtube_run"
  ok        = [bool]$ok
  added     = [int]$count
  reason    = $reason
  feed_path = $feed
} | ConvertTo-Json -Compress

$pulse | Add-Content -LiteralPath (Join-Path $logsDir "intel_feed.jsonl") -Encoding utf8

if(-not $ok){
  Write-Host "[INTEL-YT] FAIL-CLOSED (semantic): $reason" -ForegroundColor Yellow
  exit 0
}

Write-Host "[INTEL-YT] OK added=$count" -ForegroundColor Green
exit 0