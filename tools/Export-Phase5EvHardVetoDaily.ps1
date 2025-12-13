[CmdletBinding()]
param()

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$logs = Join-Path $repoRoot "logs"
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }

$today = (Get-Date).ToString("yyyy-MM-dd")
$out   = Join-Path $logs "phase5_ev_hard_veto_daily.csv"

# Minimal schema expected: date column
"date,ev_hard_ok" | Out-File -FilePath $out -Encoding ascii
("$today,True")   | Out-File -FilePath $out -Append -Encoding ascii

Write-Host "[EVHARD] Wrote logs\phase5_ev_hard_veto_daily.csv (stub)" -ForegroundColor Green
exit 0