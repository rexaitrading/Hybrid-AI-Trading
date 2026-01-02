[CmdletBinding()]
param(
  [ValidateSet("NVDA","SPY","QQQ")]
  [string]$Symbol = "NVDA",

  [string]$IBGStatusPath = "C:\IBC\status\ibg_status.json",

  [switch]$BuildBlockG,
  [switch]$Quiet
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
chcp 65001 | Out-Null

# Repo root
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $repo

# Venv python
$py = Join-Path $repo '.venv\Scripts\python.exe'
if(-not (Test-Path -LiteralPath $py)){ throw "Missing venv python: $py" }

# LIVE mode (fail-closed rules apply)
$env:HAT_IS_PAPER        = "0"
$env:HAT_SYMBOL          = $Symbol
$env:HAT_IBG_STATUS_PATH = $IBGStatusPath

# --- Gate 1: IBG health (fresh status + portUp) ---
try{
  if(Test-Path -LiteralPath (Join-Path $repo 'tools\Get-IBGHealth.ps1')){
    $h = & (Join-Path $repo 'tools\Get-IBGHealth.ps1')
    if(-not $h.ok){
      if(-not $Quiet){
        Write-Host "[LIVE-DRYDRILL] IBG_HEALTH_FAIL" -ForegroundColor Red
        Write-Host ("reasons=" + ($h.reasons -join "; ")) -ForegroundColor Red
      }
      exit 3
    }
  } else {
    if(-not $Quiet){ Write-Host "[LIVE-DRYDRILL] WARN: tools\Get-IBGHealth.ps1 missing" -ForegroundColor Yellow }
  }
}catch{
  if(-not $Quiet){ Write-Host ("[LIVE-DRYDRILL] IBG_HEALTH_ERROR: " + $_.Exception.Message) -ForegroundColor Yellow }
  exit 3
}

# --- Gate 2: Block-G contract readiness (includes IBG gate from Check-BlockGReady) ---
$checker = Join-Path $repo 'tools\Check-BlockGReady.ps1'
if(-not (Test-Path -LiteralPath $checker)){ throw "Missing: $checker" }

$args = @('-Symbol', $Symbol, '-Quiet')
if($BuildBlockG){ $args += '-Build' }

& powershell -NoProfile -ExecutionPolicy Bypass -File $checker @args | Out-Null
$bgExit = $LASTEXITCODE
if($bgExit -ne 0){
  if(-not $Quiet){ Write-Host ("[LIVE-DRYDRILL] BLOCKG_DENY exit=" + $bgExit) -ForegroundColor Red }
  exit $bgExit
}

# --- Gate 3: Python-level live gate probe (no orders) ---
# Single-line payload (quote-safe). No here-strings. No replacements.
$code = "from hybrid_ai_trading.execution.blockg_enforce import require_blockg_ready_for_live; require_blockg_ready_for_live('$Symbol'); print('LIVE_DRYDRILL_OK')"
& $py -c $code | Out-Host
exit $LASTEXITCODE