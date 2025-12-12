[CmdletBinding()]
param(
    [Parameter()]
    [string]$Symbol = "NVDA"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
$logsPath = Join-Path $repoRoot "logs"
$contractPath = Join-Path $logsPath "blockg_status_stub.json"

Write-Host "[BLOCK-G] Check-BlockGReady.ps1 -Symbol $Symbol" -ForegroundColor Cyan
Write-Host "[BLOCK-G] Contract path: $contractPath" -ForegroundColor DarkGray

if (-not (Test-Path $contractPath)) {
    Write-Host "[BLOCK-G] ERROR: Contract JSON not found." -ForegroundColor Red
    exit 1
}

try {
    $status = Get-Content $contractPath -Raw | ConvertFrom-Json

$today = (Get-Date).ToString("yyyy-MM-dd")
if (-not ($status.PSObject.Properties.Name -contains "as_of_date")) {
    Write-Host "[BLOCK-G] ERROR: Contract missing required field: as_of_date" -ForegroundColor Red
    exit 3
}
if (("$($status.as_of_date)" -ne $today)) {
    Write-Host "[BLOCK-G] ERROR: Contract stale (as_of_date=$($status.as_of_date), today=$today)" -ForegroundColor Red
    exit 3
}
} catch {
    Write-Host "[BLOCK-G] ERROR: Failed to parse contract JSON: $_" -ForegroundColor Red
    exit 1
}

# Look for per-symbol readiness key, e.g. nvda_blockg_ready, spy_blockg_ready, qqq_blockg_ready
$symbolKey = ($Symbol.ToLower() + "_blockg_ready")

if (-not ($status.PSObject.Properties.Name -contains $symbolKey)) {
    Write-Host "[BLOCK-G] ERROR: Contract missing required field: $symbolKey" -ForegroundColor Red
    exit 3
}

$ready = [bool]($status.$symbolKey)

if ($ready) {
    Write-Host "[BLOCK-G] $Symbol Block-G READY (contract $symbolKey = True)." -ForegroundColor Green
    exit 0
} else {
    Write-Host "[BLOCK-G] $Symbol Block-G NOT READY (contract $symbolKey = False)." -ForegroundColor Yellow
    exit 1
}