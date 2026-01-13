[CmdletBinding()]
param(
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","HK_SH","HK_SZ","CN_SH","CN_SZ")] [string]$Market="US"
)
# --- repo root bootstrap (env-first) ---
$repoRoot = ($env:HAT_REPO_ROOT + "").Trim()
# PHASE4_MARKETWIRE_BEGIN
try {
  $psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
  $rcFile = Join-Path $repoRoot "tools\Resolve-RunContext.ps1"
  if(Test-Path -LiteralPath $rcFile){
    $rcRaw = & $psExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $rcFile -Market $Market -Symbol NVDA 2>$null | Out-String
    $rcRaw = ($rcRaw + "").Trim()
    if($rcRaw){
      $rc = $rcRaw | ConvertFrom-Json
      if($rc -and ($rc.PSObject.Properties.Name -contains "as_of_date") -and (($rc.as_of_date + "") -ne "")){
        $env:HAT_ASOF_DATE = [string]$rc.as_of_date
      }
      if($rc -and ($rc.PSObject.Properties.Name -contains "logs_dir_out") -and (($rc.logs_dir_out + "") -ne "")){
        $env:HAT_LOGS_DIR_OUT = [string]$rc.logs_dir_out
      }
    }
  }
} catch { }
# PHASE4_MARKETWIRE_END

if(-not $repoRoot){
  $repoRoot = & (Join-Path $PSScriptRoot "Go-RepoRoot.ps1")
}
if(-not $repoRoot){ throw "[REPOROOT] FAIL-CLOSED: repoRoot empty (env+Go-RepoRoot)" }
$repoRoot = [System.IO.Path]::GetFullPath($repoRoot)
Set-Location -LiteralPath $repoRoot
[System.Environment]::CurrentDirectory = $repoRoot

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
# $toolsDir = Split-Path -Parent $PSCommandPath   # disabled (use env HAT_REPO_ROOT)
# $repoRoot = Split-Path -Parent $toolsDir        # disabled (use env HAT_REPO_ROOT)
# Set-Location $repoRoot                          # disabled (use env HAT_REPO_ROOT)
Write-Host "`n[PHASE4] Phase-4 validation harness RUN" -ForegroundColor Cyan
Write-Host "[PHASE] RepoRoot OK" -ForegroundColor DarkGray

$env:PYTHONPATH = Join-Path $repoRoot "src"
$pythonExe      = ".\.venv\Scripts\python.exe"

$stampPath = Join-Path $repoRoot "logs\phase4_validation_passed.json"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$phase4TmpRoot = (Join-Path $env:TEMP "HybridAITrading\phase4")
New-Item -ItemType Directory -Force -Path $phase4TmpRoot | Out-Null
$runTag = (Get-Date).ToString("yyyyMMdd_HHmmss")


function Write-Phase4Stamp {
  param(
    [Parameter(Mandatory)][bool]$Ok,
    [Parameter(Mandatory)][string]$Reason,
    [Parameter(Mandatory)][int]$ExitCode
  )
  $tsUtc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
  $asof = (($env:HAT_ASOF_DATE + "")).Trim()
  if(-not $asof){ $asof = (Get-Date).ToString("yyyy-MM-dd") }
  $payload = [ordered]@{
    ts_utc = $tsUtc
    as_of_date = $asof
    phase4_ok_today = $Ok
    reason = $Reason
    exit_code = $ExitCode
  }
  $json = ($payload | ConvertTo-Json -Depth 5)
  [System.IO.File]::WriteAllText($stampPath, $json, $utf8NoBom)

  $ld = (($env:HAT_LOGS_DIR_OUT + "")).Trim()
  if($ld){
    New-Item -ItemType Directory -Force -Path $ld | Out-Null
    $stampPathMarket = Join-Path $ld "phase4_validation_passed.json"
    [System.IO.File]::WriteAllText($stampPathMarket, $json, $utf8NoBom)
  }
}

function Invoke-Phase4PyTest {
  param(
    [Parameter(Mandatory)][string[]]$Args,
    [Parameter(Mandatory)][string]$Label
  )
  Write-Host "`n[PHASE4] $Label" -ForegroundColor Yellow
  $baseTemp = Join-Path $phase4TmpRoot ("{0}_{1}" -f ($Label -replace '[^\w\-]+','_'), $runTag)
  & $pythonExe -m pytest @Args --basetemp $baseTemp
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
