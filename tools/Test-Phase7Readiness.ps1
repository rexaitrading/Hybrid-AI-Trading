[CmdletBinding()]
param(
  [Parameter()][string]$Symbol = "NVDA"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

function Fail([string]$msg, [int]$code = 2) {
  Write-Host "[PHASE7] FAIL: $msg" -ForegroundColor Red
  exit $code
}

function Read-Json([string]$path) {
  if (-not (Test-Path $path)) { Fail "Missing required file: $path" 2 }
  try {
    $raw = Get-Content -LiteralPath $path -Raw
    return ($raw | ConvertFrom-Json)
  } catch {
    Fail "JSON parse error in $path : $($_.Exception.Message)" 3
  }
}

$today = (Get-Date).ToString("yyyy-MM-dd")
$sym   = (($Symbol + "")).Trim().ToUpper()
if (-not $sym) { Fail "Symbol is empty." 2 }

$phase4Path   = Join-Path $repoRoot "logs\phase4_validation_passed.json"
$contractPath = Join-Path $repoRoot "logs\blockg_status_stub.json"

$phase4   = Read-Json $phase4Path
$contract = Read-Json $contractPath

# Phase-7 stub = Phase-6 requirements (for now)
if ((($phase4.as_of_date + "")) -ne $today) { Fail "Phase4 stamp not for today ($today). as_of_date=$($phase4.as_of_date)" 4 }
if (-not [bool]$phase4.phase4_ok_today) { Fail "Phase4 not OK today." 5 }

if ((($contract.as_of_date + "")) -ne $today) { Fail "BlockG contract not for today ($today). as_of_date=$($contract.as_of_date)" 6 }
if (-not [bool]$contract.phase4_ok_today) { Fail "Contract says phase4_ok_today=false" 7 }
if (-not [bool]$contract.phase23_health_ok_today) { Fail "Contract says phase23_health_ok_today=false" 8 }
if (-not [bool]$contract.ev_hard_daily_ok_today) { Fail "Contract says ev_hard_daily_ok_today=false" 9 }
if (-not [bool]$contract.gatescore_ok_today) { Fail "Contract says gatescore_ok_today=false" 10 }

$key = ($sym.ToLower() + "_blockg_ready")
$val = $contract.$key
if ($null -eq $val) { Fail "Missing contract field: $key" 11 }
if (-not [bool]$val) { Fail "$sym not ready by contract ($key=false)" 12 }

Write-Host "[PHASE7] OK: $sym readiness satisfied (Phase4 + BlockG contract)." -ForegroundColor Green
exit 0