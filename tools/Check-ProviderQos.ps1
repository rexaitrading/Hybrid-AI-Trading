[CmdletBinding()]
param(
  [Parameter(Mandatory=$false)][int]$MaxFreshnessMsRealtime = 3000,
  [Parameter(Mandatory=$false)][double]$MaxErrorRate1m = 0.02,
  [Parameter(Mandatory=$false)][int]$MaxLatencyMsP95 = 500,
  [Parameter(Mandatory=$false)][switch]$Quiet
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
$logPath = Join-Path $repoRoot "logs\provider_qos.jsonl"

function Info([string]$m){ if(-not $Quiet){ Write-Host $m } }
function Fail([string]$m){ Write-Host $m -ForegroundColor Red; exit 2 }

if(-not (Test-Path -LiteralPath $logPath)){
  Fail "PROVIDER_QOS_MISSING: $logPath"
}

# Read last 200 lines max (fast)
  $lines = @(Get-Content -LiteralPath $logPath -Tail 200 -Encoding utf8)
if($lines.Count -eq 0){ Fail "PROVIDER_QOS_EMPTY: $logPath" }

$bad = @()
foreach($ln in $lines){
  if([string]::IsNullOrWhiteSpace($ln)){ continue }
  $j = $ln | ConvertFrom-Json
  if(($j.channel + "") -eq "realtime"){
    if([int]$j.freshness_ms -gt $MaxFreshnessMsRealtime){ $bad += "freshness_ms>$MaxFreshnessMsRealtime provider=$($j.provider) sym=$($j.symbol)" }
    if([double]$j.error_rate_1m -gt $MaxErrorRate1m){ $bad += "error_rate_1m>$MaxErrorRate1m provider=$($j.provider) sym=$($j.symbol)" }
    if([int]$j.latency_ms_p95 -gt $MaxLatencyMsP95){ $bad += "latency_ms_p95>$MaxLatencyMsP95 provider=$($j.provider) sym=$($j.symbol)" }
    if(-not [bool]$j.ok){ $bad += "ok=false provider=$($j.provider) sym=$($j.symbol)" }
  }
}

if($bad.Count -gt 0){
  Fail ("PROVIDER_QOS_NOT_OK: " + ($bad -join "; "))
}

Info "PROVIDER_QOS_OK=1"
exit 0