[CmdletBinding()]
param(
  [switch]$ForceOk
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

$root = (Resolve-Path ".").Path
Set-Location $root

$today = (Get-Date).ToString("yyyy-MM-dd")
$tsUtc  = (Get-Date).ToUniversalTime().ToString("o")

$logDir = Join-Path $root "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$out = Join-Path $logDir "phase5_ev_hard_veto_snapshot.json"

# FAIL-CLOSED default. Only ForceOk flips it true.
$ok = [bool]$ForceOk
$reason = if($ok){"forced_ok_for_dev"}else{"no_real_ev_hard_snapshot_yet"}

$payload = [ordered]@{
  ts_utc = $tsUtc
  as_of_date = $today
  ok_today = $ok
  reason = $reason
}
$json = $payload | ConvertTo-Json -Depth 6
[System.IO.File]::WriteAllText($out, ($json + "`n"), (New-Object System.Text.UTF8Encoding($false)))

Write-Host "[EV-HARD-SNAP] wrote $out ok=$ok today=$today" -ForegroundColor Green
exit 0
