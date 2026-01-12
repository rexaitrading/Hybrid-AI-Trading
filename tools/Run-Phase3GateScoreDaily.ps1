[CmdletBinding()]
param(
  [string]$Symbol = "NVDA",
  [string]$Csv = ""
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

# --- repo root bootstrap (ENV-ONLY, fail-closed) ---
$repoRoot = ($env:HAT_REPO_ROOT + "").Trim()
if(-not $repoRoot){
  throw "[REPOROOT] FAIL-CLOSED: HAT_REPO_ROOT is not set. Set it to the REAL repo root path."
}
$repoRoot = (Resolve-Path -LiteralPath $repoRoot).Path
$repoRoot = [System.IO.Path]::GetFullPath($repoRoot)

Set-Location -LiteralPath $repoRoot
[System.Environment]::CurrentDirectory = $repoRoot
$root = $repoRoot

$logsDir = Join-Path $repoRoot "logs"
if(-not (Test-Path -LiteralPath $logsDir)){
  New-Item -ItemType Directory -Force -Path $logsDir | Out-Null
}

function Invoke-BlockGCheckSafe([string]$Symbol){
  $checker = Join-Path $repoRoot "tools\Check-BlockGReady.ps1"
  if(-not (Test-Path -LiteralPath $checker)){
    throw "[PHASE3] FAIL-CLOSED: missing tools\Check-BlockGReady.ps1"
  }

  $status  = Join-Path $repoRoot "logs\blockg_status_stub.json"
  $stdout  = Join-Path $repoRoot "logs\blockg_build_stdout.txt"
  $stderr  = Join-Path $repoRoot "logs\blockg_build_stderr.txt"

  # Reuse stub if fresh (<=30min)
  $needBuild = $true
  if(Test-Path -LiteralPath $status){
    $ageMin = ((Get-Date) - (Get-Item -LiteralPath $status).LastWriteTime).TotalMinutes
    if($ageMin -le 30){
      $needBuild = $false
      Write-Host ("[PHASE3] BlockG stub fresh (age_min=" + [int]$ageMin + "); skip build") -ForegroundColor DarkGray
    }
  }

  if($needBuild){
    $builder = Join-Path $repoRoot "tools\Build-BlockGStatusStub.ps1"
    if(-not (Test-Path -LiteralPath $builder)){
      throw "[PHASE3] FAIL-CLOSED: missing tools\Build-BlockGStatusStub.ps1"
    }

    # Clean prior logs
    try { Remove-Item -LiteralPath $stdout,$stderr -Force -ErrorAction SilentlyContinue } catch {}

    # Run builder IN-PROCESS (job) with hard timeout
    $job = Start-Job -ScriptBlock {
      param($RepoRoot,$Builder,$Sym,$Stdout,$Stderr)

      $ErrorActionPreference="Stop"
      Set-StrictMode -Version Latest

      Set-Location -LiteralPath $RepoRoot
      [System.Environment]::CurrentDirectory = $RepoRoot

      $env:HAT_BLOCKG_BUILDER_FAST = "1"

      try {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $Builder -Symbol $Sym *>&1 |
          Out-File -LiteralPath $Stdout -Encoding UTF8
        exit 0
      } catch {
        ($_.Exception.ToString()) | Out-File -LiteralPath $Stderr -Encoding UTF8
        exit 2
      }
    } -ArgumentList $repoRoot,$builder,$Symbol,$stdout,$stderr

    $ok = Wait-Job -Id $job.Id -Timeout 90
    if(-not $ok){
      try { Stop-Job -Id $job.Id -Force } catch {}
      try { Remove-Job -Id $job.Id -Force } catch {}

      Write-Host "[PHASE3] builder timeout; stderr tail:" -ForegroundColor Yellow
      if(Test-Path -LiteralPath $stderr){
        Get-Content -LiteralPath $stderr -Tail 80 -Encoding UTF8 | Out-Host
      }

      if(Test-Path -LiteralPath $status){
        Write-Host "[PHASE3] WARN: builder timed out; falling back to existing stub" -ForegroundColor Yellow
        return
      }
      throw "[PHASE3] FAIL-CLOSED: BlockG builder exceeded 90s (killed) and no stub exists. See logs\blockg_build_stderr.txt"
    }

    # Drain output (forces completion)
    Receive-Job -Id $job.Id -ErrorAction SilentlyContinue | Out-Null
    try { Remove-Job -Id $job.Id -Force } catch {}

    # Hard assert stub exists
    if(-not (Test-Path -LiteralPath $status)){
      Write-Host "[PHASE3] builder finished but stub missing; stdout/stderr tail:" -ForegroundColor Yellow
      if(Test-Path -LiteralPath $stdout){ Get-Content -LiteralPath $stdout -Tail 80 -Encoding UTF8 | Out-Host }
      if(Test-Path -LiteralPath $stderr){ Get-Content -LiteralPath $stderr -Tail 80 -Encoding UTF8 | Out-Host }
      throw "[PHASE3] FAIL-CLOSED: builder did not create logs\blockg_status_stub.json"
    }

    Write-Host "[PHASE3] BlockG builder OK" -ForegroundColor Green
  }

  # Validate contract
  # Validate contract
  if(($env:HAT_ALLOW_CLOSED_DAY_DIAGNOSTICS + "") -eq "1"){
    Write-Host "[PHASE3] HOLD/closed-day diagnostics: BlockG BUILD_ONLY (no LIVE readiness required)" -ForegroundColor Yellow
    powershell -NoProfile -ExecutionPolicy Bypass -File $checker -Symbol $Symbol -Mode BUILD_ONLY *>&1 | Out-Host
  } else {
    powershell -NoProfile -ExecutionPolicy Bypass -File $checker -Symbol $Symbol *>&1 | Out-Host
  }
  if($LASTEXITCODE -ne 0){
    throw ("[PHASE3] FAIL-CLOSED: BlockG check failed exit=" + $LASTEXITCODE)
  }
}

# Hard lock imports to this repo
$py = Join-Path $root ".venv\Scripts\python.exe"
if(-not (Test-Path -LiteralPath $py)){
  throw "[PHASE3] Python exe not found: $py"
}
$env:PYTHONNOUSERSITE = "1"
$env:PYTHONPATH = (Join-Path $root "src")
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"

# Deterministic Block-G contract path
$k = ("HAT_" + "BLOCKG_" + "STATUS_" + "PATH")
[System.Environment]::SetEnvironmentVariable($k, (Join-Path $root "logs\blockg_status_stub.json"))

Write-Host "[PHASE3] ROOT=$root" -ForegroundColor Cyan
Write-Host "[PHASE3] SYMBOL=$Symbol" -ForegroundColor Cyan

Invoke-BlockGCheckSafe -Symbol $Symbol

if(-not $Csv){
  $cands = @(
    (Join-Path $root "logs\gatescore_pnl_summary.csv"),
    (Join-Path $root "logs\gatescore_daily_summary.csv"),
    (Join-Path $root "logs\gatescore_daily_summary_nvda.csv"),
    (Join-Path $root "logs\nvda_gatescore_samples.csv")
  )
  $Csv = ($cands | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1)
}
if(-not $Csv -or -not (Test-Path -LiteralPath $Csv)){
  Write-Host "[PHASE3] NOT READY: Missing GateScore CSV input (fail-closed)." -ForegroundColor Yellow
  exit 2
}

Write-Host "[PHASE3] CSV=$Csv" -ForegroundColor Cyan

& $py -m hybrid_ai_trading.gatescore.daily_build --csv $Csv --symbol $Symbol
$rc = $LASTEXITCODE
Write-Host "[PHASE3] daily_build_exit=$rc" -ForegroundColor Yellow
exit $rc
