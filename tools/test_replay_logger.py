from datetime import datetime
from hybrid_ai_trading.tools.notion_csv_logger import log_trade

log_trade({
    "ts": datetime.utcnow().isoformat(),
    "symbol": "SPY",
    "side": "LONG",
    "qty": 100,
    "entry": 500.0,
    "exit": 505.0,
    "pnl": 500.0,
    "R": 1.0,
    "pattern": "test_replay_hook",
    "regime": "NA test",
    "notes": "manual logger test trade"
})