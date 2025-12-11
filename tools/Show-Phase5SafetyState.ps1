[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
$logsDir  = Join-Path $repoRoot "logs"

if (-not (Test-Path $logsDir)) {
    Write-Host "[SAFETY] ERROR: logs directory not found at $logsDir" -ForegroundColor Red
    exit 1
}

$runCtxPath = Join-Path $logsDir "runcontext_phase5_stub.json"

if (-not (Test-Path $runCtxPath)) {
    Write-Host "[SAFETY] ERROR: RunContext stub JSON not found at $runCtxPath" -ForegroundColor Red
    Write-Host "[SAFETY] HINT: Run tools\\Build-BlockGStatusStub.ps1 and tools\\Build-RunContextStub.ps1 first." -ForegroundColor DarkYellow
    exit 1
}

Write-Host "[SAFETY] Loading Phase-5 RunContext from $runCtxPath" -ForegroundColor Cyan

try {
    $raw     = Get-Content -Path $runCtxPath -Raw -Encoding UTF8
    $runCtx  = $raw | ConvertFrom-Json
} catch {
    Write-Host "[SAFETY] ERROR: Failed to parse RunContext JSON. $_" -ForegroundColor Red
    exit 1
}

function Get-FieldSafe {
    param(
        [Parameter(Mandatory = $true)]$Obj,
        [Parameter(Mandatory = $true)][string]$Name
    )

    $prop = $Obj.PSObject.Properties[$Name]
    if ($prop -ne $null) {
        return $prop.Value
    }
    return $null
}

$tsUtc   = Get-FieldSafe -Obj $runCtx -Name "ts_utc"
$asOf    = Get-FieldSafe -Obj $runCtx -Name "as_of_date"
$mode    = Get-FieldSafe -Obj $runCtx -Name "phase5_mode"

$phase23 = Get-FieldSafe -Obj $runCtx -Name "phase23_health_ok_today"
$evHard  = Get-FieldSafe -Obj $runCtx -Name "ev_hard_daily_ok_today"
$gsFresh = Get-FieldSafe -Obj $runCtx -Name "gatescore_fresh_today"

$nvdaReady = Get-FieldSafe -Obj $runCtx -Name "nvda_blockg_ready"
$spyReady  = Get-FieldSafe -Obj $runCtx -Name "spy_blockg_ready"
$qqqReady  = Get-FieldSafe -Obj $runCtx -Name "qqq_blockg_ready"

Write-Host ""
Write-Host "=========== Phase-5 Safety State (RunContext Stub) ===========" -ForegroundColor Cyan
Write-Host ("Date        : {0}" -f $asOf)
Write-Host ("TS (UTC)    : {0}" -f $tsUtc)
Write-Host ("Phase-5 Mode: {0}" -f $mode)
Write-Host "------------------------------------------------------------" -ForegroundColor DarkCyan
Write-Host ("Phase23 OK   : {0}" -f $phase23)
Write-Host ("EV-hard OK   : {0}" -f $evHard)
Write-Host ("GateScore OK : {0}" -f $gsFresh)
Write-Host "------------------------------------------------------------" -ForegroundColor DarkCyan
Write-Host ("NVDA Block-G : {0}" -f $nvdaReady)
Write-Host ("SPY  Block-G : {0}" -f $spyReady)
Write-Host ("QQQ  Block-G : {0}" -f $qqqReady)
Write-Host "==============================================================" -ForegroundColor Cyan

# Simple summary: is NVDA Live Safety Contract satisfied?
if ($phase23 -and $evHard -and $gsFresh -and $nvdaReady) {
    Write-Host "[SAFETY] NVDA LIVE SAFETY CONTRACT: SATISFIED" -ForegroundColor Green
} else {
    Write-Host "[SAFETY] NVDA LIVE SAFETY CONTRACT: NOT SATISFIED" -ForegroundColor Red
}

exit 0