[CmdletBinding()]
param([int]$MaxAgeDays = 3)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$jp = Join-Path $repoRoot "logs\blockg_status_stub.json"
if (-not (Test-Path -LiteralPath $jp)) { throw "Missing: $jp" }

$st = Get-Content $jp -Raw -Encoding utf8 | ConvertFrom-Json
$age = 9999
try { $age = [int]$st.gatescore_age_days } catch { $age = 9999 }

if ($age -ge $MaxAgeDays) {
  Write-Host "[OPS] GateScore age_days=$age >= max=$MaxAgeDays -> LIVE MUST BE BLOCKED until refreshed" -ForegroundColor Red
  exit 2
}
elseif ($age -eq ($MaxAgeDays - 1)) {
  Write-Host "[OPS] GateScore age_days=$age nearing max=$MaxAgeDays -> run GateScore build pre-market" -ForegroundColor Yellow
  exit 0
}
else {
  Write-Host "[OPS] GateScore age_days=$age OK (max=$MaxAgeDays)" -ForegroundColor Green
  exit 0
}
