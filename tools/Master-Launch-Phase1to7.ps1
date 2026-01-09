[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol = "NVDA"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null

function Fail([string]$m){
  Write-Host ("[MASTER-LAUNCH] FAIL-CLOSED: " + $m) -ForegroundColor Red
  exit 2
}

function Step([string]$name,[scriptblock]$sb){
  Write-Host "`n====================" -ForegroundColor DarkGray
  Write-Host ("STEP: " + $name) -ForegroundColor Cyan
  Write-Host "====================" -ForegroundColor DarkGray
  & $sb
  if($LASTEXITCODE -ne 0){ Fail ("step failed (exit=" + $LASTEXITCODE + "): " + $name) }
}

# --- Repo root (canonical) ---
$repoRoot = & (Join-Path $PSScriptRoot "Go-RepoRoot.ps1")
if(-not $repoRoot){ Fail "Go-RepoRoot returned empty" }
$repoRoot = [System.IO.Path]::GetFullPath($repoRoot)
if(-not (Test-Path -LiteralPath $repoRoot)){ Fail "repoRoot not found: $repoRoot" }
Set-Location -LiteralPath $repoRoot
[System.Environment]::CurrentDirectory = $repoRoot
$env:HAT_REPO_ROOT = $repoRoot

function RunTool([string]$rel,[string[]]$args=@()){
  $abs = Join-Path $repoRoot $rel
  if(-not (Test-Path -LiteralPath $abs)){ Fail ("Missing tool: " + $rel) }
  $argv = @("-NoProfile","-ExecutionPolicy","Bypass","-File",$abs) + $args
  & powershell @argv 2>&1 | Out-Host
  if($LASTEXITCODE -ne 0){ Fail ("tool failed exit=" + $LASTEXITCODE + " file=" + $rel) }
}

Step "Load canonical secrets" {
  . (Join-Path $repoRoot "tools\Load-HatSecrets.ps1")
  "POLYGON_API_KEY_SET=" + [bool]($env:POLYGON_API_KEY) | Out-Host
  "ALPACA_API_KEY_SET=" + [bool]($env:ALPACA_API_KEY) | Out-Host
  "ALPACA_SECRET_KEY_SET=" + [bool]($env:ALPACA_SECRET_KEY) | Out-Host
}

Step "Preflight directories" {
  New-Item -ItemType Directory -Force -Path (Join-Path $repoRoot "src\.intel") | Out-Null
  New-Item -ItemType Directory -Force -Path (Join-Path $repoRoot "logs") | Out-Null
}

# -------- Intel feeds --------
Step "Intel: News"    { RunTool "tools\Run-IntelNews.ps1" }
Step "Intel: YouTube" { RunTool "tools\Run-IntelYouTube.ps1" }
Step "Intel: Full"    { RunTool "tools\Run-IntelPipeline-Full.ps1" }

# -------- Block-G stub (reuse if fresh; else rebuild with timeout) --------
Step "Block-G status stub (reuse<=30m, else build timeout 90s + fallback)" {
  $status = Join-Path $repoRoot "logs\blockg_status_stub.json"
  $hasStub = Test-Path -LiteralPath $status

  if($hasStub){
    $ageMin = ((Get-Date) - (Get-Item $status).LastWriteTime).TotalMinutes
    if($ageMin -le 30){
      Write-Host ("[BLOCK-G] Using existing stub (age_min=" + [int]$ageMin + ")") -ForegroundColor Green
      $global:LASTEXITCODE = 0
      return
    }
    Write-Host ("[BLOCK-G] Stub stale (age_min=" + [int]$ageMin + "); attempt rebuild") -ForegroundColor Yellow
  } else {
    Write-Host "[BLOCK-G] Stub missing; must build" -ForegroundColor Yellow
  }

  $exe = (Get-Command powershell).Source
  $builder = Join-Path $repoRoot "tools\Build-BlockGStatusStub.ps1"
  $stdout = Join-Path $repoRoot "logs\blockg_build_stdout.txt"
  $stderr = Join-Path $repoRoot "logs\blockg_build_stderr.txt"
  $argList = @("-NoProfile","-ExecutionPolicy","Bypass","-File",$builder,"-Symbol",$Symbol)

  $p = Start-Process -FilePath $exe -ArgumentList $argList -PassThru -NoNewWindow `
        -RedirectStandardOutput $stdout -RedirectStandardError $stderr

  if(-not $p.WaitForExit(90)){
    Stop-Process -Id $p.Id -Force
    if($hasStub){
      Write-Host "[BLOCK-G] WARN: builder timed out; falling back to existing stub" -ForegroundColor Yellow
      $global:LASTEXITCODE = 0
      return
    }
    throw "[BLOCK-G] FAIL-CLOSED: builder exceeded 90s (killed) and no stub exists. See logs\blockg_build_stderr.txt"
  }

  if($p.ExitCode -ne 0){
    if($hasStub){
      Write-Host ("[BLOCK-G] WARN: builder exit=" + $p.ExitCode + "; falling back to existing stub") -ForegroundColor Yellow
      $global:LASTEXITCODE = 0
      return
    }
    throw ("[BLOCK-G] FAIL-CLOSED: builder exit=" + $p.ExitCode + " and no stub exists. See logs\blockg_build_stderr.txt")
  }

  Write-Host "[BLOCK-G] builder OK" -ForegroundColor Green
}
 
Step "Block-G readiness (FAIL-CLOSED)" { RunTool "tools\Check-BlockGReady.ps1" @("-Symbol",$Symbol) }

# -------- Risk tests --------
Step "Phase-5 risk tests" { RunTool "tools\Run-Phase5Tests.ps1" }

# -------- Phase1Phase7 --------
Step "Phase-1 Replay Suite" { RunTool "tools\Run-Phase1ReplaySuite.ps1" }
Step "Phase-2/3 Quick"      { RunTool "tools\Run-Phase23Quick.ps1" }
Step "Phase-4 Validation"   { RunTool "tools\Run-Phase4Validation.ps1" }
Step "Phase-5 Safety Suite" { RunTool "tools\Run-Phase5SafetySuite.ps1" }
Step "Phase-6 Portfolio State"   { RunTool "tools\Build-Phase6PortfolioState.ps1" }
Step "Phase-6 Portfolio Metrics" { RunTool "tools\Build-Phase6PortfolioMetrics.ps1" }
Step "Phase-7 Optimizer Daily"   { RunTool "tools\Run-Phase7OptimizerDaily.ps1" "-Enable" }
# -------- SAFE ops --------
Step "PaperLive Ops (SAFE)" { RunTool "tools\Start-PaperLiveOps.ps1" @("-Symbol",$Symbol) }

Write-Host "`n[MASTER-LAUNCH] GREEN: Phase1Phase7 + Intel + BlockG + SAFE PaperLiveOps complete." -ForegroundColor Green
exit 0
