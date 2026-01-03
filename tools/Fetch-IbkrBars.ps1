[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$Symbol,
  [Parameter(Mandatory=$true)][string]$AsOfDate,  # YYYY-MM-DD
  [string]$IbHost="127.0.0.1",
  [int]$Port=4002,
  [int]$ClientId=77,
  [switch]$UseRth,
  [string]$OutDir=""
)
$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest

$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$py = Join-Path $repo ".venv\Scripts\python.exe"
if(-not (Test-Path $py)){ throw "Missing venv python: $py" }

$ibHist = Join-Path $repo "src\hybrid_ai_trading\ib\ib_history_fetch.py"
if(-not (Test-Path $ibHist)){
  Write-Host "[IBKR] FAIL-CLOSED: missing history fetcher: $ibHist" -ForegroundColor Yellow
  Write-Host "[IBKR] Use tools\Put-BarsCsv.ps1 to populate logs\bars\SYMBOL_YYYY-MM-DD_1m.csv for now." -ForegroundColor Yellow
  exit 2
}
# [patched] invocation built below

# --- build CLI args (flags confirmed by ib_history_fetch -h) ---
$argv = @("--symbol",$Symbol,"--as-of-date",$AsOfDate,"--host",$IbHost,"--port",$Port,"--client-id",$ClientId)
if($UseRth){ $argv += @("--use-rth") }
if($OutDir -and $OutDir.Trim().Length -gt 0){ $argv += @("--outdir",$OutDir) }

& $py -m hybrid_ai_trading.ib.ib_history_fetch @argv
# --- end args ---
if($LASTEXITCODE -eq 0){
  exit 0
}
Write-Host ("[IBKR] FAIL-CLOSED: underlying exit=" + $LASTEXITCODE + " -> mapping to 2") -ForegroundColor Yellow
exit 2