[CmdletBinding()]
param(
  # MUST be explicitly set to 1 after you run Phase-4 tests successfully
  [ValidateSet("0","1")]
  [string]$Phase4Ok = "0"
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$logs = Join-Path $repoRoot "logs"
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }

$today = (Get-Date).ToString("yyyy-MM-dd")
$out   = Join-Path $logs "phase4_validation_passed.json"

$obj = [ordered]@{
  ts_utc          = (Get-Date).ToUniversalTime().ToString("o")
  as_of_date      = $today
  phase4_ok_today = [bool]([int]$Phase4Ok)
}

$json = ($obj | ConvertTo-Json -Depth 4)
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[IO.File]::WriteAllText($out, $json, $utf8NoBom)

Write-Host "[PHASE4] Wrote $out as_of_date=$today phase4_ok_today=$($obj.phase4_ok_today)" -ForegroundColor Green
exit 0