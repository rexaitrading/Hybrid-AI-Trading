# Flatten AAPL/MSFT just in case (safe if already flat)
$env:SYMBOL="AAPL"; python .\scripts\ib_flatten_symbol.py | Out-Null
$env:SYMBOL="MSFT"; python .\scripts\ib_flatten_symbol.py | Out-Null
# Cancel any open orders
$env:SYMBOL="AAPL"; python .\scripts\ib_cancel_symbol_orders.py | Out-Null
$env:SYMBOL="MSFT"; python .\scripts\ib_cancel_symbol_orders.py | Out-Null
# Build report
python .\scripts\report_daily.py
# Open the report in Notepad
$today = Get-Date -Format "yyyy-MM-dd"
$rep = ".\logs\reports\${today}_report.md"
if (Test-Path $rep) { notepad $rep }
