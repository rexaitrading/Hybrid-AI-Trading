[CmdletBinding()]
param(
    [ValidateSet("SPY", "QQQ", "BOTH")]
    [string] $Symbol = "BOTH",

    [switch] $DryRun
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# Script lives under repoRoot\tools -> go one level up to repo root
$scriptDir = Split-Path -Parent $PSCommandPath
$repoRoot  = Split-Path -Parent $scriptDir
Set-Location $repoRoot

Write-Host "`n[PHASE2-REPORT] SPY/QQQ ORB microstructure report" -ForegroundColor Cyan
Write-Host "RepoRoot  = $repoRoot"
Write-Host "Symbol    = $Symbol"
Write-Host "DryRun    = $DryRun" -ForegroundColor Gray

# 1) Always call the enrichment wrapper first
$enrichScript = Join-Path $repoRoot "tools\\Run-SpyQqqMicrostructureEnrich.ps1"
if (-not (Test-Path $enrichScript)) {
    Write-Host "[ERROR] Enrich wrapper not found at $enrichScript" -ForegroundColor Red
    exit 1
}

Write-Host "`n[PHASE2-REPORT] Running enrichment wrapper..." -ForegroundColor Cyan
if ($DryRun) {
    & $enrichScript -Symbol $Symbol -DryRun
} else {
    & $enrichScript -Symbol $Symbol
}
$exitCode = $LASTEXITCODE
if ($exitCode -ne 0) {
    Write-Host "[PHASE2-REPORT] Enrichment wrapper FAILED with exit code $exitCode" -ForegroundColor Red
    exit $exitCode
}

if ($DryRun) {
    Write-Host "`n[PHASE2-REPORT] Dry run only; skipping CSV inspection." -ForegroundColor Yellow
    return
}

# 2) Inspect micro CSVs and print a tiny ORB-window summary
$logsDir = Join-Path $repoRoot "logs"

function Show-MicroSummary {
    param(
        [Parameter(Mandatory = $true)][string]$SymbolName,
        [Parameter(Mandatory = $true)][string]$FileName
    )

    $fullPath = Join-Path $logsDir $FileName
    if (-not (Test-Path $fullPath)) {
        Write-Host "[PHASE2-REPORT] SKIP: $FileName not found." -ForegroundColor DarkYellow
        return
    }

    $row = Import-Csv -Path $fullPath | Select-Object -First 1
    if (-not $row) {
        Write-Host "[PHASE2-REPORT] SKIP: $FileName is empty." -ForegroundColor DarkYellow
        return
    }

    $msRange = $row.ms_range_pct
    $trend   = $row.ms_trend_flag

    Write-Host ("[PHASE2-REPORT] {0}: ms_range_pct={1} ms_trend_flag={2}" -f $SymbolName, $msRange, $trend) -ForegroundColor Green
}

Write-Host "`n[PHASE2-REPORT] ORB-window microstructure summary" -ForegroundColor Cyan

if ($Symbol -in @("SPY", "BOTH")) {
    Show-MicroSummary -SymbolName "SPY" -FileName "spy_phase5_paper_for_notion_ev_diag_micro.csv"
}

if ($Symbol -in @("QQQ", "BOTH")) {
    Show-MicroSummary -SymbolName "QQQ" -FileName "qqq_phase5_paper_for_notion_ev_diag_micro.csv"
}

Write-Host "`n[PHASE2-REPORT] Done." -ForegroundColor Cyan