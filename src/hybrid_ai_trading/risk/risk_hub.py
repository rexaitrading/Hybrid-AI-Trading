from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict

@dataclass
class RiskContext:
    equity: float
    day_pnl: float
    realized_pnl: float
    unrealized_pnl: float
    max_day_loss: float        # e.g., -0.02 * equity
    max_trade_risk: float      # e.g., 0.25% of equity
    kelly_cap: float           # e.g., 0.5 (50% of full Kelly)
    regime_ok: bool
    sentiment_ok: bool

@dataclass
class OrderIntent:
    symbol: str
    side: str                 # 'long' or 'short'
    entry_px: float
    stop_px: Optional[float]  # required for sizing
    take_px: Optional[float]
    signal_strength: float    # 0..1 (from your pattern/ML/scalper trigger)

@dataclass
class SizedOrder:
    ok: bool
    reason: Optional[str]
    qty: int
    risk_per_share: float
    kelly_f: float
    est_edge: float
    est_winrate: float
    est_rr: float

class KellySizer:
    @staticmethod
    def kelly_fraction(p_win: float, r: float) -> float:
        # r = avg_win / avg_loss (loss as positive magnitude)
        # full Kelly: f* = p - (1-p)/r
        return max(0.0, min(1.0, p_win - (1 - p_win) / max(r, 1e-9)))

    @staticmethod
    def size_from_kelly(equity: float, f: float, risk_per_share: float) -> int:
        if risk_per_share <= 0: return 0
        dollar_risk = equity * f
        return max(0, int(dollar_risk // risk_per_share))

class RiskHub:
    def __init__(self, ctx: RiskContext):
        self.ctx = ctx

    def approve(self, intent: OrderIntent, stats: Dict[str, float]) -> SizedOrder:
        # gates
        if not self.ctx.regime_ok:
            return SizedOrder(False, "Regime gate failed", 0, 0, 0, 0, 0)
        if not self.ctx.sentiment_ok:
            return SizedOrder(False, "Sentiment gate failed", 0, 0, 0, 0, 0)
        if self
