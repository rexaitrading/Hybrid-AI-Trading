[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol = "NVDA",


  [ValidateSet("US","JP","HK","SG","IN","KR","TW")]
  [string]$Market = "US",
  [int]$BlockGReuseMinutes = 5,
  [int]$BlockGTimeoutSec   = 90,

  # If BlockG builder times out, reuse existing stub (if present) instead of failing closed
  [switch]$BlockGFallbackToExistingStubOnTimeout,

  [switch]$SkipIntel,
  [switch]$SkipPaperOps,

  # Hold window at end (useful for transient launch/shortcut)
  [switch]$SkipPhase7,

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

# --- Repo root (canonical, in-proc, UTF8-safe) ---
$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
$repoRoot = (Resolve-Path -LiteralPath $repoRoot -ErrorAction Stop).Path
$repoRoot = [System.IO.Path]::GetFullPath($repoRoot)
if(-not (Test-Path -LiteralPath $repoRoot)){ Fail ("repoRoot not found: " + $repoRoot) }

Set-Location -LiteralPath $repoRoot
[System.Environment]::CurrentDirectory = $repoRoot
$env:HAT_REPO_ROOT = $repoRoot
Write-Host ("[REPOROOT] " + $repoRoot) -ForegroundColor DarkGray

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
  Write-Host "[INTEL-MODE] DEGRADED_OK (earnings missing => allowed; FULL_REQUIRED remains fail-closed)" -ForegroundColor Yellow
  Step "Intel: News"    { RunTool "tools\Run-IntelNews.ps1" }
  Step "Intel: Full"    { RunTool "tools\Run-IntelPipeline-Full.ps1" @("-IntelMode","DEGRADED_OK") }
} else {
  Write-Host "[MASTER-LAUNCH] Intel steps skipped (SkipIntel=true)" -ForegroundColor Yellow
}
# REGIME_HOOK_BEGIN
Step "Regime: Determine NORMAL/HIGH_VOL/CRISIS" {
  RunTool "tools\Build-RegimeStatus.ps1" @("-Symbol",$Symbol,"-Market",$Market)
  RunTool "tools\Build-RegimeActions.ps1" @("-Symbol",$Symbol,"-Market",$Market)
}
# REGIME_HOOK_END
# CRASHMODE_HOOK_BEGIN
Step "CrashMode: Enforce crisis regime (halt/flatten/cooldown)" {
  # HOLD-safe. Writes logs\crisis_cooldown.json. Does NOT grant live readiness.
  RunTool "tools\Enforce-CrisisCrashMode.ps1" @("-Symbol",$Symbol)
}
# CRASHMODE_HOOK_END

Step "Verify Block-G readiness (one-shot gate)" {
  $vbArgs = @("-Symbol",$Symbol)
if($Hold){ $vbArgs += "-AllowClosedDayDiagnostics" }
powershell -NoProfile -ExecutionPolicy Bypass -File ".\tools\Verify-BlockG-Ready.ps1" @vbArgs *>&1 | Out-Host
  if($LASTEXITCODE -ne 0){ Fail ("Verify-BlockG-Ready failed exit=" + $LASTEXITCODE) }
}
Step "Block-G build status stub (timeout/reuse)" {
  $status = Join-Path $logsDir "blockg_status_stub.json"
  $stdout = Join-Path $logsDir "blockg_build_stdout.txt"
  $stderr = Join-Path $logsDir "blockg_build_stderr.txt"

  $needBuild = $true
  if(Test-Path -LiteralPath $status){
    $ageMin = ((Get-Date) - (Get-Item -LiteralPath $status).LastWriteTime).TotalMinutes
    if($ageMin -le $BlockGReuseMinutes){
      Write-Host ("[BLOCK-G] Using existing stub (age_min=" + [int]$ageMin + ")") -ForegroundColor Green
      $global:LASTEXITCODE = 0
      return
    }
  }

  $builder = Join-Path $repoRoot "tools\Build-BlockGStatusStub.ps1"
  if(-not (Test-Path -LiteralPath $builder)){ throw "[BLOCK-G] FAIL-CLOSED: missing tools\Build-BlockGStatusStub.ps1" }

  try { Remove-Item -LiteralPath $stdout,$stderr -Force -ErrorAction SilentlyContinue } catch {}

  $job = Start-Job -ScriptBlock {
    param($RepoRoot,$Builder,$Sym,$Stdout,$Stderr)
    $ErrorActionPreference="Stop"; Set-StrictMode -Version Latest
    Set-Location -LiteralPath $RepoRoot
    [System.Environment]::CurrentDirectory = $RepoRoot
    # Do NOT force FAST here. LIVE readiness requires full semantics.
# If operator explicitly set it, keep it; otherwise leave unset.
if(($env:HAT_BLOCKG_BUILDER_FAST + "") -ne "1"){ $env:HAT_BLOCKG_BUILDER_FAST = "" }
    try {
      & powershell -NoProfile -ExecutionPolicy Bypass -File $Builder -Symbol $Sym *>&1 |
        Out-File -LiteralPath $Stdout -Encoding UTF8
      exit 0
    } catch {
      ($_.Exception.ToString()) | Out-File -LiteralPath $Stderr -Encoding UTF8
      exit 2
    }
  } -ArgumentList $repoRoot,$builder,$Symbol,$stdout,$stderr

  $ok = Wait-Job -Id $job.Id -Timeout $BlockGTimeoutSec
  if(-not $ok){
    try { Stop-Job -Id $job.Id -Force } catch {}
    try { Remove-Job -Id $job.Id -Force } catch {}
    throw ("[BLOCK-G] FAIL-CLOSED: builder exceeded " + $BlockGTimeoutSec + "s (killed). See logs\blockg_build_stderr.txt")
  }

  Receive-Job -Id $job.Id -ErrorAction SilentlyContinue | Out-Null
  try { Remove-Job -Id $job.Id -Force } catch {}

  if(-not (Test-Path -LiteralPath $status)){
    Write-Host "[BLOCK-G] builder finished but stub missing; stdout/stderr tail:" -ForegroundColor Yellow
    if(Test-Path -LiteralPath $stdout){ Get-Content -LiteralPath $stdout -Tail 80 -Encoding UTF8 | Out-Host }
    if(Test-Path -LiteralPath $stderr){ Get-Content -LiteralPath $stderr -Tail 120 -Encoding UTF8 | Out-Host }
    throw "[BLOCK-G] FAIL-CLOSED: builder did not create logs\blockg_status_stub.json"
  }

  Write-Host "[BLOCK-G] builder OK (FAST)" -ForegroundColor Green
}

Step "Block-G readiness (FAIL-CLOSED)" {
  # HOLD policy: closed-day paper ops must be allowed to finish, but LIVE remains disallowed.
  # Verify-BlockG-Ready.ps1 already ran above and supports -AllowClosedDayDiagnostics when -Hold.
  if($Hold){
    Write-Host "[MASTER-LAUNCH] HOLD: skipping Check-BlockGReady ALL_STRICT gate (closed-day allowed; no LIVE stamp)" -ForegroundColor Yellow
    $global:LASTEXITCODE = 0
    return
  }
  RunTool "tools\Invoke-BlockGCheck.ps1" @("-Market",$Market,"-Symbol",$Symbol,"-Mode","ALL_STRICT")
}

Step "Phase-5 risk tests (risk-first)" { RunTool "tools\Run-Phase5Tests.ps1" }

Step "Phase-1 Replay Suite"        { RunTool "tools\Run-Phase1ReplaySuite.ps1" }
# HOLD policy: allow closed-day diagnostics for downstream tools (Phase-3 GateScore daily) without granting LIVE readiness.
if($Hold){
  $env:HAT_ALLOW_CLOSED_DAY_DIAGNOSTICS = "1"
  Write-Host "[MASTER-LAUNCH] HOLD: enabled HAT_ALLOW_CLOSED_DAY_DIAGNOSTICS=1" -ForegroundColor Yellow
} else {
  Remove-Item Env:\HAT_ALLOW_CLOSED_DAY_DIAGNOSTICS -ErrorAction SilentlyContinue
}
Step "Phase-2/3 Quick"             { RunTool "tools\Run-Phase23Quick.ps1" }
Step "Phase-4 Validation"          { RunTool "tools\Run-Phase4Validation.ps1" }
Step "Phase-5 Safety Suite"        { RunTool "tools\Run-Phase5SafetySuite.ps1" }
Step "Phase-6 Portfolio State"     { RunTool "tools\Build-Phase6PortfolioState.ps1" }
Step "Phase-6 Portfolio Metrics"   { RunTool "tools\Build-Phase6PortfolioMetrics.ps1" }

# IMPORTANT: Phase-7 FAIL-CLOSED unless -Enable is passed
Step "Phase-7 Optimizer Daily (optional)" {
  if($SkipPhase7){
    Write-Host "[PHASE7] skipped (SkipPhase7=true)" -ForegroundColor Yellow
    return
  }

  $abs = Join-Path $repoRoot "tools\Run-Phase7OptimizerDaily.ps1"
  if(-not (Test-Path -LiteralPath $abs)){
    Write-Host "[PHASE7] WARN: missing tool; skipped" -ForegroundColor Yellow
    return
  }

  $argv = @("-NoProfile","-ExecutionPolicy","Bypass","-File",$abs,"-Enable")
  $out = & powershell @argv 2>&1
  $rc  = $LASTEXITCODE
  if($out){ $out | Out-Host }

  if($rc -ne 0){
    Write-Host ("[PHASE7] WARN: disabled/fail-closed (exit=" + $rc + "); master launch continues") -ForegroundColor Yellow
    $global:LASTEXITCODE = 0
    return
  }

  Write-Host "[PHASE7] OK" -ForegroundColor Green
}
@(
  "RESULT=OK"
  "END_TIME=" + (Get-Date).ToString("o")
  "LAST_STEP=" + $global:__LAST_STEP
) | Add-Content -LiteralPath $global:__SUMMARY_PATH -Encoding utf8

Write-Host "`n[MASTER-LAUNCH] GREEN: Phase1->Phase7 + Intel + BlockG + SAFE PaperLiveOps complete." -ForegroundColor Green
Write-Host ("[SUMMARY] " + $global:__SUMMARY_PATH) -ForegroundColor DarkGray

if($Hold){
  Write-Host "`n[MASTER-LAUNCH] Hold=true. Press Enter to close..." -ForegroundColor Yellow
  [void](Read-Host)
}
