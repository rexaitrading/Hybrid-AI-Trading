[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("NVDA","SPY","QQQ")]
    [string]$Symbol
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

$contractPath = Join-Path $repoRoot "logs\blockg_status_stub.json"
if (-not (Test-Path $contractPath)) {
    Write-Host "[BLOCKG] Missing contract: logs\blockg_status_stub.json" -ForegroundColor Red
    exit 2
}

$raw = Get-Content $contractPath -Raw -Encoding utf8
# BOM-safe
if ($raw.Length -gt 0 -and [int][char]$raw[0] -eq 65279) { $raw = $raw.TrimStart([char]65279) }

try {
    $c = $raw | ConvertFrom-Json -ErrorAction Stop
} catch {
    Write-Host "[BLOCKG] Contract JSON parse failed" -ForegroundColor Red
    exit 2
}

$today = (Get-Date).ToString("yyyy-MM-dd")
$asOf  = [string]$c.as_of_date

if ($asOf -ne $today) {
    Write-Host "[BLOCKG] INVALID CONTRACT: stale as_of_date=$asOf today=$today" -ForegroundColor Red
    exit 3
}

function Get-Bool($v) {
    if ($v -is [bool]) { return $v }
    if ($v -is [string]) {
        $t = $v.Trim().ToLowerInvariant()
        if ($t -in @("true","1","yes","y")) { return $true }
        if ($t -in @("false","0","no","n")) { return $false }
    }
    if ($v -is [int] -or $v -is [double]) { return [bool]$v }
    return $false
}

$phase23 = Get-Bool $c.phase23_health_ok_today
$evhard  = Get-Bool $c.ev_hard_daily_ok_today
# GateScore field: accept either gatescore_fresh_today or gatescore_ok_today (schema compatibility)
$gscore = $false
if ($c.PSObject.Properties.Name -contains "gatescore_fresh_today") {
    $gscore = Get-Bool $c.gatescore_fresh_today
} elseif ($c.PSObject.Properties.Name -contains "gatescore_ok_today") {
    $gscore = Get-Bool $c.gatescore_ok_today
} else {
    Write-Host "[BLOCKG] INVALID CONTRACT: missing GateScore field (gatescore_fresh_today / gatescore_ok_today)" -ForegroundColor Red
    exit 3
}
$nvdaFlag = Get-Bool $c.nvda_blockg_ready
$spyFlag  = Get-Bool $c.spy_blockg_ready
$qqqFlag  = Get-Bool $c.qqq_blockg_ready
# required per-symbol readiness field
$required = switch ($Symbol) {
  "NVDA" { "nvda_blockg_ready" }
  "SPY"  { "spy_blockg_ready" }
  "QQQ"  { "qqq_blockg_ready" }
}
if (-not ($c.PSObject.Properties.Name -contains $required)) {
  Write-Host "[BLOCKG] INVALID CONTRACT: missing $required" -ForegroundColor Red
  exit 3
}

switch ($Symbol) {
    "NVDA" {
        $ok = ($phase23 -and $evhard -and $gscore -and $nvdaFlag)
    }
    "SPY" {
        $ok = $spyFlag
    }
    "QQQ" {
        $ok = $qqqFlag
    }
}

if ($ok) {
    Write-Host "[BLOCKG] READY Symbol=$Symbol as_of_date=$asOf" -ForegroundColor Green
    exit 0
}

Write-Host "[BLOCKG] NOT READY Symbol=$Symbol as_of_date=$asOf phase23=$phase23 ev_hard=$evhard gatescore_fresh=$gscore nvda=$nvdaFlag spy=$spyFlag qqq=$qqqFlag" -ForegroundColor Yellow
exit 2