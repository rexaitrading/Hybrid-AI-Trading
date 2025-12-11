[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

Write-Host "`n[PHASE4] Phase-4 validation harness RUN" -ForegroundColor Cyan
Write-Host "[PHASE4] RepoRoot = $repoRoot" -ForegroundColor DarkCyan

$env:PYTHONPATH = Join-Path $repoRoot "src"
$pythonExe      = ".\.venv\Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    Write-Host "[PHASE4] ERROR: Python executable not found at $pythonExe" -ForegroundColor Red
    exit 1
}

function Invoke-Phase4PyTest {
    param(
        [Parameter(Mandatory = $true)][string[]]$Args,
        [Parameter(Mandatory = $true)][string]$Label
    )

    Write-Host "`n[PHASE4] $Label" -ForegroundColor Yellow
    & $pythonExe -m pytest @Args
    $code = $LASTEXITCODE
    if ($code -ne 0) {
        Write-Host "[PHASE4] ERROR: $Label failed (exit=$code)" -ForegroundColor Red
        exit $code
    }
}

# 1) Phase-1 replay demo (NVDA bar replay → EV summary)
Invoke-Phase4PyTest -Label "Phase-1 replay demo pytest" -Args @(
    "tests/test_phase1_replay_demo.py"
)

# 2) Microstructure features (SPY/QQQ microstructure core) – optional until tests exist
$microTestPath = Join-Path $repoRoot "tests\test_microstructure_features.py"
if (Test-Path $microTestPath) {
    Invoke-Phase4PyTest -Label "Microstructure features tests" -Args @(
        "tests/test_microstructure_features.py"
    )
} else {
    Write-Host "[PHASE4] WARN: tests/test_microstructure_features.py not found; skipping microstructure test slice for now." -ForegroundColor Yellow
}

# 3) Phase-5 risk + guard slice (EV-bands, RiskManager, engine guards)
Invoke-Phase4PyTest -Label "Phase-5 risk + guard slice" -Args @(
    "tests/test_phase5_ev_bands_basic.py",
    "tests/test_phase5_riskmanager_combined_gates.py",
    "tests/test_phase5_riskmanager_daily_loss_integration.py",
    "tests/test_execution_engine_phase5_guard.py",
    "tests/test_ib_phase5_guard.py"
)

Write-Host "`n[PHASE4] Phase-4 validation harness complete (all slices green / optional slices skipped)." -ForegroundColor Green
exit 0