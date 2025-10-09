function Show-Header {
  Write-Host "============================================="
  Write-Host " Hybrid AI Trading – Ops Console (LIVE)      "
  Write-Host "============================================="
}

function Show-Status {
  Write-Host "`n-- Environment / Config --"
  python -c "import os; print('POLYGON:', bool(os.getenv('POLYGON_KEY'))); print('ALPACA:', bool(os.getenv('ALPACA_KEY_ID')) and bool(os.getenv('ALPACA_SECRET_KEY'))); print('COINAPI:', bool(os.getenv('COINAPI_KEY'))); print('COINAPI_STUB:', os.getenv('COINAPI_STUB'))"
  python -c "import hybrid_ai_trading.config.settings as s; s.load_config(force=True); print('CONFIG_PATH:', s.CONFIG_PATH); print('execution:', {k:s.CONFIG['execution'][k] for k in ('use_paper_simulator','max_order_retries','timeout_sec')}); print('alerts:', s.CONFIG.get('alerts'))"
}

function Export-PrevClose {
  Write-Host "`n-- Export Previous Close --"
  python -m hybrid_ai_trading.pipelines.export_prev_close
}

function Build-Dashboard {
  Write-Host "`n-- Daily Stock Dashboard --"
  python -m hybrid_ai_trading.pipelines.daily_stock_dashboard
}

function Start-Live {
  Write-Host "`n-- START LIVE ENGINE (equities live) --"
  python -m hybrid_ai_trading.main --pipeline paper_trade
}

function Tail-Logs {
  $last = Get-ChildItem logs\*.log -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if ($null -eq $last) { Write-Host "No logs yet." ; return }
  Write-Host "Tailing $($last.FullName) (Ctrl+C to stop)"
  Get-Content -Path $last.FullName -Wait
}

function Set-CoinAPIStub {
  param([string]$On = "1")
  $env:COINAPI_STUB = $On
  Write-Host "COINAPI_STUB set to $On (session)."
}

function Clear-CoinAPIStub {
  Remove-Item Env:COINAPI_STUB -ErrorAction SilentlyContinue
  [Environment]::SetEnvironmentVariable("COINAPI_STUB", $null, "User")
  Write-Host "COINAPI_STUB cleared (session and user)."
}

function Flatten-All {
  if (-not (Test-Path .\flatten.py)) {
    Set-Content -Encoding utf8 .\flatten.py "from hybrid_ai_trading.execution.execution_engine import ExecutionEngine as E; print(E(dry_run=False, config=None).emergency_flatten())"
  }
  Write-Host "`n-- EMERGENCY FLATTEN --"
  python .\flatten.py
}

function Place-Order {
  $sym  = Read-Host "Symbol (e.g., AAPL or BTC/USDT)"
  $side = Read-Host "Side (BUY/SELL)"
  $qty  = Read-Host "Qty (number)"
  $price = Read-Host "Price (optional; blank = market)"
  if (-not $sym -or -not $side -or -not $qty) { Write-Host "Missing inputs." ; return }
  $cmd = "python manual_order.py --symbol `"$sym`" --side `"$($side.ToUpper())`" --qty $qty"
  if ($price) { $cmd += " --price $price" }
  Write-Host "`nExecuting: $cmd"
  Invoke-Expression $cmd
}

function Show-Menu {
  Show-Header
  Write-Host ""
  Write-Host " 1) Show status (env + config)"
  Write-Host " 2) Export previous close (data/)"
  Write-Host " 3) Build daily dashboard (logs/)"
  Write-Host " 4) Start LIVE engine (paper_trade pipeline)"
  Write-Host " 5) Tail latest log"
  Write-Host " 6) Place manual order"
  Write-Host " 7) Emergency FLATTEN"
  Write-Host " 8) Enable COINAPI_STUB (crypto demo)"
  Write-Host " 9) Disable COINAPI_STUB"
  Write-Host " 0) Exit`n"
}

while ($true) {
  Show-Menu
  $choice = Read-Host "Select"
  switch ($choice) {
    "1" { Show-Status }
    "2" { Export-PrevClose }
    "3" { Build-Dashboard }
    "4" { Start-Live }
    "5" { Tail-Logs }
    "6" { Place-Order }
    "7" { Flatten-All }
    "8" { Set-CoinAPIStub -On "1" }
    "9" { Clear-CoinAPIStub }
    "0" { break }
    default { Write-Host "Unknown option." }
  }
  Write-Host "`nPress Enter to continue ..."; [void][System.Console]::ReadKey()
  Clear-Host
}
