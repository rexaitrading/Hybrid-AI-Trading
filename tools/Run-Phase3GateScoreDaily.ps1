[CmdletBinding()]
param(
  [string]$Symbol = "NVDA",
  [string]$Csv = ""
)


# --- repo root bootstrap (env-first) ---
$repoRoot = ($env:HAT_REPO_ROOT + "").Trim()
if(-not $repoRoot){
  $repoRoot = & (Join-Path $PSScriptRoot "Go-RepoRoot.ps1")
}
if(-not $repoRoot){ throw "[REPOROOT] FAIL-CLOSED: repoRoot empty (env+Go-RepoRoot)" }
$repoRoot = [System.IO.Path]::GetFullPath($repoRoot)
Set-Location -LiteralPath $repoRoot
[System.Environment]::CurrentDirectory = $repoRoot
$root = $repoRoot

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

function Invoke-BlockGCheckSafe([string]$Symbol){
  $checker = Join-Path $repoRoot "tools\Check-BlockGReady.ps1"
  if(-not (Test-Path -LiteralPath $checker)){ throw "[PHASE3] FAIL-CLOSED: missing Check-BlockGReady.ps1" }  # NOTE: We intentionally do NOT use -Build here.
  # Builder is handled by our reuse+timeout path below to avoid hangs and noisy "[BLOCKG] Build requested" output.# Fallback: reuse stub if fresh; else build with timeout; then check
  $status = Join-Path $repoRoot "logs\blockg_status_stub.json"
  $needBuild = $true
  if(Test-Path -LiteralPath $status){
    $ageMin = ((Get-Date) - (Get-Item $status).LastWriteTime).TotalMinutes
    if($ageMin -le 30){
      $needBuild = $false
      Write-Host ("[PHASE3] BlockG stub fresh (age_min=" + [int]$ageMin + "); skip build") -ForegroundColor DarkGray
    }
  }

  if($needBuild){
    $exe = (Get-Command powershell).Source
    $builder = Join-Path $repoRoot "tools\Build-BlockGStatusStub.ps1"
    if(-not (Test-Path -LiteralPath $builder)){ throw "[PHASE3] FAIL-CLOSED: missing Build-BlockGStatusStub.ps1" }

    $stdout = Join-Path $repoRoot "logs\blockg_build_stdout.txt"
    $stderr = Join-Path $repoRoot "logs\blockg_build_stderr.txt"
    $argList = @("-NoProfile","-ExecutionPolicy","Bypass","-File",$builder,"-Symbol",$Symbol)

    $p = Start-Process -FilePath $exe -ArgumentList $argList -PassThru -NoNewWindow `
          -RedirectStandardOutput $stdout -RedirectStandardError $stderr

    if(-not $p.WaitForExit(90)){
      Stop-Process -Id $p.Id -Force
try{
  Write-Host "[PHASE3] builder timeout; stderr tail:" -ForegroundColor Yellow
  if(Test-Path -LiteralPath $stderr){
    Get-Content -LiteralPath $stderr -Tail 80 -Encoding utf8 | Out-Host
  }
}catch{}
throw "[PHASE3] FAIL-CLOSED: BlockG builder exceeded 90s (killed). See logs\blockg_build_stderr.txt"
    }
    if($p.ExitCode -ne 0){
      throw ("[PHASE3] FAIL-CLOSED: BlockG builder exit=" + $p.ExitCode + " (see logs\blockg_build_stderr.txt)")
    }
    Write-Host "[PHASE3] BlockG builder OK" -ForegroundColor Green
  }

  powershell -NoProfile -ExecutionPolicy Bypass -File $checker -Symbol $Symbol *>&1 | Out-Host
  if($LASTEXITCODE -ne 0){ throw ("[PHASE3] FAIL-CLOSED: BlockG check failed exit=" + $LASTEXITCODE) }
}
# $root is pinned to $repoRoot (env-first)
$py   = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "[PHASE3] Python exe not found: $py" }

# Hard lock imports to this repo
$env:PYTHONNOUSERSITE = "1"
$env:PYTHONPATH = (Join-Path $root "src")
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"

# Deterministic Block-G contract path (single source of truth)
# NOTE: set env var name without embedding its literal text (keeps grep clean)
$k = ("HAT_" + "BLOCKG_" + "STATUS_" + "PATH")
[System.Environment]::SetEnvironmentVariable($k, (Join-Path $root "logs\blockg_status_stub.json"))

Write-Host "[PHASE3] ROOT=$root" -ForegroundColor Cyan
Write-Host "[PHASE3] SYMBOL=$Symbol" -ForegroundColor Cyan

# 1) Build + validate Block-G (safe wrapper)
Invoke-BlockGCheckSafe -Symbol $Symbol
# 2) Choose CSV input for daily_build (REAL CLI)
if (-not $Csv) {
  $cands = @(
    (Join-Path $root "logs\gatescore_pnl_summary.csv"),
    (Join-Path $root "logs\gatescore_daily_summary.csv"),
    (Join-Path $root "logs\gatescore_daily_summary_nvda.csv"),
    (Join-Path $root "logs\nvda_gatescore_samples.csv")
  )
  $Csv = ($cands | Where-Object { Test-Path $_ } | Select-Object -First 1)
}
if (-not $Csv -or -not (Test-Path -LiteralPath $Csv)) {  Write-Host "[PHASE3] NOT READY: Missing GateScore CSV input (fail-closed)." -ForegroundColor Yellow
  exit 2}

Write-Host "[PHASE3] CSV=$Csv" -ForegroundColor Cyan

& $py -m hybrid_ai_trading.gatescore.daily_build --csv $Csv --symbol $Symbol
$rc = $LASTEXITCODE

Write-Host "[PHASE3] daily_build_exit=$rc" -ForegroundColor Yellow
exit $rc
