import datetime as dt
import os

from hybrid_ai_trading.tools.notion_csv_logger import log_trade

# EXAMPLE: pretend we executed one ORB trade on AAPL during replay
csv_out = os.path.join("logs", "theory_trades.csv")

date = "2025-10-24"
ticker = "AAPL"
setup = "ORB"
context = "TrendUp;HighVol"
entry_t = f"{date}T09:31"
exit_t = f"{date}T09:36"
entry = 217.42
exit_ = 218.11
qty = 200
fees = 1.20
slip = 0.80
rm = 0.9
pnl = (exit_ - entry) * qty - fees - slip
notes = "Clean 1m ORB over pre-market high; held above VWAP"
replay_id = "aapl-20251024-orb-001"

log_trade(
    path=csv_out,
    Date=date,
    Ticker=ticker,
    Setup=setup,
    Context=context,
    EntryTime=entry_t,
    ExitTime=exit_t,
    Entry=entry,
    Exit=exit_,
    Qty=qty,
    Fees=fees,
    Slippage=slip,
    RM=rm,
    PnL=pnl,
    Notes=notes,
    ReplayID=replay_id,
)
print("Wrote", csv_out)
