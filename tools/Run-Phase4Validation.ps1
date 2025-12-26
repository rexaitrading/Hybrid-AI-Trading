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

$stampPath = Join-Path $repoRoot "logs\phase4_validation_passed.json"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Write-Phase4Stamp {
  param(
    [Parameter(Mandatory)][bool]$Ok,
    [Parameter(Mandatory)][string]$Reason,
    [Parameter(Mandatory)][int]$ExitCode
  )
  $tsUtc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
  $today = (Get-Date).ToString("yyyy-MM-dd")
  $payload = [ordered]@{
    ts_utc = $tsUtc
    as_of_date = $today
    phase4_ok_today = $Ok
    reason = $Reason
    exit_code = $ExitCode
  }
  [System.IO.File]::WriteAllText($stampPath, ($payload | ConvertTo-Json -Depth 5), $utf8NoBom)
}

function Invoke-Phase4PyTest {
  param(
    [Parameter(Mandatory)][string[]]$Args,
    [Parameter(Mandatory)][string]$Label
  )
  Write-Host "`n[PHASE4] $Label" -ForegroundColor Yellow
  & $pythonExe -m pytest @Args
  $code = $LASTEXITCODE
  if ($code -ne 0) { throw "pytest_failed:$Label:exit=$code" }
}

try {
  if (-not (Test-Path -LiteralPath $pythonExe)) {
    throw "python_missing:$pythonExe"
  }

  # 1) Phase-1 replay demo (required)
  $t1 = "tests/test_phase1_replay_demo.py"
  if (-not (Test-Path -LiteralPath (Join-Path $repoRoot $t1))) {
    throw "missing_required_test:$t1"
  }
  Invoke-Phase4PyTest -Label "Phase-1 replay demo pytest" -Args @($t1)

  # 2) Microstructure slice (optional)
  $micro = "tests/test_microstructure_features.py"
  if (Test-Path -LiteralPath (Join-Path $repoRoot $micro)) {
    Invoke-Phase4PyTest -Label "Microstructure features tests" -Args @($micro)
  } else {
    Write-Host "[PHASE4] WARN: $micro not found; skipping microstructure slice." -ForegroundColor Yellow
  }

  # 3) Phase-5 risk + guard slice (required set: only run files that exist; but require at least 1)
  $phase5Candidates = @(
    "tests/test_phase5_riskmanager_combined_gates.py",
    "tests/test_phase5_riskmanager_daily_loss_integration.py",
    "tests/test_execution_engine_phase5_guard.py",
    "tests/test_ib_phase5_guard.py"
  )

  $phase5Args = @()
  foreach ($t in $phase5Candidates) {
    if (Test-Path -LiteralPath (Join-Path $repoRoot $t)) { $phase5Args += $t }
    else { Write-Host "[PHASE4] WARN: missing phase5 test => $t (skipping)" -ForegroundColor Yellow }
  }

  if ($phase5Args.Count -lt 1) {
    throw "missing_required_phase5_slice:0_tests_present"
  }

  Invoke-Phase4PyTest -Label "Phase-5 risk + guard slice" -Args $phase5Args

  Write-Host "`n[PHASE4] Phase-4 validation harness complete (required slices green / optional slices skipped)." -ForegroundColor Green
  Write-Phase4Stamp -Ok $true -Reason "ok" -ExitCode 0
  exit 0
}
catch {
  $msg = ($_.Exception.Message + "")
  Write-Host "[PHASE4] FAIL-CLOSED: $msg" -ForegroundColor Red

  # derive exit code
  $exitCode = 5
  if ($msg -match 'exit=(\d+)') { $exitCode = [int]$Matches[1] }
  elseif ($msg -like 'missing_required_test*') { $exitCode = 4 }
  elseif ($msg -like 'missing_required_phase5_slice*') { $exitCode = 4 }
  elseif ($msg -like 'python_missing*') { $exitCode = 2 }

  Write-Phase4Stamp -Ok $false -Reason $msg -ExitCode $exitCode
  exit $exitCode
}