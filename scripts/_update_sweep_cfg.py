import yaml, os
from datetime import datetime
p = "config/config.yaml"
with open(p, "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f) or {}
u = cfg.get("universe") or {}
core = list(u.get("Core_Stocks") or [])
macro = list(u.get("Macro_Risk") or [])
tickers = [str(x).strip().upper() for x in (core + macro) if str(x).strip()]
if not tickers:
    tickers = ["AAPL","MSFT","GOOGL","AMZN","TSLA","NVDA","META","JPM","JNJ","SPY","QQQ","GLD","TLT","USO","UUP"]
cfg["sweep_symbols"] = ",".join(sorted(set(tickers)))
cfg.setdefault("sweep_hours_back", 24)
cfg.setdefault("sweep_limit", 100)
with open(p, "w", encoding="utf-8") as f:
    yaml.safe_dump(cfg, f, sort_keys=False)
print("SWEEP_SYMBOLS:", cfg["sweep_symbols"])
print("sweep_hours_back:", cfg["sweep_hours_back"])
print("sweep_limit:", cfg["sweep_limit"])