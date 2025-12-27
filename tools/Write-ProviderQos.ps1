[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$Provider,
  [Parameter(Mandatory=$true)][string]$Channel,
  [Parameter(Mandatory=$false)][string]$Symbol = "",
  [Parameter(Mandatory=$false)][int]$LatencyMsP50 = 0,
  [Parameter(Mandatory=$false)][int]$LatencyMsP95 = 0,
  [Parameter(Mandatory=$false)][double]$ErrorRate1m = 0.0,
  [Parameter(Mandatory=$false)][int]$FreshnessMs = 0,
  [Parameter(Mandatory=$false)][int]$ThrottleHits1m = 0,
  [Parameter(Mandatory=$false)][bool]$Ok = $true,
  [Parameter(Mandatory=$false)][string]$Notes = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
$logPath = Join-Path $repoRoot "logs\provider_qos.jsonl"

$entry = [ordered]@{
  ts_utc = (Get-Date).ToUniversalTime().ToString("o")
  provider = $Provider
  channel = $Channel
  symbol = $Symbol
  latency_ms_p50 = $LatencyMsP50
  latency_ms_p95 = $LatencyMsP95
  error_rate_1m = $ErrorRate1m
  freshness_ms = $FreshnessMs
  throttle_hits_1m = $ThrottleHits1m
  ok = [bool]$Ok
  notes = $Notes
}

$line = ($entry | ConvertTo-Json -Compress)
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
if(-not (Test-Path -LiteralPath $logPath)){
  [System.IO.File]::WriteAllText($logPath, $line + "`n", $utf8NoBom)
} else {
  [System.IO.File]::AppendAllText($logPath, $line + "`n", $utf8NoBom)
}

"QOS_WROTE=1 PATH=$logPath" | Out-Host