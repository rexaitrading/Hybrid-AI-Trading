[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

function Emit([string]$RepoRoot,[bool]$Ok,[string]$Reason){
  $today = (Get-Date).ToString("yyyy-MM-dd")
  $tsUtc = (Get-Date).ToUniversalTime().ToString("o")
  $logs  = Join-Path $RepoRoot "logs"
  New-Item -ItemType Directory -Force -Path $logs | Out-Null
  $feed = Join-Path $logs "intel_feed.jsonl"

  $obj = [ordered]@{
    ts_utc    = $tsUtc
    as_of_date= $today
    kind      = "intel_earnings_run"
    ok        = [bool]$Ok
    added     = 0
    reason    = ($Reason + "")
    feed_path = ""
  }

  $line = ($obj | ConvertTo-Json -Compress -Depth 6)
  Add-Content -LiteralPath $feed -Encoding utf8 -Value $line
}

$repoRoot = & (Join-Path $PSScriptRoot "Go-RepoRoot.ps1")
if(-not $repoRoot){ throw "[INTEL-EARN] FAIL-CLOSED: Go-RepoRoot returned empty" }
$repoRoot = [System.IO.Path]::GetFullPath($repoRoot)

. (Join-Path $repoRoot "tools\Load-HatSecrets.ps1")

# TODO: Implement real earnings collector (eg. provider API) -> write normalized JSONL feed
# For now: explicit FAIL-CLOSED so "perfect coverage" cannot be claimed.
Emit -RepoRoot $repoRoot -Ok $false -Reason "missing_real_earnings_collector_implement_me"
Write-Host "[INTEL-EARN] FAIL-CLOSED: missing implementation (pulse emitted ok=false)" -ForegroundColor Yellow
exit 2
