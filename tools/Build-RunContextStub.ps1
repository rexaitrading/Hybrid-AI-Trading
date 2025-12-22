[CmdletBinding()]
param(
    [string]$Symbol = "NVDA"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
$logsDir  = Join-Path $repoRoot "logs"

if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
}

$statusPath    = Join-Path $logsDir "blockg_status_stub.json"
$runCtxPath    = Join-Path $logsDir "run_context.json"            # canonical
$runCtxLegacy  = Join-Path $logsDir "runcontext_phase5_stub.json" # legacy compat

if (-not (Test-Path $statusPath)) {
    Write-Host "[RUNCTX] ERROR: Block-G status JSON not found at $statusPath" -ForegroundColor Red
    exit 1
}

Write-Host "[RUNCTX] Loading Block-G status from $statusPath" -ForegroundColor Cyan

try {
    $raw    = Get-Content -Path $statusPath -Raw -Encoding UTF8
    $status = $raw | ConvertFrom-Json
} catch {
    Write-Host "[RUNCTX] ERROR: Failed to parse Block-G status JSON. $_" -ForegroundColor Red
    exit 1
}

function Get-StatusFieldSafe {
    param(
        [Parameter(Mandatory = $true)]$Status,
        [Parameter(Mandatory = $true)][string]$Name
    )
    $prop = $Status.PSObject.Properties[$Name]
    if ($prop -ne $null) { return $prop.Value }
    return $null
}

$today = (Get-Date).ToString("yyyy-MM-dd")
$asOf  = Get-StatusFieldSafe -Status $status -Name "as_of_date"
if (-not $asOf) { $asOf = Get-StatusFieldSafe -Status $status -Name "date" }
if (-not $asOf) { $asOf = Get-StatusFieldSafe -Status $status -Name "trading_day" }
if (-not $asOf) { $asOf = $today }

$phase23   = Get-StatusFieldSafe -Status $status -Name "phase23_health_ok_today"
$evHard    = Get-StatusFieldSafe -Status $status -Name "ev_hard_daily_ok_today"
$gsFresh   = Get-StatusFieldSafe -Status $status -Name "gatescore_fresh_today"
$nvdaReady = Get-StatusFieldSafe -Status $status -Name "nvda_blockg_ready"
$spyReady  = Get-StatusFieldSafe -Status $status -Name "spy_blockg_ready"
$qqqReady  = Get-StatusFieldSafe -Status $status -Name "qqq_blockg_ready"

# Derive mode from env flag (default paper-safe)
$mode = "paper"
try {
    $envFlag = [string]$env:HAT_IS_PAPER
    if ($envFlag -eq "0") { $mode = "live" }
} catch { $mode = "paper" }

$tsUtc = (Get-Date).ToUniversalTime().ToString("o")

$payload = [ordered]@{
    ts_utc                  = $tsUtc
    as_of_date              = $asOf
    mode                    = $mode
    symbol                  = $Symbol
    phase5_mode             = "Phase5-Safety"
    blockg_status_path      = "logs/blockg_status_stub.json"
    phase23_health_ok_today = $phase23
    ev_hard_daily_ok_today  = $evHard
    gatescore_fresh_today   = $gsFresh
    nvda_blockg_ready       = $nvdaReady
    spy_blockg_ready        = $spyReady
    qqq_blockg_ready        = $qqqReady
}

$payloadJson = $payload | ConvertTo-Json -Depth 6
$enc = New-Object System.Text.UTF8Encoding($false)

# Write canonical + legacy
[System.IO.File]::WriteAllText($runCtxPath,   $payloadJson + "`n", $enc)
[System.IO.File]::WriteAllText($runCtxLegacy, $payloadJson + "`n", $enc)

Write-Host "[RUNCTX] Writing RunContext to $runCtxPath (and legacy $runCtxLegacy)" -ForegroundColor Cyan
Write-Host "[RUNCTX] RunContext snapshot:" -ForegroundColor Yellow
$payload.GetEnumerator() | Format-Table -AutoSize

exit 0