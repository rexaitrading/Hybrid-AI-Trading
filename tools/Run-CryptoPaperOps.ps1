[CmdletBinding()]
param(
  [int]$TickSec = 60,
  [string]$Symbols = "BTC-USD,ETH-USD",
  [switch]$Once,
  [int]$Lookback = 10,
  [double]$Thr = 0.0005,
  [double]$UsdNotional = 25.0,
  [int]$CooldownSec = 0
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest
chcp 65001 | Out-Null

$repoRoot = "C:\HATJ\HybridAITrading"
Set-Location -LiteralPath $repoRoot
$env:HAT_REPO_ROOT = $repoRoot

$logDir = Join-Path $repoRoot "logs\crypto"
if(-not (Test-Path -LiteralPath $logDir)){ New-Item -ItemType Directory -Path $logDir | Out-Null }

$ts = (Get-Date).ToString("yyyyMMdd_HHmmss")
$runLog = Join-Path $logDir ("crypto_paperops_" + $ts + ".log")
$stopFile = Join-Path $logDir "STOP.txt"

function Log([string]$m){
  $line = ("[{0}] {1}" -f (Get-Date).ToString("o"), $m)
  $line | Tee-Object -FilePath $runLog -Append | Out-Host
}

$py = Join-Path $repoRoot ".venv\Scripts\python.exe"
if(-not (Test-Path -LiteralPath $py)){ throw "Missing python venv: $py" }

Log ("[CRYPTO] START PaperSim TickSec=" + $TickSec + " Symbols=" + $Symbols + " Once=" + $Once + " Lookback=" + $Lookback + " Thr=" + $Thr + " UsdNotional=" + $UsdNotional)

$iter = 0
while($true){
  $iter++

  if(-not $Once -and (Test-Path -LiteralPath $stopFile)){
    Log "[CRYPTO] STOP file present. Exiting loop."
    break
  }

  try{
    $args = @(
      "-m","hybrid_ai_trading.runners.crypto_paper_sim",
      "--symbols",$Symbols,
      "--outdir",$logDir,
      "--lookback",$Lookback,
      "--thr",$Thr,
      "--usd_notional",$UsdNotional,
      "--cooldown_sec",$CooldownSec
    )

    Log ("[CRYPTO] Iter=" + $iter + " Running: " + $py + " " + ($args -join " "))

    # Capture FULL python stdout+stderr into the run log
    & $py @args 2>&1 | Tee-Object -FilePath $runLog -Append | Out-Host

    $ec = $LASTEXITCODE
    Log ("[CRYPTO] Iter=" + $iter + " exit=" + $ec)
  } catch {
    Log ("[CRYPTO] Iter=" + $iter + " POWERSHELL_EXCEPTION:`n" + ($_ | Out-String))
    $ec = 2
  }

  if($Once){ break }
  Start-Sleep -Seconds $TickSec
}

Log "[CRYPTO] END"
exit 0

