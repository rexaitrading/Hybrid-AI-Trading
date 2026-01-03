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

# --- expected output file contract (truth source) ---
$effectiveOutDir = "logs\bars"
if($OutDir -and $OutDir.Trim().Length -gt 0){ $effectiveOutDir = $OutDir.Trim() }
$barsDir = Join-Path $repo $effectiveOutDir
$expected = Join-Path $barsDir ("{0}_{1}_1m.csv" -f $Symbol.ToUpperInvariant(), $AsOfDate)
# --- end contract ---

$py = Join-Path $repo ".venv\Scripts\python.exe"
if(-not (Test-Path $py)){ throw "Missing venv python: $py" }

try {
  $prev = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  
$ibHist = Join-Path $repo "src\hybrid_ai_trading\ib\ib_history_fetch.py"
} catch {
  Write-Host ("[IBKR] FAIL-CLOSED: exception in wrapper: " + $_.Exception.Message) -ForegroundColor Yellow
} finally {
  $ErrorActionPreference = $prev
}

if(Test-Path -LiteralPath $expected){
  exit 0
}
Write-Host ("[IBKR] FAIL-CLOSED: missing output file: " + $expected) -ForegroundColor Yellow
exit 2
