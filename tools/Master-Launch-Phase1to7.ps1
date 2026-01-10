[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol = "NVDA",

  [int]$BlockGReuseMinutes = 5,
  [int]$BlockGTimeoutSec   = 90,

  # If BlockG builder times out, reuse existing stub (if present) instead of failing closed
  [switch]$BlockGFallbackToExistingStubOnTimeout,

  [switch]$SkipIntel,
  [switch]$SkipPaperOps,

  # Hold window at end (useful for transient launch/shortcut)
  [switch]$Hold
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
chcp 65001 | Out-Null

function Fail([string]$m){
  Write-Host ("[MASTER-LAUNCH] FAIL-CLOSED: " + $m) -ForegroundColor Red
  exit 2
}

function Write-Section([string]$title){
  Write-Host "`n====================" -ForegroundColor DarkGray
  Write-Host ("STEP: " + $title) -ForegroundColor Cyan
  Write-Host "====================" -ForegroundColor DarkGray
}

$global:__LAST_STEP = "<none>"
$global:__SUMMARY_PATH = $null

function Step([string]$name,[scriptblock]$sb){
  $global:__LAST_STEP = $name
  Write-Section $name

  try {
    & $sb
  } catch {
    Write-Host ("[MASTER-LAUNCH] TERMINATING ERROR in step: " + $name) -ForegroundColor Red
    Write-Host ("[MASTER-LAUNCH] " + $_.Exception.Message) -ForegroundColor Red
    $detail = ($_ | Out-String)
    if($detail){ $detail.TrimEnd() | Out-Host }

    if($global:__SUMMARY_PATH){
      @(
        "RESULT=FAIL"
        "END_TIME=" + (Get-Date).ToString("o")
        "LAST_STEP=" + $global:__LAST_STEP
        "ERROR=" + $_.Exception.Message
      ) | Add-Content -LiteralPath $global:__SUMMARY_PATH -Encoding utf8
    }
    exit 2
  }

  if($LASTEXITCODE -ne 0){
    Fail ("step failed (exit=" + $LASTEXITCODE + "): " + $name)
  }
}

# --- Repo root (canonical) ---
$repoRoot = & .\tools\Go-RepoRoot.ps1
if(-not $repoRoot){ Fail "Go-RepoRoot returned empty" }

$repoRoot = [System.IO.Path]::GetFullPath($repoRoot)
if(-not (Test-Path -LiteralPath $repoRoot)){ Fail "repoRoot not found: $repoRoot" }

Set-Location -LiteralPath $repoRoot
[System.Environment]::CurrentDirectory = $repoRoot
$env:HAT_REPO_ROOT = $repoRoot

$logsDir  = Join-Path $repoRoot "logs"
$intelDir = Join-Path $repoRoot "src\.intel"
New-Item -ItemType Directory -Force -Path $logsDir  | Out-Null
New-Item -ItemType Directory -Force -Path $intelDir | Out-Null

# --- Launch diag + summary ---
$launchDiag = Join-Path $logsDir ("launch_diag_" + (Get-Date).ToString("yyyyMMdd_HHmmss") + "_MASTER.txt")
$global:__SUMMARY_PATH = Join-Path $logsDir ("master_launch_summary_" + (Get-Date).ToString("yyyyMMdd_HHmmss") + ".txt")

$cmd = ""
try { $cmd = (Get-CimInstance Win32_Process -Filter ("ProcessId=" + $PID)).CommandLine } catch { $cmd = "<CIM_FAIL>" }

@(
  "TIME=" + (Get-Date).ToString("o")
  "PID=" + $PID
  "HOST=" + $Host.Name
  "PSVersion=" + $PSVersionTable.PSVersion.ToString()
  "Edition=" + $PSVersionTable.PSEdition
  "PSCommandPath=" + $PSCommandPath
  "PSScriptRoot=" + $PSScriptRoot
  "CommandLine=" + $cmd
  "CWD=" + (Get-Location).Path
  "SYMBOL=" + $Symbol
  "SkipIntel=" + [string]$SkipIntel
  "SkipPaperOps=" + [string]$SkipPaperOps
  "BlockGReuseMinutes=" + $BlockGReuseMinutes
  "BlockGTimeoutSec=" + $BlockGTimeoutSec
  "BlockGFallbackToExistingStubOnTimeout=" + [string]$BlockGFallbackToExistingStubOnTimeout
) | Set-Content -LiteralPath $launchDiag -Encoding utf8

@(
  "RESULT=RUNNING"
  "START_TIME=" + (Get-Date).ToString("o")
  "SYMBOL=" + $Symbol
  "LAUNCH_DIAG=" + $launchDiag
) | Set-Content -LiteralPath $global:__SUMMARY_PATH -Encoding utf8

Write-Host ("[LAUNCH-DIAG] " + $launchDiag) -ForegroundColor DarkGray
Write-Host ("[SUMMARY]     " + $global:__SUMMARY_PATH) -ForegroundColor DarkGray

# --- RunTool (hardened; suppress known pytest atexit noise; exit-code authoritative) ---
function RunTool([string]$rel,[string[]]$args=@()){
  $abs = Join-Path $repoRoot $rel
  if(-not (Test-Path -LiteralPath $abs)){ Fail ("Missing tool: " + $rel) }

  $global:LASTEXITCODE = 0
  $argv = @("-NoProfile","-ExecutionPolicy","Bypass","-File",$abs) + $args

  $prevEap = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    $out = & powershell @argv 2>&1
    $rc  = $LASTEXITCODE
  } finally {
    $ErrorActionPreference = $prevEap
  }

  # Print output, but optionally suppress the known pytest cleanup permission spam IF exit code is 0
  if($out){
    if($rc -eq 0){
      $s = ($out | Out-String)
      $isPytestCleanupNoise =
        ($s -match 'Exception ignored in atexit callback') -and
        ($s -match 'cleanup_numbered_dir') -and
        ($s -match 'pytest-of-') -and
        ($s -match 'PermissionError:\s*\[WinError 5\]')

      if($isPytestCleanupNoise){
        Write-Host "[MASTER-LAUNCH] NOTE: suppressed pytest atexit cleanup WinError5 noise (exit=0)" -ForegroundColor DarkGray
      } else {
        $out | Out-Host
      }
    } else {
      $out | Out-Host
    }
  }

  if($rc -ne 0){
    Fail ("tool failed exit=" + $rc + " file=" + $rel)
  }

  $global:LASTEXITCODE = 0
}

# -----------------------------
# Pipeline
# -----------------------------
Step "Load canonical secrets" {
  . (Join-Path $repoRoot "tools\Load-HatSecrets.ps1")
  "POLYGON_API_KEY_SET="     + [bool]($env:POLYGON_API_KEY)     | Out-Host
  "ALPACA_API_KEY_SET="      + [bool]($env:ALPACA_API_KEY)      | Out-Host
  "ALPACA_SECRET_KEY_SET="   + [bool]($env:ALPACA_SECRET_KEY)   | Out-Host
}

Step "Preflight directories" {
  New-Item -ItemType Directory -Force -Path $intelDir | Out-Null
  New-Item -ItemType Directory -Force -Path $logsDir  | Out-Null
}

if(-not $SkipIntel){
  Step "Intel: News"    { RunTool "tools\Run-IntelNews.ps1" }
  Step "Intel: YouTube" { RunTool "tools\Run-IntelYouTube.ps1" }
  Step "Intel: Full"    { RunTool "tools\Run-IntelPipeline-Full.ps1" @("-IntelMode","DEGRADED_OK") }
} else {
  Write-Host "[MASTER-LAUNCH] Intel steps skipped (SkipIntel=true)" -ForegroundColor Yellow
}

Step "Block-G build status stub (timeout/reuse)" {
  $status = Join-Path $logsDir "blockg_status_stub.json"
  $stdout = Join-Path $logsDir "blockg_build_stdout.txt"
  $stderr = Join-Path $logsDir "blockg_build_stderr.txt"

  if(Test-Path -LiteralPath $status){
    $ageMin = ((Get-Date) - (Get-Item $status).LastWriteTime).TotalMinutes
    if($ageMin -le $BlockGReuseMinutes){
      Write-Host ("[BLOCK-G] Using existing stub (age_min=" + [int]$ageMin + ")") -ForegroundColor Green
      $global:LASTEXITCODE = 0
      return
    }
  }

  $exe = (Get-Command powershell).Source
  $scriptPath = Join-Path $repoRoot "tools\Build-BlockGStatusStub.ps1"
  $argList = @("-NoProfile","-ExecutionPolicy","Bypass","-File",$scriptPath,"-Symbol",$Symbol)

  Write-Host ("[BLOCK-G] start : " + $scriptPath) -ForegroundColor DarkGray
  Write-Host ("[BLOCK-G] stdout: " + $stdout) -ForegroundColor DarkGray
  Write-Host ("[BLOCK-G] stderr: " + $stderr) -ForegroundColor DarkGray

  $p = Start-Process -FilePath $exe -ArgumentList $argList -PassThru -NoNewWindow `
        -RedirectStandardOutput $stdout -RedirectStandardError $stderr

  if(-not $p.WaitForExit($BlockGTimeoutSec)){
    Stop-Process -Id $p.Id -Force

    if($BlockGFallbackToExistingStubOnTimeout -and (Test-Path -LiteralPath $status)){
      Write-Host "[BLOCK-G] WARN: builder timed out; falling back to existing stub" -ForegroundColor Yellow
      $global:LASTEXITCODE = 0
      return
    }

    throw ("[BLOCK-G] FAIL-CLOSED: builder exceeded " + $BlockGTimeoutSec + "s (killed). See logs\blockg_build_stderr.txt")
  }

  if($p.ExitCode -ne 0){
    throw ("[BLOCK-G] FAIL-CLOSED: builder exit=" + $p.ExitCode + " (see logs\blockg_build_stderr.txt)")
  }

  Write-Host "[BLOCK-G] builder OK" -ForegroundColor Green
}

Step "Block-G readiness (FAIL-CLOSED)" { RunTool "tools\Check-BlockGReady.ps1" @("-Symbol",$Symbol) }

Step "Phase-5 risk tests (risk-first)" { RunTool "tools\Run-Phase5Tests.ps1" }

Step "Phase-1 Replay Suite"        { RunTool "tools\Run-Phase1ReplaySuite.ps1" }
Step "Phase-2/3 Quick"             { RunTool "tools\Run-Phase23Quick.ps1" }
Step "Phase-4 Validation"          { RunTool "tools\Run-Phase4Validation.ps1" }
Step "Phase-5 Safety Suite"        { RunTool "tools\Run-Phase5SafetySuite.ps1" }
Step "Phase-6 Portfolio State"     { RunTool "tools\Build-Phase6PortfolioState.ps1" }
Step "Phase-6 Portfolio Metrics"   { RunTool "tools\Build-Phase6PortfolioMetrics.ps1" }

# IMPORTANT: Phase-7 FAIL-CLOSED unless -Enable is passed
Step "Phase-7 Optimizer Daily"     { RunTool "tools\Run-Phase7OptimizerDaily.ps1" @("-Enable") }

if(-not $SkipPaperOps){
  Step "PaperLive Ops (SAFE)" { RunTool "tools\Start-PaperLiveOps.ps1" @("-Symbol",$Symbol) }
} else {
  Write-Host "[MASTER-LAUNCH] PaperLive Ops skipped (SkipPaperOps=true)" -ForegroundColor Yellow
}

@(
  "RESULT=OK"
  "END_TIME=" + (Get-Date).ToString("o")
  "LAST_STEP=" + $global:__LAST_STEP
) | Add-Content -LiteralPath $global:__SUMMARY_PATH -Encoding utf8

Write-Host "`n[MASTER-LAUNCH] GREEN: Phase1→Phase7 + Intel + BlockG + SAFE PaperLiveOps complete." -ForegroundColor Green
Write-Host ("[SUMMARY] " + $global:__SUMMARY_PATH) -ForegroundColor DarkGray

if($Hold){
  Write-Host "`n[MASTER-LAUNCH] Hold=true. Press Enter to close..." -ForegroundColor Yellow
  [void](Read-Host)
}

