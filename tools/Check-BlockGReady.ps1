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

# Prefer logs\blockg_status_stub.json (used by Test-BlockGDateSanity), fallback to .intel
$logsStatus  = Join-Path $repoRoot "logs\\blockg_status_stub.json"
$intelStatus = Join-Path $repoRoot ".intel\\blockg_status_stub.json"

if (Test-Path $logsStatus) {
    $statusPath = $logsStatus
} elseif (Test-Path $intelStatus) {
    $statusPath = $intelStatus
} else {
    Write-Error "BLOCK-G: status JSON not found (.intel or logs)."
    exit 1
}

Write-Host "BLOCK-G: using status JSON at $statusPath" -ForegroundColor Cyan

try {
    $raw = Get-Content -Path $statusPath -Raw -Encoding UTF8
    $status = $raw | ConvertFrom-Json
} catch {
    Write-Error "BLOCK-G: failed to parse status JSON at $statusPath. $_"
    exit 1
}

function Get-AsOfDateString {
    param([Parameter(Mandatory = $true)]$Payload)

    # Use PSObject.Properties to avoid StrictMode issues
    $props = $Payload.PSObject.Properties

    $candidate = $null
    foreach ($name in @("as_of_date","date","trading_day")) {
        $prop = $props[$name]
        if ($prop -ne $null -and $prop.Value -ne $null -and $prop.Value -ne "") {
            $candidate = [string]$prop.Value
            break
        }
    }

    if (-not $candidate) {
        return $null
    }

    if ($candidate.Length -ge 10) {
        return $candidate.Substring(0,10)
    }
    return $candidate
}

function To-StrictBool {
    param([Parameter(Mandatory = $true)]$Value)

    if ($null -eq $Value) { return $false }
    if ($Value -is [bool]) { return [bool]$Value }

    if ($Value -is [string]) {
        $v = $Value.Trim().ToLowerInvariant()
        if ($v -in @("1","true","yes","y"))  { return $true }
        if ($v -in @("0","false","no","n")) { return $false }
    }

    return [bool]$Value
}

# 1) Today-ness
$asOf = Get-AsOfDateString -Payload $status
if (-not $asOf) {
    Write-Error "BLOCK-G: status JSON missing as_of_date/date/trading_day."
    exit 1
}

$today = (Get-Date).ToString("yyyy-MM-dd")

if ($asOf -ne $today) {
    Write-Error "BLOCK-G: status JSON date mismatch. as_of_date=$asOf, today=$today."
    exit 1
}

# 2) Global health flags
$phase23Ok = To-StrictBool $status.phase23_health_ok_today
$evHardOk  = To-StrictBool $status.ev_hard_daily_ok_today
$gsFresh   = To-StrictBool $status.gatescore_fresh_today

if (-not $phase23Ok) {
    Write-Error "BLOCK-G: phase23_health_ok_today is FALSE."
    exit 1
}
if (-not $evHardOk) {
    Write-Error "BLOCK-G: ev_hard_daily_ok_today is FALSE."
    exit 1
}
if (-not $gsFresh) {
    Write-Error "BLOCK-G: gatescore_fresh_today is FALSE."
    exit 1
}

# 3) Per-symbol flag
$symbolUpper = $Symbol.ToUpperInvariant()
$readyFlag = $null

switch ($symbolUpper) {
    "NVDA" { $readyFlag = $status.nvda_blockg_ready }
    "SPY"  { $readyFlag = $status.spy_blockg_ready }
    "QQQ"  { $readyFlag = $status.qqq_blockg_ready }
    default {
        # Unknown symbol -> conservative: treat as not ready
        Write-Error "BLOCK-G: unknown symbol '$Symbol' for Block-G check."
        exit 1
    }
}

if (-not (To-StrictBool $readyFlag)) {
    Write-Error "BLOCK-G: per-symbol ready flag is FALSE for $Symbol."
    exit 1
}

Write-Host "BLOCK-G: READY for symbol=$Symbol (date=$asOf)." -ForegroundColor Green
exit 0