[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$Symbol = "NVDA"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

function Fail([string]$msg, [int]$code = 2) {
  Write-Host "[BLOCK-G] FAIL: $msg" -ForegroundColor Red
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

$today    = (Get-Date).ToString("yyyy-MM-dd")
$symUpper = (($Symbol + "")).Trim().ToUpper()
if (-not $symUpper) { Fail "Symbol is empty." 2 }

$contractPath = Join-Path $repoRoot "logs\blockg_status_stub.json"
$contract     = Read-Json $contractPath

Write-Host "[BLOCK-G] Check-BlockGReady.ps1 -Symbol $symUpper"
Write-Host "[BLOCK-G] Today = $today"
Write-Host "[BLOCK-G] Contract path: $contractPath"

if ((($contract.as_of_date + "")) -ne $today) {
  Fail "Contract not for today ($today). as_of_date=$($contract.as_of_date)" 4
}

# Contract-only semantics (no recomputing)
$key = ($symUpper.ToLower() + "_blockg_ready")
$val = $contract.$key

if ($null -eq $val) {
  Fail "Missing contract field: $key" 5
}

if (-not [bool]$val) {
  Fail "$symUpper Block-G NOT READY (contract $key=false)." 6
}

Write-Host "[BLOCK-G] $symUpper Block-G READY (contract $key=true)." -ForegroundColor Green
exit 0