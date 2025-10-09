import yaml

from hybrid_ai_trading.risk.sentiment_gate import score_headlines_for_symbols

with open("config/config.yaml", "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f) or {}
symbols = (cfg.get("sweep_symbols") or "AAPL,MSFT,GOOGL,AMZN,TSLA").upper()
hours_back = int(cfg.get("sweep_hours_back", 6))
limit = int(cfg.get("sweep_limit", 100))
res = score_headlines_for_symbols(
    symbols, hours_back=hours_back, limit=limit, side="BUY"
)
total = int(res.get("total", 0))
allows = sum(1 for s in res.get("stories", []) if s.get("allow"))
print(f"PROBE total={total} allows={allows}")
