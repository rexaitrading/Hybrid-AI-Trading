[CmdletBinding()]
param(
  [ValidateSet("US","JP","HK","SG","IN","KR","TW","HK_SH","HK_SZ")]
  [string]$Market = "US",

  [ValidateSet("NVDA","SPY","QQQ","ALL")]
  [string]$Symbol = "NVDA"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null

# --- repo root bootstrap (env-first) ---
$repoRoot = (($env:HAT_REPO_ROOT + "")).Trim()
if(-not $repoRoot){
  $repoRoot = & (Join-Path $PSScriptRoot "Go-RepoRoot.ps1")
}
if(-not $repoRoot){ throw "[REPOROOT] FAIL-CLOSED: repoRoot empty" }
$repoRoot = [System.IO.Path]::GetFullPath($repoRoot)
Set-Location -LiteralPath $repoRoot
[System.Environment]::CurrentDirectory = $repoRoot
if(-not (Test-Path ".\.git")){ throw "[FAIL-CLOSED] NOT IN REPO ROOT" }

# --- CLEAN MARKET / SYMBOL WIRE (NO QUOTES EVER) ---
$Market = (($Market + "")).Trim().ToUpperInvariant()
if(-not $Market){ $Market = (($env:HAT_MARKET + "")).Trim().ToUpperInvariant() }
if(-not $Market){ $Market = "US" }
$env:HAT_MARKET = $Market

$Symbol = (($Symbol + "")).Trim().ToUpperInvariant()
if(-not $Symbol){ $Symbol = "NVDA" }
$env:HAT_SYMBOL = $Symbol

function Run-Step([string]$name, [scriptblock]$sb){
  Write-Host "`n==================== $name ====================" -ForegroundColor Cyan
  & $sb
  Write-Host "[OK] $name" -ForegroundColor Green
}

# --- SAFE RUNNER (NO STRING[] ARGUMENTS) ---
function Run-PS([string]$path, [hashtable]$params=@()){
  if(-not (Test-Path $path)){ throw "Missing tool: $path" }

  $cmd = {
    param($ScriptPath, $Params)
    & $ScriptPath @Params
    exit $LASTEXITCODE
  }

  & powershell `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -Command $cmd `
    -Args $path, $params

  $code = [int]$LASTEXITCODE
  if($code -ne 0){ throw "Tool failed: $path exit=$code" }
}

function Run-PSAllowExit([string]$path, [int[]]$okExits, [hashtable]$params=@()){
  if(-not (Test-Path $path)){ throw "Missing tool: $path" }

  $cmd = {
    param($ScriptPath, $Params)
    & $ScriptPath @Params
    exit $LASTEXITCODE
  }

  & powershell `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -Command $cmd `
    -Args $path, $params

  $code = [int]$LASTEXITCODE
  if(-not ($okExits -contains $code)){
    throw "Tool failed: $path exit=$code"
  }
}

# ==================== PIPELINE ====================

Run-Step "Phase4: Stamp (todayness)" {
  Run-PS ".\tools\Run-Phase4Stamp.ps1" @{
    Market = $env:HAT_MARKET
    Symbol = $env:HAT_SYMBOL
  }
}

Run-Step "Phase23: Health daily" {
  Run-PS ".\tools\Run-Phase23HealthDaily.ps1" @{
    Market = $env:HAT_MARKET
    Symbol = $env:HAT_SYMBOL
  }
}

Run-Step "Phase5: EV-hard snapshot" {
  # EV-hard snapshot consumes env:HAT_MARKET internally; do NOT pass Market/Symbol
  Run-PS ".\tools\Build-EvHardSnapshot.ps1" @{}
}

Run-Step "Phase5: EV-hard daily veto row" {
  Run-PS ".\tools\Run-EvHardVetoDaily.ps1" @{
    Market = $env:HAT_MARKET
    Symbol = $env:HAT_SYMBOL
  }
}

Run-Step "Phase3: GateScore PnL summary" {
  Run-PS ".\tools\Build-GateScorePnlSummary.ps1" @{
    Market = $env:HAT_MARKET
    Symbol = $env:HAT_SYMBOL
  }
}

Run-Step "BlockG: Build contract" {
  Run-PS ".\tools\Build-BlockGStatusStub.ps1" @{
    Market = $env:HAT_MARKET
    Symbol = $env:HAT_SYMBOL
  }
}

Run-Step "BlockG: Contract-only checker" {
  Run-PSAllowExit ".\tools\Invoke-BlockGCheck.ps1" @(0,2) @{
    Market = $env:HAT_MARKET
    Symbol = $env:HAT_SYMBOL
    Mode   = "ALL_STRICT"
  }
}

Write-Host "`nDONE: Run-Phase1ToPhase7Daily completed." -ForegroundColor Yellow
exit 0

