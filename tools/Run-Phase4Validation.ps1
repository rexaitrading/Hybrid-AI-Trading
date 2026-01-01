[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
$choke = Join-Path $repoRoot "tools\Pytest-Chokepoint.ps1"
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
  & powershell -NoProfile -ExecutionPolicy Bypass -File $choke @Args
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

  # 2) Phase-2 microstructure + cost model slice (REQUIRED; fail-closed)
  $phase2Candidates = @(
    "tests/test_microstructure_regime.py",
    "tests/test_phase2_costs_package.py",
    "tests/test_phase2_cost_gate.py",
    "tests/test_phase2_cost_gate_latency.py",
    "tests/test_phase2_cost_gate_wiring.py"
  )

  $phase2Args = @()
  foreach ($t in $phase2Candidates) {
    if (Test-Path -LiteralPath (Join-Path $repoRoot $t)) { $phase2Args += $t }
    else { Write-Host "[PHASE4] WARN: missing phase2 test => $t (skipping)" -ForegroundColor Yellow }
  }
  if ($phase2Args.Count -lt 1) {
    throw "missing_required_phase2_slice:0_tests_present"
  }
  Invoke-Phase4PyTest -Label "Phase-2 microstructure/cost slice" -Args $phase2Args

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

# --- Write Phase-4 evidence JSON for Block-G (UTF-8 no-BOM, LF) ---
$repoRoot = (Split-Path -Parent (Split-Path -Parent $PSCommandPath))
$choke = Join-Path $repoRoot "tools\Pytest-Chokepoint.ps1"
$logsDir = Join-Path $repoRoot "logs"
if(-not (Test-Path $logsDir)){ New-Item -ItemType Directory -Force -Path $logsDir | Out-Null }
$today = (Get-Date).ToString("yyyy-MM-dd")
$ok = ($LASTEXITCODE -eq 0)
$obj = [ordered]@{ ts_utc=(Get-Date).ToUniversalTime().ToString("o"); as_of_date=$today; phase4_ok_today=[bool]$ok }
$json = ($obj | ConvertTo-Json -Depth 6)
$json = ($json -replace "`r`n","`n").TrimEnd()+"`n"
$path = Join-Path $logsDir "phase4_validation_passed.json"
$enc = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($path, $json, $enc)
Write-Host ("[PHASE4] wrote evidence: " + $path) -ForegroundColor DarkCyan
# --- end evidence ---
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