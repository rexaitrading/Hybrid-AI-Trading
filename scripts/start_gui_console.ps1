# --- SETTINGS (adjust TWS path if different) ---
$twsExe   = "C:\Jts\tws.exe"           # <-- change if your TWS is elsewhere
$port     = 7497                       # Paper
$maxWaitS = 180

# --- Activate repo + env ---
cd "$PSScriptRoot\.."
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH="src"
$env:IB_HOST="127.0.0.1"; $env:IB_PORT="$port"; $env:IB_CLIENT_ID="201"
$env:TIF="IOC"; $env:TICK_CAP="20"; $env:MAX_NOTIONAL_USD="1000"
$env:OUTSIDE_RTH="true"; $env:ABORT_IF_NO_QUOTE="true"
# guards
$env:TRADE_WINDOWS="06:35-12:45"; $env:MAX_SPREAD_BPS="8"; $env:MAX_DAILY_LOSS_USD="300"; $env:MAX_EXPOSURE_USD="5000"

# --- Start TWS if API port not up ---
function Test-Port($p){ try { (Test-NetConnection 127.0.0.1 -Port $p -WarningAction SilentlyContinue).TcpTestSucceeded } catch { $false } }
if (-not (Test-Port $port)) {
  if (Test-Path $twsExe) { Start-Process -FilePath $twsExe | Out-Null }
}

# --- Wait for port to open ---
$sw=[Diagnostics.Stopwatch]::StartNew()
while(-not (Test-Port $port) -and $sw.Elapsed.TotalSeconds -lt $maxWaitS){ Start-Sleep -Milliseconds 500 }
# --- Launch GUI ---
Start-Process -FilePath "python.exe" -ArgumentList ".\scripts\gui_trading_console.py" -WorkingDirectory (Get-Location).Path
