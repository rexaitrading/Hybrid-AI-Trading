import os

import hybrid_ai_trading.runners.paper_trader as M  # exposes _qc_run_once
from hybrid_ai_trading.runners.paper_logger import JsonlLogger

os.makedirs("logs", exist_ok=True)
log_path = "logs/runner_paper.jsonl"
logger = JsonlLogger(log_path)

symbols = ["AAPL", "MSFT"]
snapshots = [{"symbol": s, "price": None} for s in symbols]
cfg = {"provider_only": True}

logger.info("run_start", mode="provider-only-helper", symbols=symbols)
result = M._qc_run_once(symbols, snapshots, cfg, logger)
logger.info("once_done", result=result)
print("provider-only once: items:", len(result.get("items", [])))
