[CmdletBinding()]
param(
  [switch]$Once,
  [int]$TickSec = 60,
  [string]$Symbols = "BTC-USD,ETH-USD",
  [switch]$WarmupNow
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest
chcp 65001 | Out-Null

$repo = "C:\HATJ\HybridAITrading"
Set-Location -LiteralPath $repo
$env:HAT_REPO_ROOT = $repo

$cryptoDir = Join-Path $repo "logs\crypto_asia"
New-Item -ItemType Directory -Path $cryptoDir -Force | Out-Null

# Heartbeat log (always)
$hb = Join-Path $cryptoDir "asia_ops_heartbeat.log"
function HB([string]$m){
  ("[{0}] {1}" -f (Get-Date).ToUniversalTime().ToString("o"), $m) | Out-File -FilePath $hb -Append -Encoding utf8
}
HB ("RUN_START utc=" + (Get-Date).ToUniversalTime().ToString("o"))

$py = Join-Path $repo ".venv\Scripts\python.exe"
if(-not (Test-Path -LiteralPath $py)){
  HB ("EXIT_NO_PY venv_missing=" + $py)
  exit 2
}

# Session gate (UTC 00:00-08:00)
& $py -c "from hybrid_ai_trading.runners.crypto_session import is_asia_session_utc; import sys; sys.exit(0 if is_asia_session_utc() else 10)"
if($LASTEXITCODE -ne 0){
  HB ("EXIT_OUTSIDE_SESSION utc=" + (Get-Date).ToUniversalTime().ToString("o"))
  exit 0
}

# ARM gate (Asia)
$allowFlag = Join-Path $cryptoDir "ALLOW_SIM.txt"
if(-not (Test-Path -LiteralPath $allowFlag)){
  HB ("EXIT_DISARMED utc=" + (Get-Date).ToUniversalTime().ToString("o"))
  exit 0
}

# Allow sim gate for this run (scheduled task environment)
$env:HAT_CRYPTO_ALLOW_SIM="1"

# Warmup micro-burst during Asia session: at the top of each hour (minute 0-1)
$nowUtc = (Get-Date).ToUniversalTime()
if($WarmupNow -or ($nowUtc.Minute -lt 2)){
  HB ("WARMUP_BURST_ON utc=" + $nowUtc.ToString("o") + " ticks=12 lookback=6 thr=0.00030 (calm) (hourly_micro)")
  for($i=1; $i -le 12; $i++){
    # Refresh snapshot (so sim sees moving prices)
    powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repo "tools\Write-CryptoPriceSnapshot-Demo.ps1") -CryptoDir $cryptoDir -Once -TickSec 1 -Smooth -BtcStepMax 10 -EthStepMax 0.8 -MeanRevert 0.15 | Out-Null
    # Refresh snapshot (so sim sees moving prices)
    powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repo "tools\Write-CryptoPriceSnapshot-Demo.ps1") -CryptoDir $cryptoDir -Once -TickSec 1 -Smooth -BtcStepMax 10 -EthStepMax 0.8 -MeanRevert 0.15 | Out-Null
    & $py -m hybrid_ai_trading.runners.crypto_paper_sim `
      --symbols $Symbols `
      --outdir $cryptoDir `
      --usd_notional 15 `
      --max_pos_usd 120 `
      --max_trades_per_hour 4 `
      --daily_loss_cap 15 `
      --daily_loss_cap_symbol 6 `
      --cooldown_sec 0 --min_hold_sec 15 `
      --lookback 6 --thr 0.00030 --dry_run | Out-Null
    Start-Sleep -Seconds 1
  }
  HB ("WARMUP_BURST_DONE utc=" + (Get-Date).ToUniversalTime().ToString("o"))
}

HB ("TICK_RUN utc=" + (Get-Date).ToUniversalTime().ToString("o"))

# Run Asia regime (tighter + lower risk)
    # Refresh snapshot (so sim sees moving prices)
    powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repo "tools\Write-CryptoPriceSnapshot-Demo.ps1") -CryptoDir $cryptoDir -Once -TickSec 1 -Smooth -BtcStepMax 10 -EthStepMax 0.8 -MeanRevert 0.15 | Out-Null
    # Refresh snapshot (so sim sees moving prices)
    powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $repo "tools\Write-CryptoPriceSnapshot-Demo.ps1") -CryptoDir $cryptoDir -Once -TickSec 1 -Smooth -BtcStepMax 10 -EthStepMax 0.8 -MeanRevert 0.15 | Out-Null
& $py -m hybrid_ai_trading.runners.crypto_paper_sim `
  --symbols $Symbols `
  --outdir $cryptoDir `
  --usd_notional 15 `
  --max_pos_usd 120 `
  --max_trades_per_hour 4 `
  --daily_loss_cap 15 `
  --daily_loss_cap_symbol 6 `
  --cooldown_sec 120 `
  --lookback 6 --thr 0.00030 | Out-Null

HB ("TICK_DONE utc=" + (Get-Date).ToUniversalTime().ToString("o") + " exit=" + $LASTEXITCODE)
exit 0

















