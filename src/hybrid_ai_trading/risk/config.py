from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class RiskConfig:
    state_path: Optional[str] = None
    base_equity_fallback: float = 10000.0
    fail_closed: bool = True

    # --- legacy/compat fields (RiskManager older paths expect these) ---
    # daily_loss_limit: absolute PnL floor (negative). If None, may be derived from day_loss_cap_pct.
    daily_loss_limit: Optional[float] = None

    # trade_loss_limit: per-trade risk limit (optional)
    trade_loss_limit: Optional[float] = None

    # max_drawdown: alias (fraction). Canonical is max_drawdown_pct.
    max_drawdown: Optional[float] = None

    # max_position_size: optional clamp used by some legacy checks
    max_position_size: Optional[float] = None

    # max_daily_loss: alias for daily loss cap (absolute). Some tests/paths use it.
    max_daily_loss: Optional[float] = None

    # Phase-5 canonical daily loss cap (absolute, negative). Used by Phase-5 gate tests.
    phase5_daily_loss_cap: Optional[float] = None

    # optional performance floors used by some legacy gates
    roi_min: Optional[float] = None
    sharpe_min: Optional[float] = None
    sortino_min: Optional[float] = None
    day_loss_cap_pct: Optional[float] = None
    per_trade_notional_cap: Optional[float] = None
    max_trades_per_day: int = 0
    max_consecutive_losers: int = 0
    cooldown_bars: int = 0
    max_drawdown_pct: Optional[float] = None
    equity: float = 100000.0
    max_leverage: Optional[float] = None
    max_portfolio_exposure: Optional[float] = None
