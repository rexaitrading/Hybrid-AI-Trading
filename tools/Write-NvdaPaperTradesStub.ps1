[CmdletBinding()]
param()

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$logs = Join-Path $repoRoot "logs"
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }

$out = Join-Path $logs "paper_trades.jsonl"

# PLUMBING ONLY:
# One candidate trade line for the NVDA paper runner to consume.
# Edit freely. If you never run this script, the system stays fail-closed.
'{"ts":"PLUMBING","symbol":"NVDA","side":"BUY","qty":1,"price":100.0,"regime":"TEST","order_type":"MKT"}' |
  Out-File -FilePath $out -Encoding ascii

Write-Host "[NVDA-PAPER] Wrote logs\paper_trades.jsonl (plumbing stub)" -ForegroundColor Green
return