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

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"
chcp 65001 | Out-Null

$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

# --- output contract ---
$effectiveOutDir = "logs\bars"
if($OutDir -and $OutDir.Trim().Length -gt 0){ $effectiveOutDir = $OutDir.Trim() }

# absolute output dir + expected file
$barsDir  = Join-Path $repo $effectiveOutDir
New-Item -ItemType Directory -Force -Path $barsDir | Out-Null

$expected = Join-Path $barsDir ("{0}_{1}_1m.csv" -f $Symbol.ToUpperInvariant(), $AsOfDate)
# --- end contract ---

# python + fetcher
$py = Join-Path $repo ".venv\Scripts\python.exe"
if(-not (Test-Path -LiteralPath $py)){ throw "Missing venv python: $py" }

$ibHist = Join-Path $repo "src\hybrid_ai_trading\ib\ib_history_fetch.py"
if(-not (Test-Path -LiteralPath $ibHist)){ throw "Missing ib_history_fetch.py: $ibHist" }

# build args (match python --help)
$args = @(
  $ibHist,
  "--symbol", $Symbol,
  "--as-of-date", $AsOfDate,
  "--host", $IbHost,
  "--port", ([string]$Port),
  "--client-id", ([string]$ClientId),
  "--outdir", $effectiveOutDir
)
if($UseRth.IsPresent){ $args += @("--use-rth") }

Write-Host ("[IBKR] RUN: " + $py + " " + ($args -join " ")) -ForegroundColor Cyan

# run with cwd=repo so relative outdir works
$outAll = (& $py @args 2>&1 | Out-String)
$pyExit = $LASTEXITCODE
$outAll | Out-Host
Write-Host ("[IBKR] python_exit=" + $pyExit) -ForegroundColor DarkGray

# verify output
if(Test-Path -LiteralPath $expected){
  Write-Host ("[IBKR] OK wrote: " + $expected) -ForegroundColor Green
  exit 0
}

Write-Host ("[IBKR] FAIL-CLOSED: missing output file: " + $expected) -ForegroundColor Yellow
# preserve python failure signal if it failed, else contract failure
if($pyExit -ne 0){ exit $pyExit }
exit 2