[CmdletBinding()]
param(
  [Parameter(Mandatory=$false)][string]$AsOf = ""
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$logs = Join-Path $repoRoot "logs"
if(-not (Test-Path $logs)){ New-Item -ItemType Directory -Force -Path $logs | Out-Null }

$today = if($AsOf){ $AsOf } else { (Get-Date).ToString("yyyy-MM-dd") }
$out   = Join-Path $logs ("portfolio_optimizer_daily_{0}.json" -f $today)

# Inputs (placeholder hooks)
# You can wire these later:
# - logs\run_context.json (Phase5 safety context)
# - logs\positions_*.json/csv (portfolio state)
$runCtxPath = Join-Path $logs "run_context.json"

$reasons = New-Object System.Collections.Generic.List[string]
$status = "SKIPPED"

if(-not (Test-Path $runCtxPath)){
  $status = "SKIPPED"
  $reasons.Add("missing_run_context_json")
}

# Minimal “optimizer” placeholder:
# If SKIPPED => empty allocations; if OK => still empty but explicit constraints_ok=false
$payload = [ordered]@{
  ts_utc = (Get-Date).ToUniversalTime().ToString("o")
  as_of_date = $today
  status = $status
  reasons = @($reasons)
  constraints_ok = $false
  allocations = @()
  notes = "Phase7 scaffold: wire real inputs + constraints later"
}

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($out, ($payload | ConvertTo-Json -Depth 6), $utf8NoBom)

Write-Host "[PHASE7] wrote $out status=$status" -ForegroundColor Green
exit 0