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

function Log {
  param([string]$Msg)
  $line = "[{0}] {1}`n" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Msg
  $daily = Join-Path $OpsDir ("ops_{0}.log" -f (Get-Date -Format "yyyyMMdd"))
  Add-Content -LiteralPath $daily -Value $line -Encoding utf8
  $line | Out-Host
}

function Run-Step {
  param([string]$Name, [scriptblock]$Action)
  $ts = Get-Date -Format "yyyyMMdd_HHmmss"
  $out = Join-Path $OpsDir ("{0}.{1}.out.log" -f $Name, $ts)
  $err = Join-Path $OpsDir ("{0}.{1}.err.log" -f $Name, $ts)

  Log "STEP_START $Name out=$out err=$err"
  try { & $Action 1> $out 2> $err; Log "STEP_OK    $Name" }
  catch { Log "STEP_FAIL  $Name :: $($_.Exception.Message)" }
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

  if ($now.Minute -eq 0 -and $now.Second -lt 5) {
    Log "HEARTBEAT hour=$(Get-Date -Format HH)"
  }

  Start-Sleep -Seconds 5
}