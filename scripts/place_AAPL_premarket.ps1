$env:PYTHONPATH = "src"
python -m hybrid_ai_trading.execution.paper_order
  --host 127.0.0.1 --port 7497 --client-id 2001
  --symbol AAPL --side BUY --qty 1
  --tp-pct 0.8 --sl-pct 0.5
  --spread-bps-cap 12 --ticks-clamp 20
  --outside-rth 1 --early-open-block-min 0 --autoreprice-sec 60
  --cooldown-min 10
