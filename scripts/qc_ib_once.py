import os

from ib_insync import IB, Stock

import hybrid_ai_trading.runners.paper_trader as M
from hybrid_ai_trading.runners.paper_logger import JsonlLogger

os.makedirs("logs", exist_ok=True)
log_path = "logs/runner_paper.jsonl"
logger = JsonlLogger(log_path)

ib = IB()
ib.connect("127.0.0.1", 4002, clientId=14, timeout=15)
symbols = ["AAPL", "MSFT"]
contracts = {s: Stock(s, "SMART", "USD") for s in symbols}
for c in contracts.values():
    ib.reqMktData(c, "", False, False)
ib.sleep(1.5)


def snap(sym):
    t = ib.ticker(contracts[sym])
    px = t.last or t.marketPrice() or t.close or t.vwap
    try:
        px = float(px) if px is not None else None
    except:
        px = None
    return {"symbol": sym, "price": px}


snapshots = [snap(s) for s in symbols]
ib.disconnect()

logger.info("run_start", mode="ib-once-helper", symbols=symbols, snapshots=snapshots)
cfg = {}
result = M._qc_run_once(symbols, snapshots, cfg, logger)
logger.info("once_done", result=result)
print("ib once: items:", len(result.get("items", [])))
