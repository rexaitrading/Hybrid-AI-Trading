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

# 1) Phase-1 replay demo (NVDA bar replay ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ EV summary)
Invoke-Phase4PyTest -Label "Phase-1 replay demo pytest" -Args @(
    "tests/test_phase1_replay_demo.py"
)

# 2) Microstructure features (SPY/QQQ microstructure core) ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã¢â‚¬Å“ optional until tests exist
$microTestPath = Join-Path $repoRoot "tests\test_microstructure_features.py"
if (Test-Path $microTestPath) {
    Invoke-Phase4PyTest -Label "Microstructure features tests" -Args @(
        "tests/test_microstructure_features.py"
    )
} else {
    Write-Host "[PHASE4] WARN: tests/test_microstructure_features.py not found; skipping microstructure test slice for now." -ForegroundColor Yellow
}

# 3) Phase-5 risk + guard slice (EV-bands, RiskManager, engine guards)
    # 3) Phase-5 risk + guard slice (EV-bands, RiskManager, engine guards)
    $phase5Tests = @(
        "tests/test_phase5_ev_bands_basic.py"
        "tests/test_phase5_riskmanager_combined_gates.py"
        "tests/test_phase5_riskmanager_daily_loss_integration.py"
        "tests/test_execution_engine_phase5_guard.py"
        "tests/test_ib_phase5_guard.py"
    ) | Where-Object { Test-Path (Join-Path $repoRoot $_) }

    if ($phase5Tests.Count -gt 0) {
        Invoke-Phase4PyTest -Label "Phase-5 risk + guard slice" -Args $phase5Tests
    } else {
        Write-Host "[PHASE4] WARN: no Phase-5 slice tests found; skipping Phase-5 slice." -ForegroundColor Yellow
    }

Write-Host "`n[PHASE4] Phase-4 validation harness complete (all slices green / optional slices skipped)." -ForegroundColor Green

function Write-Phase4Stamp {
    try {
        $toolsDir2 = Split-Path -Parent $PSCommandPath
        $repoRoot2 = Split-Path -Parent $toolsDir2
        $logsDir2  = Join-Path $repoRoot2 "logs"
        if (-not (Test-Path $logsDir2)) { New-Item -ItemType Directory -Path $logsDir2 | Out-Null }

        $stampObj = [ordered]@{
            ts_utc          = (Get-Date).ToUniversalTime().ToString("o")
            as_of_date      = (Get-Date).ToString("yyyy-MM-dd")
            phase4_ok_today = $true
        }

        $json = ($stampObj | ConvertTo-Json -Depth 5)
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText((Join-Path $logsDir2 "phase4_validation_passed.json"), $json, $utf8NoBom)
        Write-Host "[PHASE4] Wrote logs\phase4_validation_passed.json" -ForegroundColor DarkGray
    } catch {
        Write-Host "[PHASE4] WARN: could not write phase4 stamp: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

Write-Phase4Stamp
exit 0# --- Block-G: Phase-4 "passed today" stamp (contract input) ---
try {
  $repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
  $logsDir  = Join-Path $repoRoot "logs"
  if (-not (Test-Path $logsDir)) { New-Item -ItemType Directory -Path $logsDir | Out-Null }

  $stamp = [ordered]@{
    ts_utc      = (Get-Date).ToUniversalTime().ToString("o")
    as_of_date  = (Get-Date).ToString("yyyy-MM-dd")
    phase4_ok_today = $true
  }

  $json = ($stamp | ConvertTo-Json -Depth 5)
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText((Join-Path $logsDir "phase4_validation_passed.json"), $json, $utf8NoBom)
  Write-Host "[PHASE4] Wrote logs\phase4_validation_passed.json" -ForegroundColor DarkGray
} catch {
  Write-Host "[PHASE4] WARN: could not write phase4 stamp: $($_.Exception.Message)" -ForegroundColor Yellow
}
# --- end stamp ---
