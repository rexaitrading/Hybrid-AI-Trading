[CmdletBinding()]
param([switch]$Ok)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$root = (Resolve-Path ".").Path
$logs = Join-Path $root "logs"
New-Item -ItemType Directory -Force -Path $logs | Out-Null

$today = (Get-Date).ToString("yyyy-MM-dd")
$ts = (Get-Date).ToUniversalTime().ToString("s") + "Z"

$obj = [ordered]@{
  ts_utc = $ts
  as_of_date = $today
  phase4_ok_today = [bool]$Ok
}

$path = Join-Path $logs "phase4_validation_passed.json"
$obj | ConvertTo-Json -Depth 5 | Out-File -LiteralPath $path -Encoding utf8 -Force

Write-Host "WROTE=$path phase4_ok_today=$($obj.phase4_ok_today) as_of_date=$today" -ForegroundColor Green
exit 0