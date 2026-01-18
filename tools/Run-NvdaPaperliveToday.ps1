[CmdletBinding()]
param(
  [int]$MinEvents = 120,

  [ValidateSet("US","JP","HK","SG","IN","KR","TW")]
  [string]$Market = ((($env:HAT_MARKET + "")).Trim().ToUpperInvariant()),

  [string]$AsOfDate = ((($env:HAT_ASOF_DATE + "")).Trim()),

  [string]$OutPath = "",

  [double]$Edge = 0.03,
  [double]$Micro = 0.60
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Set-Location $repoRoot
Set-Location $repoRoot

if(-not $Market){ $Market = "US" }
$Market = ($Market + "").Trim().ToUpperInvariant()

# FAIL-CLOSED: non-US must provide market day
if($Market -ne "US"){
  if(-not $AsOfDate){ throw ("[FAIL-CLOSED] missing AsOfDate for Market=" + $Market + " (set env:HAT_ASOF_DATE or pass -AsOfDate)") }
  if($AsOfDate.Length -ge 10){ $AsOfDate = $AsOfDate.Substring(0,10) }
  if($AsOfDate -notmatch '^\d{4}-\d{2}-\d{2}$'){ throw ("[FAIL-CLOSED] AsOfDate not yyyy-MM-dd: " + $AsOfDate) }
}

if(-not $OutPath){
  if($Market -eq "US"){
    # US legacy default (preserve existing consumers)
    $OutPath = (Join-Path $repoRoot "logs\nvda_phase5_paperlive_results_today.jsonl")
  } else {
    # Non-US per-market default
    $OutPath = (Join-Path $repoRoot ("logs\" + $Market + "\nvda_phase5_paperlive_results_today.jsonl"))
  }
}

$py = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "venv python not found at $py" }

Write-Host "[NVDA-PAPERLIVE] Building today paperlive inputs" -ForegroundColor Cyan

& $py -m hybrid_ai_trading.runners.nvda_paperlive_today `
  --out $OutPath `
  --market $Market `
  $(if($AsOfDate){ "--as-of-date", $AsOfDate }) `
  --n $MinEvents `
  --regime NVDA_BPLUS_LIVE `
  --edge ([string]$Edge) `
  --micro ([string]$Micro) `
  --pnl-samples 1 `
  --price 0.0 `
  --local-start 09:30:00

$ec = $LASTEXITCODE
if ($ec -ne 0) {
  Write-Host "[NVDA-PAPERLIVE] ERROR: producer exit=$ec" -ForegroundColor Red
  exit $ec
}

if (-not (Test-Path $OutPath)) {
  Write-Host "[NVDA-PAPERLIVE] ERROR: output not created: $OutPath" -ForegroundColor Red
  exit 2
}

$cnt = @(Get-Content $OutPath).Count
Write-Host "[NVDA-PAPERLIVE] Wrote rows=$cnt -> $OutPath" -ForegroundColor Green

if ($cnt -lt $MinEvents) {
  Write-Host "[NVDA-PAPERLIVE] ERROR: too few rows ($cnt < $MinEvents)" -ForegroundColor Red
  exit 4
}

exit 0
