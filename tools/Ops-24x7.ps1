[CmdletBinding()]
param(
  [int]$IntelEveryMinutes = 30,
  [int]$PaperEveryMinutes = 5
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$VenvPy   = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$OpsDir   = Join-Path $RepoRoot "logs\ops"
New-Item -ItemType Directory -Force -Path $OpsDir | Out-Null

# ---- counters / rollup ----
$script:failIntel = 0
$script:failPaper = 0
$script:nextRoll  = (Get-Date).Date.AddDays(1)  # next local midnight

function Log {
  param([string]$Msg)
  $line  = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Msg
  $daily = Join-Path $OpsDir ("ops_{0}.log" -f (Get-Date -Format "yyyyMMdd"))
  Add-Content -LiteralPath $daily -Value ($line + "`n") -Encoding utf8
  $line | Out-Host
}

function Write-Rollup {
  $day  = Get-Date -Format "yyyyMMdd"
  $roll = Join-Path $OpsDir ("rollup_{0}.txt" -f $day)

  $intelOut = (Get-ChildItem -LiteralPath $OpsDir -Filter "intel.*.out.log" -File -ErrorAction SilentlyContinue | Measure-Object).Count
  $paperOut = (Get-ChildItem -LiteralPath $OpsDir -Filter "paper.*.out.log" -File -ErrorAction SilentlyContinue | Measure-Object).Count
  $last     = Get-ChildItem -LiteralPath $OpsDir -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1

  $body = @"
date=$day
intel_runs=$intelOut
paper_runs=$paperOut
failIntel=$script:failIntel
failPaper=$script:failPaper
last_file=$($last.Name)
last_write=$($last.LastWriteTime)
"@
  Set-Content -LiteralPath $roll -Value $body -Encoding utf8
  Log "ROLLUP wrote $roll"
}

function Run-Step {
  param([string]$Name, [scriptblock]$Action)

  $ts  = Get-Date -Format "yyyyMMdd_HHmmss"
  $out = Join-Path $OpsDir ("{0}.{1}.out.log" -f $Name, $ts)
  $err = Join-Path $OpsDir ("{0}.{1}.err.log" -f $Name, $ts)

  Log "STEP_START $Name out=$out err=$err"
  try {
    & $Action 1> $out 2> $err
    Log "STEP_OK    $Name"
  } catch {
    Log ("STEP_FAIL  {0} :: {1}" -f $Name, $_.Exception.Message)
    if ($Name -eq "intel") { $script:failIntel++ }
    if ($Name -eq "paper") { $script:failPaper++ }
  }
}

if (-not (Test-Path -LiteralPath $VenvPy)) { throw "Missing venv python: $VenvPy" }

# Reduce ccxt/git noise (safe; may or may not be honored by libs)
$env:CCXT_NO_GIT = "1"
$env:VERSIONEER_OVERRIDE = "0"
$env:SETUPTOOLS_SCM_PRETEND_VERSION = "0"

$nextIntel = Get-Date
$nextPaper = Get-Date

Log "OPS_24x7_START RepoRoot=$RepoRoot"
Log "IntelEveryMinutes=$IntelEveryMinutes PaperEveryMinutes=$PaperEveryMinutes"
Log "VenvPy=$VenvPy"

while ($true) {
  $now = Get-Date

  if ($now -ge $nextIntel) {
    Run-Step -Name "intel" -Action {
      $intel = Join-Path $RepoRoot "tools\Run-IntelPipeline.ps1"
      if (Test-Path -LiteralPath $intel) {
        powershell -NoProfile -ExecutionPolicy Bypass -File $intel
      } else {
        Write-Output "SKIP: tools\Run-IntelPipeline.ps1 not found"
      }
    }
    $nextIntel = (Get-Date).AddMinutes($IntelEveryMinutes)
  }

  if ($now -ge $nextPaper) {
    Run-Step -Name "paper" -Action {
      $paper1 = Join-Path $RepoRoot "scripts\run_eth1h_paper.ps1"
      $paper2 = Join-Path $RepoRoot "scripts\run_eth1h_kraken.ps1"

      if (Test-Path -LiteralPath $paper1) {
        powershell -NoProfile -ExecutionPolicy Bypass -File $paper1
      } else {
        Write-Output "SKIP: scripts\run_eth1h_paper.ps1 not found"
      }

      if (Test-Path -LiteralPath $paper2) {
        powershell -NoProfile -ExecutionPolicy Bypass -File $paper2
      } else {
        Write-Output "SKIP: scripts\run_eth1h_kraken.ps1 not found"
      }
    }
    $nextPaper = (Get-Date).AddMinutes($PaperEveryMinutes)
  }

  # midnight rollup
  if ($now -ge $script:nextRoll) {
    try { Write-Rollup } catch { Log ("ROLLUP_FAIL :: {0}" -f $_.Exception.Message) }
    $script:nextRoll = (Get-Date).Date.AddDays(1)
  }

  Start-Sleep -Seconds 5
}