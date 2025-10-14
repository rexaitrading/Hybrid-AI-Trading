cd "$PSScriptRoot\.."
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH="src"
$env:IB_HOST="127.0.0.1"; $env:IB_PORT="7497"; $env:IB_CLIENT_ID="201"
# Optional for IB dailyPnL guard
$env:IB_ACCOUNT="U21633271"

# Order policy
$env:TIF="IOC"; $env:TICK_CAP="20"; $env:MAX_NOTIONAL_USD="1000"
$env:OUTSIDE_RTH="true"; $env:ABORT_IF_NO_QUOTE="true"

# Risk Guard defaults
$env:TRADE_WINDOWS="06:35-12:45"
$env:MAX_SPREAD_BPS="8"
$env:MAX_DAILY_LOSS_USD="300"
$env:MAX_EXPOSURE_USD="5000"
$env:COOLDOWN_MIN="5"              # block for 5 minutes after a realized losing close
$env:ADAPTIVE_SPREAD_FACTOR="0.5"  # eff_bps = max(floor_bps, 0.5*spread_bps), clamped by TICK_CAP
$env:MAX_SLIPPAGE_BPS="20"

$Host.UI.RawUI.WindowTitle = "Hybrid Trading Console (Paper | IOC | Guards v2)"
Write-Host "[READY] Trading console loaded at $(Get-Location)" -ForegroundColor Green
python .\scripts\trading_status.py
Remove-Item Env:IB_ACCOUNT -ErrorAction SilentlyContinue
$env:SLACK_WEBHOOK="https://hooks.slack.com/services/REPLACE/ME/PLEASE"
$env:OPEN_AUCTION_WINDOW="06:29-06:30"
$env:CLOSE_AUCTION_WINDOW="12:59-13:00"
$env:MAX_SPREAD_BPS="12"
