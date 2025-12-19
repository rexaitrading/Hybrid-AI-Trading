[CmdletBinding()]
param(
  [Parameter(Mandatory=$false)]
  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "NVDA",

  # Optional override for tests / tooling. If empty, script will compute canonical path.
  [string]$ContractPath = ""
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

# Robust script directory (works even if $PSScriptRoot is empty)
$scriptPath = $PSCommandPath
if (-not $scriptPath) { $scriptPath = $MyInvocation.MyCommand.Path }
if (-not $scriptPath) { Fail 3 "cannot resolve script path (PSCommandPath/MyInvocation empty)" }

$toolsDir = Split-Path -Parent $scriptPath
$repoRoot = Split-Path -Parent $toolsDir

function Resolve-ContractPath {
  param([Parameter(Mandatory=$true)][string]$Sym)
  $logs = Join-Path $repoRoot "logs"
  $canonical = Join-Path $logs "blockg_status_stub.json"
  $per = Join-Path $logs ("blockg_status_stub_{0}.json" -f $Sym.ToLowerInvariant())
  if (Test-Path -LiteralPath $canonical) { return $canonical }
  if (Test-Path -LiteralPath $per) { return $per }
  return $canonical
}

# Decide which contract path to use
$usePath = $ContractPath
if (-not ($usePath + "").Trim()) {
  $usePath = Resolve-ContractPath -Sym $Symbol
}

# Read JSON (BOM-safe)
function Read-JsonFile {
  param([Parameter(Mandatory=$true)][string]$Path)
  if(-not (Test-Path -LiteralPath $Path)){ return $null }
  $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
  if ($raw.Length -gt 0 -and [int][char]$raw[0] -eq 65279) { $raw = $raw.TrimStart([char]65279) }
  try { return ($raw | ConvertFrom-Json -ErrorAction Stop) } catch { return $null }
}

function RequireFlag([object]$Obj, [string]$Field) {
  $p = $Obj.PSObject.Properties.Name
  if ($p -notcontains $Field) { Fail 3 "contract missing required field: $Field" }
  return [bool]$Obj.$Field
}

$c = Read-JsonFile -Path $usePath
if (-not $c) { Fail 3 "contract missing/unreadable/invalid json: $usePath" }

# Freshness: MUST match today (fail-closed)
$today = (Get-Date).ToString("yyyy-MM-dd")
$asOf = [string]$c.as_of_date
if ([string]::IsNullOrWhiteSpace($asOf)) { Fail 3 "contract missing as_of_date" }
if ($asOf -ne $today) { Fail 3 "contract stale: as_of_date=$asOf today=$today" }

# ALL support
if ($Symbol -eq "ALL") {
  $nvda = RequireFlag $c "nvda_blockg_ready"
  $spy  = RequireFlag $c "spy_blockg_ready"
  $qqq  = RequireFlag $c "qqq_blockg_ready"
  if ($nvda -and $spy -and $qqq) { Write-Host "[BLOCK-G] READY: ALL" -ForegroundColor Green; exit 0 }
  Fail 10 ("NOT_READY: ALL nvda=$nvda spy=$spy qqq=$qqq")
}

switch ($Symbol) {
  "NVDA" { $field = "nvda_blockg_ready" }
  "SPY"  { $field = "spy_blockg_ready" }
  "QQQ"  { $field = "qqq_blockg_ready" }
  default { Fail 3 "unsupported symbol: $Symbol" }
}

$ok = RequireFlag $c $field
if (-not $ok) { Fail 10 "NOT_READY: $Symbol ($field=false)" }

Write-Host "[BLOCK-G] READY: $Symbol" -ForegroundColor Green
exit 0