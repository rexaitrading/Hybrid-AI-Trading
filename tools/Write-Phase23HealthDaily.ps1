[CmdletBinding()]
param(
  [switch]$Ok
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$root = (Resolve-Path ".").Path
$logs = Join-Path $root "logs"
New-Item -ItemType Directory -Force -Path $logs | Out-Null

$today = (Get-Date).ToString("yyyy-MM-dd")
$path  = Join-Path $logs "phase23_health_daily.csv"

# Fail-closed default: Ok is false unless explicitly set
$val = [bool]$Ok

if(-not (Test-Path $path)){
  "date,phase23_ok" | Out-File -LiteralPath $path -Encoding utf8
}

# Append today row (idempotent: remove existing today rows first)
$rows = Get-Content -LiteralPath $path -Encoding utf8 | Where-Object { $_ -and ($_ -notmatch "^\s*$today,") }
$rows | Out-File -LiteralPath $path -Encoding utf8 -Force
"$today,$val" | Add-Content -LiteralPath $path -Encoding utf8

Write-Host "WROTE=$path  date=$today phase23_ok=$val" -ForegroundColor Green
exit 0