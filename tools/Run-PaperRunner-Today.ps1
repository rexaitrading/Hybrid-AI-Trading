[CmdletBinding()]
param(
  [ValidateSet("SPY","QQQ")]
  [Parameter(Mandatory=$true)]
  [string]$Symbol,

  [int]$Ticks = 120,

  [int]$SleepMs = 350,

  [switch]$ProviderOnly,

  [switch]$Clean
)

Set-StrictMode -Version Latest
$ErrorActionPreference="Stop"

function Fail([string]$m){
  Write-Host ("[PAPER-RUNNER] FAIL-CLOSED: " + $m) -ForegroundColor Red
  exit 2
}

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
Set-Location -LiteralPath $repoRoot

$py = Join-Path $repoRoot ".venv\Scripts\python.exe"
if(-not (Test-Path -LiteralPath $py)){ Fail "missing python venv: $py" }

$lower = $Symbol.ToLowerInvariant()
$outRel  = ("logs/{0}_phase5_paperlive_results_with_micro_today.jsonl" -f $lower)
$outPath = Join-Path $repoRoot $outRel
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $outPath) | Out-Null

if($Clean -and (Test-Path -LiteralPath $outPath)){
  Remove-Item -LiteralPath $outPath -Force
}

$provArgs = @()
if($ProviderOnly){ $provArgs += '--provider-only' }

function LineCount([string]$p){
  if(-not (Test-Path -LiteralPath $p)){ return 0 }
  return (Get-Content -LiteralPath $p -Encoding utf8 | Measure-Object -Line).Lines
}

$startLines = LineCount $outPath
Write-Host ("[PAPER-RUNNER] START Symbol={0} ticks={1} sleepMs={2} out={3}" -f $Symbol,$Ticks,$SleepMs,$outRel) -ForegroundColor Cyan

for($i=1; $i -le $Ticks; $i++){
  & $py -m hybrid_ai_trading.runners.paper_runner `
    --once `
    --universe $Symbol `
    @provArgs `
    --log-file $outPath *>&1 | Out-Null

  if($LASTEXITCODE -ne 0){ Fail ("tick {0} exit={1}" -f $i,$LASTEXITCODE) }

  if($SleepMs -gt 0){ Start-Sleep -Milliseconds $SleepMs }

  if(($i % 10) -eq 0){
    $n = LineCount $outPath
    Write-Host ("[PAPER-RUNNER] tick {0}/{1} lines={2}" -f $i,$Ticks,$n) -ForegroundColor DarkGray
  }
}

$endLines = LineCount $outPath
Write-Host ("[PAPER-RUNNER] OK: Symbol={0} ticks={1} lines_start={2} lines_end={3} clean={4} providerOnly={5} => {6}" -f `
  $Symbol,$Ticks,$startLines,$endLines,[bool]$Clean,[bool]$ProviderOnly,$outRel) -ForegroundColor Green
exit 0