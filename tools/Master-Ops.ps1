[CmdletBinding()]
param(
  [Parameter(Position=0)]
  [ValidateSet("START","CHECK","LOCK")]
  [string]$Cmd = "CHECK",

  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol = "NVDA",

  [switch]$Weekly,

  # Optional: enable SPY/QQQ checks inside FinalLock/BlockG builder
  [switch]$EnableSpyQqq,

  # For START: prefer IB snapshots when healthy (recommended)
  [switch]$UseIBSnapshotsWhenHealthy
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

$toolsDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $toolsDir
Set-Location $repoRoot

function Say([string]$msg){ Write-Host ("[MASTER] " + $msg) -ForegroundColor Cyan }
function Warn([string]$msg){ Write-Warning ("[MASTER] " + $msg) }
function Fail([string]$msg){ Write-Host ("[MASTER] FAIL-CLOSED: " + $msg) -ForegroundColor Yellow; exit 2 }

# -----------------------------
# HARD paper-only safety
# -----------------------------
$env:HAT_IS_PAPER = "1"
$env:HAT_LIVE_DISABLED = "1"
Remove-Item Env:\HAT_CONFIRM_LIVE -ErrorAction SilentlyContinue

# Ensure IBG status path is visible to THIS process + child processes (tests/guards)
try {
  $u = [System.Environment]::GetEnvironmentVariable("HAT_IBG_STATUS_PATH","User")
  if(-not [string]::IsNullOrWhiteSpace($u)){
    $env:HAT_IBG_STATUS_PATH = $u
  }
} catch { }

# -----------------------------
# Helpers
# -----------------------------
function Show-Health {
  Say "RepoRoot=$repoRoot"
  Say ("IBG_USER=" + [string]([System.Environment]::GetEnvironmentVariable("HAT_IBG_STATUS_PATH","User")))
  if(Test-Path -LiteralPath (Join-Path $toolsDir "Get-IBGHealth.ps1")){
    try {
      $h = & (Join-Path $toolsDir "Get-IBGHealth.ps1")
      ($h | ConvertTo-Json -Depth 4) | Out-Host
    } catch {
      Warn ("Get-IBGHealth failed: " + $_.Exception.Message)
    }
  } else {
    Warn "Missing tools/Get-IBGHealth.ps1"
  }
}

function Daily-Check {
  Say "DAILY CHECK"
  Show-Health

  $hb = Join-Path $repoRoot "logs\paper_live_heartbeat.json"
  if(Test-Path -LiteralPath $hb){
    Say "HEARTBEAT tail1:"
    Get-Content $hb -Tail 1 -Encoding utf8 | Out-Host
  } else {
    Warn "Missing heartbeat: $hb (paper-live may not be running)"
  }

  $intelDir = Join-Path $repoRoot "src\.intel"
  if(Test-Path -LiteralPath $intelDir){
    Say "INTEL freshness (top 5):"
    Get-ChildItem $intelDir -File -ErrorAction SilentlyContinue |
      Sort-Object LastWriteTime -Descending |
      Select-Object -First 5 Name,LastWriteTime,Length |
      Format-Table -AutoSize | Out-Host
  } else {
    Warn "Missing intel dir: $intelDir"
  }
}

function Weekly-Check {
  Say "WEEKLY CHECK (drift)"
  $latest = Get-ChildItem (Join-Path $repoRoot "logs") -File -Filter "paper_live_$Symbol*.jsonl" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if($latest){
    Say ("Latest decisions file=" + $latest.FullName)
    Get-Content $latest.FullName -Tail 50 -Encoding utf8 | Out-Host
  } else {
    Warn "No paper_live JSONL found for Symbol=$Symbol"
  }

  $intelDir = Join-Path $repoRoot "src\.intel"
  if(Test-Path -LiteralPath $intelDir){
    Say "INTEL freshness (top 20):"
    Get-ChildItem $intelDir -File -ErrorAction SilentlyContinue |
      Sort-Object LastWriteTime -Descending |
      Select-Object -First 20 Name,LastWriteTime,Length |
      Format-Table -AutoSize | Out-Host
  }
}

function Do-Lock {
  # Weekend/weekday router
  $dow = (Get-Date).DayOfWeek
  $isWeekend = ($dow -eq "Saturday" -or $dow -eq "Sunday")

  if($isWeekend){
    Say "LOCK: weekend -> Run-FinalLock WEEKEND"
    $final = Join-Path $toolsDir "Run-FinalLock.ps1"
    if(-not (Test-Path -LiteralPath $final)){ Fail "Missing tools/Run-FinalLock.ps1" }

    if($EnableSpyQqq){
      & $final -Mode WEEKEND -Symbols ALL -EnableSpyQqq -SkipNotionExport | Out-Host
    } else {
      & $final -Mode WEEKEND -Symbols NVDA -SkipNotionExport | Out-Host
    }
    if($LASTEXITCODE -ne 0){ Fail "Run-FinalLock failed rc=$LASTEXITCODE" }
    Say "LOCK OK (weekend)"
    return
  }

  Say "LOCK: weekday -> Run-WeekdayPreMarketLock"
  $wk = Join-Path $toolsDir "Run-WeekdayPreMarketLock.ps1"
  if(-not (Test-Path -LiteralPath $wk)){ Fail "Missing tools/Run-WeekdayPreMarketLock.ps1" }

  if($EnableSpyQqq){
    & $wk -Symbols NVDA -EnableSpyQqq -StrictPhase7 | Out-Host
  } else {
    & $wk -Symbols NVDA -StrictPhase7 | Out-Host
  }
  if($LASTEXITCODE -ne 0){ Fail "Run-WeekdayPreMarketLock failed rc=$LASTEXITCODE" }
  Say "LOCK OK (weekday)"
}

function Do-Start {
  Say "START: launching INTEL + PAPER-LIVE (paper-only)"
  $starter = Join-Path $toolsDir "Start-PaperLiveOps.ps1"
  if(-not (Test-Path -LiteralPath $starter)){ Fail "Missing tools/Start-PaperLiveOps.ps1" }

  if($UseIBSnapshotsWhenHealthy){
    & $starter -Symbol $Symbol -UseIBSnapshotsWhenHealthy | Out-Host
  } else {
    & $starter -Symbol $Symbol | Out-Host
  }
}

# -----------------------------
# Main
# -----------------------------
switch($Cmd){
  "START" { Do-Start; exit 0 }
  "LOCK"  { Do-Lock; exit 0 }
  "CHECK" {
    Daily-Check
    if($Weekly){ Weekly-Check }
    exit 0
  }
}
