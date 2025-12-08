[CmdletBinding()]
param(
    [switch] $DryRunOnly
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# Script lives under repoRoot\tools -> go one level up to repo root
$scriptDir = Split-Path -Parent $PSCommandPath
$repoRoot  = Split-Path -Parent $scriptDir
Set-Location $repoRoot

Write-Host "`n[PHASE2-SUITE] Phase-2 SPY/QQQ ORB microstructure suite" -ForegroundColor Cyan
Write-Host "RepoRoot    = $repoRoot"
Write-Host "DryRunOnly  = $DryRunOnly" -ForegroundColor Gray

$enrichScript = Join-Path $repoRoot "tools\\Run-SpyQqqMicrostructureEnrich.ps1"
$reportScript = Join-Path $repoRoot "tools\\Run-SpyQqqMicrostructureReport.ps1"

if (-not (Test-Path $enrichScript)) {
    Write-Host "[ERROR] Enrich wrapper not found at $enrichScript" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $reportScript)) {
    Write-Host "[ERROR] Report wrapper not found at $reportScript" -ForegroundColor Red
    exit 1
}

if ($DryRunOnly) {
    Write-Host "`n[PHASE2-SUITE] Dry-run enrichment + report (BOTH)" -ForegroundColor Cyan
    & $enrichScript -Symbol BOTH -DryRun
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        Write-Host "[PHASE2-SUITE] Enrich dry-run FAILED (code=$exitCode)" -ForegroundColor Red
        exit $exitCode
    }

    & $reportScript -Symbol BOTH -DryRun
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        Write-Host "[PHASE2-SUITE] Report dry-run FAILED (code=$exitCode)" -ForegroundColor Red
        exit $exitCode
    }

    Write-Host "`n[PHASE2-SUITE] Dry-run completed successfully." -ForegroundColor Green
    return
}

Write-Host "`n[PHASE2-SUITE] Real enrichment + report (BOTH)" -ForegroundColor Cyan

# 1) Real enrichment both symbols
& $enrichScript -Symbol BOTH
$exitCode = $LASTEXITCODE
if ($exitCode -ne 0) {
    Write-Host "[PHASE2-SUITE] Enrich FAILED (code=$exitCode)" -ForegroundColor Red
    exit $exitCode
}

# 2) Real report both symbols
& $reportScript -Symbol BOTH
$exitCode = $LASTEXITCODE
if ($exitCode -ne 0) {
    Write-Host "[PHASE2-SUITE] Report FAILED (code=$exitCode)" -ForegroundColor Red
    exit $exitCode
}

Write-Host "`n[PHASE2-SUITE] Phase-2 SPY/QQQ microstructure suite completed successfully." -ForegroundColor Green