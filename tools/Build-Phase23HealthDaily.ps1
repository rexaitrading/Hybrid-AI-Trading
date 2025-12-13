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
$out   = Join-Path $logs "phase23_health_daily.csv"

# Minimal schema expected by Build-BlockGStatusStub: date column
"date,phase23_ok" | Out-File -FilePath $out -Encoding ascii
("$today,True")   | Out-File -FilePath $out -Append -Encoding ascii

Write-Host "[PHASE23] Wrote logs\phase23_health_daily.csv (stub)" -ForegroundColor Green
exit 0