from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass
class RiskConfig:
    state_path: Optional[str] = None
    base_equity_fallback: float = 10000.0
    fail_closed: bool = True
    day_loss_cap_pct: Optional[float] = None
    per_trade_notional_cap: Optional[float] = None
    max_trades_per_day: int = 0
    max_consecutive_losers: int = 0
    cooldown_bars: int = 0
    max_drawdown_pct: Optional[float] = None
    equity: float = 100000.0
    max_leverage: Optional[float] = None
    max_portfolio_exposure: Optional[float] = None
