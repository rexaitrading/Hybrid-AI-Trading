[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

Write-Host "`n[PHASE5-FULLCI] === Phase-5 Full CI ===" -ForegroundColor Cyan

# 1) Phase-5 microsuite
$microSuite = Join-Path $toolsDir "Run-Phase5MicroSuite.ps1"
if (Test-Path $microSuite) {
    Write-Host "`n[STEP 1] Phase-5 microsuite" -ForegroundColor Yellow
    & $microSuite
} else {
    Write-Host "[STEP 1] SKIP: Run-Phase5MicroSuite.ps1 not found at $microSuite" -ForegroundColor DarkYellow
}

# 2) EV preflight
$evPreflight = Join-Path $toolsDir "Run-Phase5EvPreflight.ps1"
if (Test-Path $evPreflight) {
    Write-Host "`n[STEP 2] Phase-5 EV preflight (EV anchors + PnL/EV audit + pytest slice)" -ForegroundColor Yellow
    & $evPreflight
} else {
    Write-Host "[STEP 2] SKIP: Run-Phase5EvPreflight.ps1 not found at $evPreflight" -ForegroundColor DarkYellow
}

# 3) Optional IB API smoke
$ibSmoke = Join-Path $toolsDir "Test-IBAPI.ps1"
if (Test-Path $ibSmoke) {
    Write-Host "`n[STEP 3] Optional IB API smoke" -ForegroundColor Yellow
    try {
        & $ibSmoke
    } catch {
        Write-Host "[STEP 3] IB API smoke FAILED (non-fatal for FullCI) :" -ForegroundColor Red
        Write-Host $_ -ForegroundColor Red
    }
} else {
    Write-Host "[STEP 3] SKIP: Test-IBAPI.ps1 not found at $ibSmoke" -ForegroundColor DarkYellow
}

# 4) Optional Notion snapshot sanity
$notionPnl = Join-Path $toolsDir "Show-Phase5PnlLast5Days.ps1"
if (Test-Path $notionPnl) {
    Write-Host "`n[STEP 4] Optional Phase-5 PnL last 5 days snapshot" -ForegroundColor Yellow
    & $notionPnl
} else {
    Write-Host "[STEP 4] SKIP: Show-Phase5PnlLast5Days.ps1 not found at $notionPnl" -ForegroundColor DarkYellow
}

Write-Host "`n[PHASE5-FULLCI] === End Phase-5 Full CI ===`n" -ForegroundColor Cyan