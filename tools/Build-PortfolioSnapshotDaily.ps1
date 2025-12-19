[CmdletBinding()]
param()

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$logsDir = Join-Path $repoRoot "logs"
if (-not (Test-Path $logsDir)) { New-Item -ItemType Directory -Path $logsDir | Out-Null }

$today = (Get-Date).ToString("yyyy-MM-dd")

# STUB (fail-closed semantics later): write explicit fields now so Phase6/7 can require it.
$pf = [ordered]@{
  ts_utc             = (Get-Date).ToUniversalTime().ToString("o")
  as_of_date         = $today
  account_equity     = 0.0
  open_symbols       = @()
  gross_exposure_pct = 0.0
  net_exposure_pct   = 0.0
  var_95_pct         = 0.0
  portfolio_ok_today = $true
}

$json = ($pf | ConvertTo-Json -Depth 10)
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText((Join-Path $logsDir "portfolio_snapshot_daily.json"), $json, $utf8NoBom)

Write-Host "[PORTFOLIO] Wrote logs\portfolio_snapshot_daily.json" -ForegroundColor Green
exit 0