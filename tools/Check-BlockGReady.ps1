[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)]
  [ValidateNotNullOrEmpty()]
  [string]$Symbol,

  # Optional override for tests / tooling
  [string]$ContractPath = (Join-Path $PSScriptRoot "..\logs\blockg_status_stub.json")
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Fail([int]$Code, [string]$Msg) {
  Write-Host "[BLOCK-G] $Msg" -ForegroundColor Yellow
  exit $Code
}

# Exit codes (deterministic)
# 0  = READY
# 3  = CONTRACT_INVALID (missing/stale/missing required fields/parse error)
# 10 = NOT_READY (contract ok but readiness flag false)

try {
  if (-not (Test-Path $ContractPath)) {
    Fail 3 "contract missing: $ContractPath"
  }

  $raw = Get-Content $ContractPath -Raw -Encoding UTF8
  $obj = $raw | ConvertFrom-Json
} catch {
  Fail 3 ("contract unreadable/invalid json: " + $_.Exception.Message)
}

# Freshness: as_of_date MUST equal today (fail-closed)
$today = (Get-Date).ToString("yyyy-MM-dd")
$asOf = [string]$obj.as_of_date
if ([string]::IsNullOrWhiteSpace($asOf)) {
  Fail 3 "contract missing as_of_date"
}
if ($asOf -ne $today) {
  Fail 3 "contract stale: as_of_date=$asOf today=$today"
}

function RequireFlag([object]$Obj, [string]$Field) {
  $p = $Obj.PSObject.Properties.Name
  if ($p -notcontains $Field) {
    Fail 3 "contract missing required field: $Field"
  }
  return [bool]$Obj.$Field
}

$sym = ($Symbol.Trim().ToUpperInvariant())

# Support common multi-symbol calls (fail closed)
if ($sym -eq "ALL") {
  $nvda = RequireFlag $obj "nvda_blockg_ready"
  $spy  = RequireFlag $obj "spy_blockg_ready"
  $qqq  = RequireFlag $obj "qqq_blockg_ready"

  if ($nvda -and $spy -and $qqq) {
    Write-Host "[BLOCK-G] READY: ALL" -ForegroundColor Green
    exit 0
  }

  Fail 10 ("NOT_READY: ALL nvda=$nvda spy=$spy qqq=$qqq")
}

switch ($sym) {
  "NVDA" { $field = "nvda_blockg_ready" }
  "SPY"  { $field = "spy_blockg_ready" }
  "QQQ"  { $field = "qqq_blockg_ready" }
  default { Fail 3 "unsupported symbol: $sym (expected NVDA/SPY/QQQ/ALL)" }
}

$ok = RequireFlag $obj $field
if (-not $ok) {
  Fail 10 "NOT_READY: $sym ($field=false)"
}

Write-Host "[BLOCK-G] READY: $sym" -ForegroundColor Green
exit 0