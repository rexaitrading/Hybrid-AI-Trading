[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$name = "\IBG-ForceClose-19h"
$out = schtasks /query /tn $name /fo LIST /v 2>$null

if (-not $out) {
  Write-Host "[IBG-AUDIT] OK: task not found: $name" -ForegroundColor Green
  exit 0
}

$stateLine = ($out | Select-String -SimpleMatch "Scheduled Task State:" | ForEach-Object { $_.ToString() }) -join "
"

if ($stateLine -match "Enabled") {
  Write-Host "[IBG-AUDIT] WARN: IBG force-close task is ENABLED. Disable it to prevent IBG shutdown." -ForegroundColor Yellow
  exit 2
}

Write-Host "[IBG-AUDIT] OK: IBG force-close task disabled." -ForegroundColor Green
exit 0