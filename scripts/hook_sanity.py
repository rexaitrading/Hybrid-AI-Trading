from datetime import datetime, date, time
from hybrid_ai_trading.tools.replay_logger_hook import log_closed_trade

log_closed_trade(
    symbol="AAPL",
    setup="ORB",
    context_tags=["TrendUp","HighVol"],
    entry_time=datetime.combine(date(2025,10,24), time(9,31)),
    exit_time=datetime.combine(date(2025,10,24), time(9,36)),
    entry=217.42,
    exit=218.11,
    qty=200,
    fees=1.20,
    slippage=0.80,
    r_multiple=0.9,
    notes="Hook sanity",
    replay_id="aapl-20251024-orb-hook"
)
print("hook_ok")