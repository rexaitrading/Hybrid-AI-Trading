$env:PYTHONPATH="src"
$env:IB_HOST="127.0.0.1"; $env:IB_PORT="7497"; $env:IB_CLIENT_ID="201"
$env:TIF="IOC"; $env:TICK_CAP="20"; $env:MAX_NOTIONAL_USD="1000"
$env:OUTSIDE_RTH="true"; $env:ABORT_IF_NO_QUOTE="true"

# AAPL (use 5 bps)
$env:SYMBOL="AAPL"; $env:SIDE="BUY";  $env:QTY="1"; $env:SLIPPAGE_BPS="5"; python .\scripts\ib_quote_market_order.py
$env:SIDE="SELL"; $env:QTY="1"; python .\scripts\ib_quote_market_order.py

# MSFT (high price → 3 bps to respect 20-tick cap)
$env:SYMBOL="MSFT"; $env:SIDE="BUY";  $env:QTY="1"; $env:SLIPPAGE_BPS="3"; python .\scripts\ib_quote_market_order.py
$env:SIDE="SELL"; $env:QTY="1"; python .\scripts\ib_quote_market_order.py

# Verify & show last orders
python .\scripts\ib_positions_check.py
Get-Content .\logs\orders.csv -Tail 20
