[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ")] [string]$Symbol="NVDA",
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","CN_SH","CN_SZ")] [string]$Market="US"
)
Set-StrictMode -Version Latest

function Get-CanonicalRepoRoot {
  # FAIL-CLOSED canonical repo root (prefer env:HAT_REPO_ROOT if valid)
  $envRoot = ($env:HAT_REPO_ROOT + "").Trim()
  if($envRoot){
    try {
      $r = (Resolve-Path -LiteralPath $envRoot -ErrorAction Stop).Path
      if(Test-Path -LiteralPath (Join-Path $r ".git")){ return $r }
    } catch { }
  }
  $p = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..") -ErrorAction Stop).Path
  while($p -and -not (Test-Path -LiteralPath (Join-Path $p ".git"))){
    $parent = Split-Path -Parent $p
    if(-not $parent -or $parent -eq $p){ break }
    $p = $parent
  }
  if(-not $p -or -not (Test-Path -LiteralPath (Join-Path $p ".git"))){
    throw "[FAIL-CLOSED] repo root not found (.git missing). envRoot=$envRoot scriptRoot=$PSScriptRoot"
  }
  return $p
}

function Get-CanonicalLogRoot([string]$RepoRoot,[string]$Market){
  $m = ([string]$Market).ToUpperInvariant().Trim()
  if(-not $m){ $m = "US" }
  $repoFull = (Resolve-Path -LiteralPath $RepoRoot -ErrorAction Stop).Path
  if(-not (Test-Path -LiteralPath (Join-Path $repoFull ".git"))){
    throw "[FAIL-CLOSED] repo root missing .git: $repoFull"
  }
  $logRoot = Join-Path (Join-Path $repoFull "logs") $m
  if($logRoot -notlike ($repoFull + "*")){
    throw "[FAIL-CLOSED] logRoot escaped repo: logRoot=$logRoot repo=$repoFull"
  }
  New-Item -ItemType Directory -Force -Path $logRoot | Out-Null
  return $logRoot
}

$ErrorActionPreference="Stop"

$toolsDir = Split-Path -Parent $PSCommandPath
$ready = Join-Path $toolsDir "Check-BlockGReady.ps1"
$diag  = Join-Path $toolsDir "Check-BlockGDiagnosticOk.ps1"
# ---- RunContext gate: this test only applies on CLOSED days ----
try {
  $repo = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
  $psExe = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
  $rr = Get-CanonicalRepoRoot
  $rcRaw = & (Join-Path $rr "tools\Resolve-RunContext.ps1") -Market $Market -Symbol $Symbol | Out-String
  $rcRaw = ($rcRaw + "").Trim()
  if($rcRaw){
    $rc = $rcRaw | ConvertFrom-Json
    $closed = $false
    $tradingDay = $true
    if($rc.PSObject.Properties.Name -contains "market_closed_today"){ $closed = [bool]$rc.market_closed_today }
    if($rc.PSObject.Properties.Name -contains "is_trading_day"){ $tradingDay = [bool]$rc.is_trading_day }

    # If it is a normal trading day, this "weekend semantics" test must be skipped.
    if((-not $closed) -and $tradingDay){
      Write-Host ("[TEST] SKIP BlockGWeekendSemantics: not closed day (market_closed_today=false, is_trading_day=true) market=" + $Market) -ForegroundColor Yellow
      exit 0
    }
  }
} catch {
  # Fail-closed on uncertainty: DO NOT skip.
}
# ---- end RunContext gate ----
# 1) Live gate must be fail-closed on weekends/closed days (exit 10)
powershell -NoProfile -ExecutionPolicy Bypass -File $ready -Market $Market -Symbol $Symbol | Out-Host
$codeReady = $LASTEXITCODE

# 2) Diagnostic gate must succeed on weekends/closed days (exit 0)
powershell -NoProfile -ExecutionPolicy Bypass -File $diag -Market $Market -Symbol $Symbol | Out-Host
$codeDiag = $LASTEXITCODE

# Weekend/closed-day expected behavior:
# - Ready returns 10 (diagnostic ok but live disallowed)
# - Diag returns 0
if($codeReady -ne 10){ throw "[TEST] Expected Check-BlockGReady exit=10 on closed day, got=$codeReady" }
if($codeDiag -ne 0){ throw "[TEST] Expected Check-BlockGDiagnosticOk exit=0 on closed day, got=$codeDiag" }

Write-Host "[TEST] BlockG closed-day semantics OK (ready=10 diag=0)" -ForegroundColor Green
exit 0
