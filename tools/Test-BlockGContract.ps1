[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [ValidateSet("NVDA","SPY","QQQ")]
    [string]$Symbol = "NVDA"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

function Get-StatusFieldSafe {
    param(
        [Parameter(Mandatory = $true)]$Status,
        [Parameter(Mandatory = $true)][string]$Name
    )

    $prop = $Status.PSObject.Properties[$Name]
    if ($prop -ne $null) {
        return $prop.Value
    }
    return $null
}

# Discover status JSON path (same logic as Check-BlockGReady.ps1)
$logsStatus  = Join-Path $repoRoot "logs\\blockg_status_stub.json"
$intelStatus = Join-Path $repoRoot ".intel\\blockg_status_stub.json"

if (Test-Path $logsStatus) {
    $statusPath = $logsStatus
} elseif (Test-Path $intelStatus) {
    $statusPath = $intelStatus
} else {
    Write-Host "BLOCK-G TEST: status JSON not found in logs or .intel." -ForegroundColor Red
    exit 1
}

Write-Host "BLOCK-G TEST: using status JSON at $statusPath" -ForegroundColor Cyan

try {
    $raw = Get-Content -Path $statusPath -Raw -Encoding UTF8
    $status = $raw | ConvertFrom-Json
} catch {
    Write-Host "BLOCK-G TEST: failed to parse status JSON. $_" -ForegroundColor Red
    exit 1
}

# Show a small summary (safe property access)
$asOf          = Get-StatusFieldSafe -Status $status -Name "as_of_date"
if (-not $asOf) { $asOf = Get-StatusFieldSafe -Status $status -Name "date" }
if (-not $asOf) { $asOf = Get-StatusFieldSafe -Status $status -Name "trading_day" }

$phase23Ok     = Get-StatusFieldSafe -Status $status -Name "phase23_health_ok_today"
$evHardOk      = Get-StatusFieldSafe -Status $status -Name "ev_hard_daily_ok_today"
$gsFresh       = Get-StatusFieldSafe -Status $status -Name "gatescore_fresh_today"
$nvdaReady     = Get-StatusFieldSafe -Status $status -Name "nvda_blockg_ready"
$spyReady      = Get-StatusFieldSafe -Status $status -Name "spy_blockg_ready"
$qqqReady      = Get-StatusFieldSafe -Status $status -Name "qqq_blockg_ready"

Write-Host "BLOCK-G TEST: status snapshot:" -ForegroundColor Yellow
Write-Host ("  as_of_date               = {0}" -f $asOf)
Write-Host ("  phase23_health_ok_today  = {0}" -f $phase23Ok)
Write-Host ("  ev_hard_daily_ok_today   = {0}" -f $evHardOk)
Write-Host ("  gatescore_fresh_today    = {0}" -f $gsFresh)
Write-Host ("  nvda_blockg_ready        = {0}" -f $nvdaReady)
Write-Host ("  spy_blockg_ready         = {0}" -f $spyReady)
Write-Host ("  qqq_blockg_ready         = {0}" -f $qqqReady)

Write-Host ""
Write-Host "BLOCK-G TEST: invoking Check-BlockGReady.ps1 -Symbol $Symbol" -ForegroundColor Cyan

$checker = Join-Path $toolsDir "Check-BlockGReady.ps1"

if (-not (Test-Path $checker)) {
    Write-Host "BLOCK-G TEST: checker script not found at $checker" -ForegroundColor Red
    exit 1
}

& $checker -Symbol $Symbol
$exitCode = $LASTEXITCODE

if ($exitCode -eq 0) {
    Write-Host "BLOCK-G TEST: Check-BlockGReady.ps1 EXIT=0 (READY) for $Symbol" -ForegroundColor Green
} else {
    Write-Host "BLOCK-G TEST: Check-BlockGReady.ps1 EXIT=$exitCode (NOT READY) for $Symbol" -ForegroundColor Red
}

exit $exitCode