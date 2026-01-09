[CmdletBinding()]
param(
  [int]$HoursBack = 24,
  [int]$LimitTotal = 80
)

Set-StrictMode -Version Latest
# --- secrets (canonical) ---
. (Join-Path $PSScriptRoot "Load-HatSecrets.ps1")
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$py = Join-Path $repoRoot ".venv\Scripts\python.exe"
if(-not (Test-Path $py)){ throw "Missing venv python: $py" }
$env:PYTHONPATH = Join-Path $repoRoot "src"

$srcIntel  = Join-Path $repoRoot "src\.intel"
$logsDir   = Join-Path $repoRoot "logs"
$logsIntel = Join-Path $logsDir ".intel"
New-Item -ItemType Directory -Force -Path $srcIntel | Out-Null
New-Item -ItemType Directory -Force -Path $logsIntel | Out-Null

$feed = Join-Path $srcIntel "news_feed.jsonl"

# pass knobs via env to keep CLI stable
$env:HAT_INTEL_HOURS_BACK = "$HoursBack"
$env:HAT_INTEL_LIMIT      = "$LimitTotal"

$ok=$false; $reason=""; $count=0
try{
  $out = & $py -m hybrid_ai_trading.intel.collectors.collect_cli news 2>&1
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

# Mirror feed to logs for audit
if(Test-Path $feed){
  Copy-Item -LiteralPath $feed -Destination (Join-Path $logsIntel "news_feed.jsonl") -Force
  Copy-Item -LiteralPath $feed -Destination (Join-Path $logsDir  "news_feed.jsonl") -Force
}

# Always append pulse line (semantic fail-closed)
$pulse = [ordered]@{
  ts_utc    = (Get-Date).ToUniversalTime().ToString("o")
  as_of_date= (Get-Date).ToString("yyyy-MM-dd")
  kind      = "intel_news_run"
  ok        = [bool]$ok
  added     = [int]$count
  reason    = $reason
  feed_path = $feed
} | ConvertTo-Json -Compress

$pulse | Add-Content -LiteralPath (Join-Path $logsDir "intel_feed.jsonl") -Encoding utf8

if(-not $ok){
  Write-Host "[INTEL-NEWS] FAIL-CLOSED (semantic): $reason" -ForegroundColor Yellow
  exit 0
}

Write-Host "[INTEL-NEWS] OK added=$count" -ForegroundColor Green
exit 0