[CmdletBinding()]
param(
  [switch]$Smooth,
  [double]$BtcStepMax = 15,
  [double]$EthStepMax = 2,
  [double]$MeanRevert = 0.10,
  [string]$CryptoDir = "",
  [switch]$Once,
  [int]$TickSec = 1,
  [double]$BtcBase = 43000,
  [double]$EthBase = 2300,
  [double]$BtcJitter = 200,
  [double]$EthJitter = 30
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest
chcp 65001 | Out-Null

$repoRoot="C:\HATJ\HybridAITrading"
$cryptoDir = if([string]::IsNullOrWhiteSpace($CryptoDir)){ (Join-Path $repoRoot "logs\crypto") } else { $CryptoDir }
New-Item -ItemType Directory -Path $cryptoDir -Force | Out-Null

$pricePath = Join-Path $cryptoDir "price_snapshot.json"
$stopFile  = Join-Path $cryptoDir "STOP_PRICE.txt"
$hbPath    = Join-Path $cryptoDir "price_demo_heartbeat.log"
$errPath   = Join-Path $cryptoDir "price_demo_error.log"


# Smooth mode state
$btcCur = [double]$BtcBase
$ethCur = [double]$EthBase

function Write-Utf8NoBomAtomic([string]$Path,[string]$Text){
  $tmp = $Path + ".tmp"
  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($tmp, $Text, $utf8NoBom)
  Move-Item -LiteralPath $tmp -Destination $Path -Force
}

"[{0}] [PRICE-DEMO] START price={1} ticksec={2} stop={3}" -f (Get-Date).ToString("o"), $pricePath, $TickSec, $stopFile |
  Out-File -FilePath $hbPath -Append -Encoding utf8

while($true){
  try {
    if(Test-Path -LiteralPath $stopFile){
      "[{0}] [PRICE-DEMO] STOP_PRICE detected. Exiting." -f (Get-Date).ToString("o") |
        Out-File -FilePath $hbPath -Append -Encoding utf8
      break
    }
    if($Smooth){
      # mean-reverting random walk (small steps)
      $btcStep = (Get-Random -Minimum (-1.0) -Maximum 1.0) * [double]$BtcStepMax
      $ethStep = (Get-Random -Minimum (-1.0) -Maximum 1.0) * [double]$EthStepMax

      # mean reversion toward base
      $btcCur = $btcCur + $btcStep + ([double]$MeanRevert * ([double]$BtcBase - $btcCur))
      $ethCur = $ethCur + $ethStep + ([double]$MeanRevert * ([double]$EthBase - $ethCur))

      $btc = [Math]::Round($btcCur, 2)
      $eth = [Math]::Round($ethCur, 2)
    } else {
      # legacy wide jitter
      $btc = [Math]::Round($BtcBase + (Get-Random -Minimum (-1*$BtcJitter) -Maximum ($BtcJitter+1)), 2)
      $eth = [Math]::Round($EthBase + (Get-Random -Minimum (-1*$EthJitter) -Maximum ($EthJitter+1)), 2)
    }
    $json = @"
{
  "BTC-USD": $btc,
  "ETH-USD": $eth
}
"@

    Write-Utf8NoBomAtomic -Path $pricePath -Text $json

    "[{0}] wrote btc={1} eth={2}" -f (Get-Date).ToString("o"), $btc, $eth |
      Out-File -FilePath $hbPath -Append -Encoding utf8
    if($Once){ break }

    Start-Sleep -Seconds $TickSec
  } catch {
    "[{0}] EXCEPTION:`n{1}" -f (Get-Date).ToString("o"), ($_ | Out-String) |
      Out-File -FilePath $errPath -Append -Encoding utf8
    throw
  }
}

exit 0


