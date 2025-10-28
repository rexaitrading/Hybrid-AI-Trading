from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from hybrid_ai_trading.tools.replay_logger_hook import log_closed_trade

@dataclass
class ReplayResult:
    bars: int
    trades: int
    pnl: float
    entry_px: Optional[float]
    exit_px: Optional[float]
    final_pos: object = None

def run_replay(df, symbol: str, mode: str = "auto", **kw) -> ReplayResult:
    # Minimal stub: just prove import path + CSV hook wiring
    now = datetime(2025, 10, 24, 9, 35)
    log_closed_trade(
        symbol=symbol, setup="STUB", context_tags=[],
        entry_time=now, exit_time=now,
        entry=100.0, exit=100.5, qty=10,
        fees=0.0, slippage=0.0, r_multiple=0.0,
        notes="stub row", replay_id=f"{symbol}-stub"
    )
    return ReplayResult(bars=1, trades=1, pnl=5.0, entry_px=100.0, exit_px=100.5)