[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
$logsDir  = Join-Path $repoRoot "logs"

if (-not (Test-Path $logsDir)) {
    Write-Host "[SAFETY-CSV] ERROR: logs directory not found at $logsDir" -ForegroundColor Red
    exit 1
}

$runCtxPath = Join-Path $logsDir "runcontext_phase5_stub.json"
$outCsvPath = Join-Path $logsDir "phase5_safety_runcontext_daily.csv"

if (-not (Test-Path $runCtxPath)) {
    Write-Host "[SAFETY-CSV] ERROR: RunContext stub JSON not found at $runCtxPath" -ForegroundColor Red
    Write-Host "[SAFETY-CSV] HINT: Run tools\\Build-BlockGStatusStub.ps1 and tools\\Build-RunContextStub.ps1 first." -ForegroundColor DarkYellow
    exit 1
}

Write-Host "[SAFETY-CSV] Loading Phase-5 RunContext from $runCtxPath" -ForegroundColor Cyan

try {
    $raw    = Get-Content -Path $runCtxPath -Raw -Encoding UTF8
    $runCtx = $raw | ConvertFrom-Json
} catch {
    Write-Host "[SAFETY-CSV] ERROR: Failed to parse RunContext JSON. $_" -ForegroundColor Red
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

$asOf    = Get-FieldSafe -Obj $runCtx -Name "as_of_date"
if (-not $asOf) { $asOf = "" }

$mode    = Get-FieldSafe -Obj $runCtx -Name "phase5_mode"
$phase23 = Get-FieldSafe -Obj $runCtx -Name "phase23_health_ok_today"
$evHard  = Get-FieldSafe -Obj $runCtx -Name "ev_hard_daily_ok_today"
$gsFresh = Get-FieldSafe -Obj $runCtx -Name "gatescore_fresh_today"

$nvdaReady = Get-FieldSafe -Obj $runCtx -Name "nvda_blockg_ready"
$spyReady  = Get-FieldSafe -Obj $runCtx -Name "spy_blockg_ready"
$qqqReady  = Get-FieldSafe -Obj $runCtx -Name "qqq_blockg_ready"

$row = [PSCustomObject]@{
    as_of_date          = $asOf
    phase5_mode         = $mode
    phase23_ok          = $phase23
    ev_hard_ok          = $evHard
    gatescore_ok        = $gsFresh
    nvda_blockg_ready   = $nvdaReady
    spy_blockg_ready    = $spyReady
    qqq_blockg_ready    = $qqqReady
}

Write-Host "[SAFETY-CSV] Writing Phase-5 safety RunContext CSV to $outCsvPath" -ForegroundColor Cyan
$row | Export-Csv -Path $outCsvPath -NoTypeInformation -Encoding UTF8

Write-Host "[SAFETY-CSV] Sample row:" -ForegroundColor Yellow
$row | Format-Table -AutoSize

exit 0