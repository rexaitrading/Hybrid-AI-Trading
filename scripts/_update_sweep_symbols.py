import yaml

p = "config/config.yaml"
with open(p, "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f) or {}
uni = cfg.get("universe") or {}
core = list(uni.get("Core_Stocks") or [])
tickers = [str(x).strip().upper() for x in core if str(x).strip()]
if not tickers:
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "JPM", "JNJ"]
cfg["sweep_symbols"] = ",".join(tickers)
with open(p, "w", encoding="utf-8") as f:
    yaml.safe_dump(cfg, f, sort_keys=False)
print("SWEEP_SYMBOLS:", cfg["sweep_symbols"])
